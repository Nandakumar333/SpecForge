"""Parallel pipeline runner — concurrent spec generation (Feature 016)."""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.parallel_state import (
    ParallelExecutionState,
    ServiceRunStatus,
    _now_iso,
)
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.parallel_progress_tracker import ProgressTracker
    from specforge.core.spec_pipeline import PipelineOrchestrator


class ParallelPipelineRunner:
    """Run spec pipelines concurrently across multiple services."""

    def __init__(
        self,
        orchestrator_factory: Callable[[], PipelineOrchestrator],
        tracker: ProgressTracker,
        max_workers: int = 4,
        fail_fast: bool = False,
    ) -> None:
        self._orchestrator_factory = orchestrator_factory
        self._tracker = tracker
        self._max_workers = max_workers
        self._fail_fast = fail_fast
        self._shutdown_event = threading.Event()
        self._original_sigint = None

    def run(
        self,
        service_slugs: tuple[str, ...],
        project_root: Path,
        force: bool = False,
        max_workers: int | None = None,
        fail_fast: bool | None = None,
    ) -> Result[ParallelExecutionState, str]:
        """Execute spec pipelines in parallel for all given services."""
        workers = max_workers or self._max_workers
        ff = fail_fast if fail_fast is not None else self._fail_fast
        effective_workers = min(workers, len(service_slugs))

        if not service_slugs:
            return Err("No services to process")

        self._install_signal_handler()
        try:
            return self._execute(
                service_slugs, project_root, force,
                effective_workers, ff,
            )
        finally:
            self._restore_signal_handler()

    def _execute(
        self,
        slugs: tuple[str, ...],
        project_root: Path,
        force: bool,
        max_workers: int,
        fail_fast: bool,
    ) -> Result[ParallelExecutionState, str]:
        """Submit services to thread pool and collect results."""
        results: dict[str, ServiceRunStatus] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures: dict[Future, str] = {}
            for slug in slugs:
                if self._shutdown_event.is_set():
                    break
                fut = executor.submit(
                    self._run_single_service,
                    slug, project_root, force,
                )
                futures[fut] = slug

            results = self._handle_futures(
                futures, executor, fail_fast,
            )

        return Ok(self._build_state(
            slugs, results, max_workers, fail_fast,
        ))

    def _run_single_service(
        self, slug: str, project_root: Path, force: bool,
    ) -> ServiceRunStatus:
        """Execute spec pipeline for a single service (runs in thread)."""
        self._tracker.on_phase_start(slug, "spec")
        try:
            orchestrator = self._orchestrator_factory()
            result = orchestrator.run(slug, project_root, force=force)
            if result.ok:
                self._tracker.on_service_complete(slug)
                return ServiceRunStatus(
                    slug=slug, status="completed",
                    phases_completed=7, completed_at=_now_iso(),
                )
            self._tracker.on_service_failed(slug, str(result.error))
            return ServiceRunStatus(
                slug=slug, status="failed",
                error=str(result.error), completed_at=_now_iso(),
            )
        except Exception as exc:
            error = str(exc)
            self._tracker.on_service_failed(slug, error)
            return ServiceRunStatus(
                slug=slug, status="failed",
                error=error, completed_at=_now_iso(),
            )

    def _handle_futures(
        self,
        futures: dict[Future, str],
        executor: ThreadPoolExecutor,
        fail_fast: bool,
    ) -> dict[str, ServiceRunStatus]:
        """Collect future results, handle fail-fast cancellation."""
        results: dict[str, ServiceRunStatus] = {}
        for fut in as_completed(futures):
            slug = futures[fut]
            try:
                status = fut.result()
                results[slug] = status
            except Exception as exc:
                results[slug] = ServiceRunStatus(
                    slug=slug, status="failed",
                    error=str(exc), completed_at=_now_iso(),
                )

            if fail_fast and results[slug].status == "failed":
                self._shutdown_event.set()
                executor.shutdown(wait=False, cancel_futures=True)
                for _other_fut, other_slug in futures.items():
                    if other_slug not in results:
                        results[other_slug] = ServiceRunStatus(
                            slug=other_slug, status="cancelled",
                            completed_at=_now_iso(),
                        )
                break
        return results

    def _build_state(
        self,
        all_slugs: tuple[str, ...],
        results: dict[str, ServiceRunStatus],
        max_workers: int,
        fail_fast: bool,
    ) -> ParallelExecutionState:
        """Build final ParallelExecutionState from results."""
        services = tuple(
            results.get(slug, ServiceRunStatus(slug=slug, status="cancelled"))
            for slug in all_slugs
        )
        statuses = {s.status for s in services}
        if statuses <= {"completed"}:
            overall = "completed"
        elif "failed" in statuses:
            overall = "failed"
        elif "cancelled" in statuses:
            overall = "cancelled"
        else:
            overall = "in-progress"

        return ParallelExecutionState(
            run_id=_now_iso(),
            mode="decompose",
            architecture="microservice",
            total_services=len(all_slugs),
            max_workers=max_workers,
            fail_fast=fail_fast,
            status=overall,
            services=services,
            started_at=_now_iso(),
            completed_at=_now_iso() if overall != "in-progress" else None,
        )

    def _install_signal_handler(self) -> None:
        """Install SIGINT handler for graceful shutdown."""
        try:
            self._original_sigint = signal.getsignal(signal.SIGINT)

            def _handler(signum: int, frame: object) -> None:
                if self._shutdown_event.is_set():
                    if self._original_sigint and callable(self._original_sigint):
                        self._original_sigint(signum, frame)
                    return
                self._shutdown_event.set()

            signal.signal(signal.SIGINT, _handler)
        except (ValueError, OSError):
            pass

    def _restore_signal_handler(self) -> None:
        """Restore original SIGINT handler."""
        try:
            if self._original_sigint is not None:
                signal.signal(signal.SIGINT, self._original_sigint)
        except (ValueError, OSError):
            pass
