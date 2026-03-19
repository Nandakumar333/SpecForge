"""Adapter to run SubAgentExecutor in parallel waves (Feature 016)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from specforge.core.parallel_state import (
    ParallelExecutionState,
    ServiceRunStatus,
    _now_iso,
)
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.parallel_progress_tracker import ProgressTracker
    from specforge.core.sub_agent_executor import SubAgentExecutor


class ParallelImplRunner:
    """Parallel implementation runner using SubAgentExecutor per service.

    Implements the same .run() interface as ParallelPipelineRunner
    so TopologicalParallelExecutor can use either.
    """

    def __init__(
        self,
        executor_factory: Callable[[], SubAgentExecutor],
        tracker: ProgressTracker,
        max_workers: int = 4,
        fail_fast: bool = False,
        mode: str = "prompt-display",
    ) -> None:
        self._executor_factory = executor_factory
        self._tracker = tracker
        self._max_workers = max_workers
        self._fail_fast = fail_fast
        self._mode = mode
        self._shutdown_event = threading.Event()

    def run(
        self,
        service_slugs: tuple[str, ...],
        project_root: object,
        max_workers: int | None = None,
        fail_fast: bool | None = None,
        **kwargs,
    ) -> Result[ParallelExecutionState, str]:
        """Execute implementation in parallel for given service slugs."""
        workers = min(
            max_workers or self._max_workers,
            len(service_slugs),
        )
        ff = fail_fast if fail_fast is not None else self._fail_fast

        if not service_slugs:
            return Err("No services to implement")

        results: dict[str, ServiceRunStatus] = {}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures: dict[Future, str] = {}
            for slug in service_slugs:
                if self._shutdown_event.is_set():
                    break
                fut = executor.submit(self._run_service, slug)
                futures[fut] = slug

            for fut in as_completed(futures):
                slug = futures[fut]
                try:
                    results[slug] = fut.result()
                except Exception as exc:
                    results[slug] = ServiceRunStatus(
                        slug=slug, status="failed",
                        error=str(exc), completed_at=_now_iso(),
                    )
                if ff and results[slug].status == "failed":
                    self._shutdown_event.set()
                    executor.shutdown(wait=False, cancel_futures=True)
                    for _other_fut, other_slug in futures.items():
                        if other_slug not in results:
                            results[other_slug] = ServiceRunStatus(
                                slug=other_slug, status="cancelled",
                                completed_at=_now_iso(),
                            )
                    break

        services = tuple(
            results.get(s, ServiceRunStatus(slug=s, status="cancelled"))
            for s in service_slugs
        )
        statuses = {s.status for s in services}
        overall = "completed"
        if "failed" in statuses:
            overall = "failed"
        elif "cancelled" in statuses:
            overall = "cancelled"

        return Ok(ParallelExecutionState(
            run_id=_now_iso(),
            mode="implement",
            architecture="microservice",
            total_services=len(service_slugs),
            max_workers=workers,
            fail_fast=ff,
            status=overall,
            services=services,
            started_at=_now_iso(),
            completed_at=_now_iso(),
        ))

    def _run_service(self, slug: str) -> ServiceRunStatus:
        """Execute implementation for a single service in a thread."""
        self._tracker.on_phase_start(slug, "implement")
        try:
            executor = self._executor_factory()
            result = executor.execute(slug, self._mode)
            if result.ok:
                state = result.value
                done = sum(1 for t in state.tasks if t.status == "completed")
                self._tracker.on_service_complete(slug)
                return ServiceRunStatus(
                    slug=slug, status="completed",
                    phases_completed=done,
                    phases_total=len(state.tasks),
                    completed_at=_now_iso(),
                )
            self._tracker.on_service_failed(slug, str(result.error))
            return ServiceRunStatus(
                slug=slug, status="failed",
                error=str(result.error), completed_at=_now_iso(),
            )
        except Exception as exc:
            self._tracker.on_service_failed(slug, str(exc))
            return ServiceRunStatus(
                slug=slug, status="failed",
                error=str(exc), completed_at=_now_iso(),
            )
