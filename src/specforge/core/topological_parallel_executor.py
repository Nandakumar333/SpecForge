"""Topological wave computation and parallel wave executor (Feature 016)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from specforge.core.dependency_graph import build_graph, compute_phases
from specforge.core.parallel_state import (
    ParallelExecutionState,
    WaveStatus,
    _now_iso,
)
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.parallel_pipeline_runner import ParallelPipelineRunner
    from specforge.core.parallel_progress_tracker import ProgressTracker


def compute_waves(manifest: dict) -> Result[tuple[WaveStatus, ...], str]:
    """Compute dependency waves from manifest.

    Returns WaveStatus tuples with service assignments per wave.
    """
    graph_r = build_graph(manifest)
    if not graph_r.ok:
        return Err(graph_r.error)
    phases_r = compute_phases(graph_r.value)
    if not phases_r.ok:
        return Err(phases_r.error)
    waves = tuple(
        WaveStatus(index=p.index, services=p.services)
        for p in phases_r.value
    )
    return Ok(waves)


def architecture_to_waves(
    manifest: dict,
) -> Result[tuple[WaveStatus, ...], str]:
    """Compute waves based on architecture type.

    - microservice: topological ordering from dependency graph
    - monolith: single wave with all modules
    - modular-monolith: topological if communication[] exists, else single wave
    """
    arch = manifest.get("architecture", "monolithic")
    services = manifest.get("services", [])
    if not services:
        return Err("Manifest contains no services")

    slugs = tuple(s["slug"] for s in services)

    if arch == "monolithic":
        return Ok((WaveStatus(index=0, services=slugs),))

    if arch == "modular-monolith":
        has_comm = any(s.get("communication") for s in services)
        if not has_comm:
            return Ok((WaveStatus(index=0, services=slugs),))

    return compute_waves(manifest)


class TopologicalParallelExecutor:
    """Execute services in topologically sorted dependency waves."""

    def __init__(
        self,
        runner: ParallelPipelineRunner,
        tracker: ProgressTracker,
    ) -> None:
        self._runner = runner
        self._tracker = tracker

    def execute(
        self,
        manifest: dict,
        project_root: object,
        max_workers: int = 4,
        fail_fast: bool = False,
    ) -> Result[ParallelExecutionState, str]:
        """Execute all waves sequentially, services within each in parallel."""
        waves_r = architecture_to_waves(manifest)
        if not waves_r.ok:
            return Err(waves_r.error)

        waves = waves_r.value
        failed_services: set[str] = set()
        all_results: list[ParallelExecutionState] = []

        for wave in waves:
            runnable, blocked = self._check_blocked(
                wave, manifest, failed_services,
            )
            for slug in blocked:
                blocker = self._find_blocker(slug, manifest, failed_services)
                self._tracker.on_service_blocked(slug, blocker)

            if not runnable:
                if fail_fast:
                    break
                continue

            wave_updated = replace(
                wave, status="in-progress", started_at=_now_iso(),
            )
            result = self._runner.run(
                service_slugs=runnable,
                project_root=project_root,
                max_workers=max_workers,
                fail_fast=fail_fast,
            )
            if result.ok:
                state = result.value
                for svc in state.services:
                    if svc.status == "failed":
                        failed_services.add(svc.slug)
                all_results.append(state)
                wave_updated = replace(
                    wave_updated,
                    status=self._wave_status(state),
                    completed_at=_now_iso(),
                )
            else:
                return result

            if fail_fast and failed_services:
                break

        return Ok(self._merge_results(
            all_results, waves, manifest, max_workers, fail_fast,
        ))

    def _check_blocked(
        self,
        wave: WaveStatus,
        manifest: dict,
        failed: set[str],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Split wave services into runnable and blocked."""
        if not failed:
            return wave.services, ()
        deps = self._build_dep_map(manifest)
        runnable: list[str] = []
        blocked: list[str] = []
        for slug in wave.services:
            if deps.get(slug, set()) & failed:
                blocked.append(slug)
            else:
                runnable.append(slug)
        return tuple(runnable), tuple(blocked)

    def _find_blocker(
        self, slug: str, manifest: dict, failed: set[str],
    ) -> str:
        """Find which failed service blocks this one."""
        deps = self._build_dep_map(manifest)
        blockers = deps.get(slug, set()) & failed
        return next(iter(sorted(blockers)), "unknown")

    def _build_dep_map(self, manifest: dict) -> dict[str, set[str]]:
        """Build slug -> set of dependency slugs."""
        result: dict[str, set[str]] = {}
        for svc in manifest.get("services", []):
            slug = svc["slug"]
            deps: set[str] = set()
            for link in svc.get("communication", []):
                deps.add(link["target"])
            result[slug] = deps
        return result

    def _wave_status(self, state: ParallelExecutionState) -> str:
        """Compute wave status from result state."""
        statuses = {s.status for s in state.services}
        if statuses == {"completed"}:
            return "completed"
        if "failed" in statuses:
            return "partial"
        return "completed"

    def _merge_results(
        self,
        results: list[ParallelExecutionState],
        waves: tuple[WaveStatus, ...],
        manifest: dict,
        max_workers: int,
        fail_fast: bool,
    ) -> ParallelExecutionState:
        """Merge per-wave results into a single state."""
        from specforge.core.parallel_state import (
            ParallelExecutionState,
            ServiceRunStatus,
        )

        all_services: list[ServiceRunStatus] = []
        for r in results:
            all_services.extend(r.services)

        arch = manifest.get("architecture", "microservice")
        all_slugs = {s["slug"] for s in manifest.get("services", [])}
        seen = {s.slug for s in all_services}
        for slug in sorted(all_slugs - seen):
            all_services.append(ServiceRunStatus(slug=slug, status="blocked"))

        statuses = {s.status for s in all_services}
        if statuses <= {"completed", "blocked"}:
            overall = "completed"
        elif "failed" in statuses:
            overall = "failed"
        elif "cancelled" in statuses:
            overall = "cancelled"
        else:
            overall = "in-progress"

        return ParallelExecutionState(
            run_id=_now_iso(),
            mode="implement",
            architecture=arch,
            total_services=len(all_slugs),
            max_workers=max_workers,
            fail_fast=fail_fast,
            status=overall,
            services=tuple(all_services),
            waves=waves,
            started_at=_now_iso(),
            completed_at=_now_iso() if overall != "in-progress" else None,
        )
