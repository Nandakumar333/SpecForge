"""Thread-safe progress tracker for parallel execution (Feature 016)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from specforge.core.parallel_state import (
    ParallelExecutionState,
    ServiceRunStatus,
    WaveStatus,
    _now_iso,
    save_state,
)

if TYPE_CHECKING:
    pass


class ProgressTracker:
    """Thread-safe progress tracking with inline console output."""

    def __init__(
        self,
        console: Console,
        total_services: int,
        total_phases_per_service: int = 7,
        state_path: Path | None = None,
    ) -> None:
        self._console = console
        self._total_services = total_services
        self._phases_per_service = total_phases_per_service
        self._state_path = state_path
        self._lock = threading.Lock()
        self._service_phases: dict[str, int] = {}
        self._service_status: dict[str, str] = {}
        self._service_errors: dict[str, str] = {}
        self._service_blocked_by: dict[str, str] = {}
        self._service_start: dict[str, float] = {}
        self._service_end: dict[str, float] = {}
        self._run_start: float = time.monotonic()

    def on_phase_start(self, slug: str, phase: str) -> None:
        """Record phase start for a service."""
        with self._lock:
            if slug not in self._service_start:
                self._service_start[slug] = time.monotonic()
            self._service_status[slug] = "in-progress"

    def on_phase_complete(self, slug: str, phase: str) -> None:
        """Record phase completion and print inline progress."""
        with self._lock:
            count = self._service_phases.get(slug, 0) + 1
            self._service_phases[slug] = count
            self._console.print(
                f"  [cyan]{slug}[/] completed {phase} "
                f"[{count}/{self._phases_per_service}]"
            )
            self._persist()

    def on_phase_failed(
        self, slug: str, phase: str, error: str,
    ) -> None:
        """Record phase failure."""
        with self._lock:
            self._service_status[slug] = "failed"
            self._service_errors[slug] = f"{phase}: {error}"
            self._service_end[slug] = time.monotonic()
            self._console.print(
                f"  [red]{slug}[/] FAILED at {phase}: {error}"
            )
            self._persist()

    def on_service_complete(self, slug: str) -> None:
        """Record service completion with timing."""
        with self._lock:
            self._service_status[slug] = "completed"
            self._service_end[slug] = time.monotonic()
            elapsed = self._service_end[slug] - self._service_start.get(
                slug, self._run_start
            )
            self._console.print(
                f"  [green]{slug}[/] DONE ({elapsed:.1f}s)"
            )
            self._persist()

    def on_service_failed(self, slug: str, error: str) -> None:
        """Record service failure."""
        with self._lock:
            self._service_status[slug] = "failed"
            self._service_errors[slug] = error
            self._service_end[slug] = time.monotonic()
            self._console.print(
                f"  [red]{slug}[/] FAILED: {error}"
            )
            self._persist()

    def on_service_blocked(self, slug: str, blocked_by: str) -> None:
        """Record service as blocked."""
        with self._lock:
            self._service_status[slug] = "blocked"
            self._service_blocked_by[slug] = blocked_by
            self._console.print(
                f"  [yellow]{slug}[/] BLOCKED by {blocked_by}"
            )
            self._persist()

    def on_service_cancelled(self, slug: str) -> None:
        """Record service cancellation."""
        with self._lock:
            self._service_status[slug] = "cancelled"
            self._service_end[slug] = time.monotonic()
            self._persist()

    def get_summary(
        self,
        mode: str = "decompose",
        architecture: str = "microservice",
        max_workers: int = 4,
        fail_fast: bool = False,
        waves: tuple[WaveStatus, ...] = (),
    ) -> ParallelExecutionState:
        """Build a ParallelExecutionState from tracked data."""
        with self._lock:
            return self._build_state(
                mode, architecture, max_workers, fail_fast, waves,
            )

    def _build_state(
        self,
        mode: str,
        architecture: str,
        max_workers: int,
        fail_fast: bool,
        waves: tuple[WaveStatus, ...],
    ) -> ParallelExecutionState:
        """Internal: build state snapshot (must hold lock)."""
        services = tuple(
            self._build_service_status(slug, waves)
            for slug in sorted(
                set(self._service_phases)
                | set(self._service_status)
            )
        )
        overall = self._compute_overall(services)
        return ParallelExecutionState(
            run_id=_now_iso(),
            mode=mode,
            architecture=architecture,
            total_services=self._total_services,
            max_workers=max_workers,
            fail_fast=fail_fast,
            status=overall,
            services=services,
            waves=waves,
            started_at=_now_iso(),
        )

    def _build_service_status(
        self, slug: str, waves: tuple[WaveStatus, ...],
    ) -> ServiceRunStatus:
        """Build ServiceRunStatus for a single service."""
        status = self._service_status.get(slug, "pending")
        phases = self._service_phases.get(slug, 0)
        wave_idx = 0
        for w in waves:
            if slug in w.services:
                wave_idx = w.index
                break
        return ServiceRunStatus(
            slug=slug,
            status=status,
            wave_index=wave_idx,
            phases_completed=phases,
            phases_total=self._phases_per_service,
            error=self._service_errors.get(slug),
            blocked_by=self._service_blocked_by.get(slug),
        )

    def _compute_overall(
        self, services: tuple[ServiceRunStatus, ...],
    ) -> str:
        """Compute overall run status."""
        statuses = {s.status for s in services}
        if statuses <= {"completed", "blocked"}:
            return "completed"
        if "failed" in statuses:
            return "failed"
        if "cancelled" in statuses:
            return "cancelled"
        if "in-progress" in statuses:
            return "in-progress"
        return "pending"

    def _persist(self) -> None:
        """Write state to disk if state_path is set (must hold lock)."""
        if self._state_path is None:
            return
        state = self._build_state(
            "decompose", "microservice", 4, False, (),
        )
        import contextlib

        with contextlib.suppress(OSError):
            save_state(self._state_path, state)
