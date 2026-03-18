"""Unit tests for MetricsCalculator (Feature 012 — Phase 3)."""

from __future__ import annotations

from specforge.core.metrics_calculator import (
    build_lifecycle,
    derive_service_status,
)
from specforge.core.result import Err, Ok
from specforge.core.status_collector import ServiceRawState


# ── Helpers ───────────────────────────────────────────────────────────


def _pipeline(phases: list[dict]) -> Ok:
    return Ok({"service_slug": "test", "schema_version": "1.0", "phases": phases})


def _execution(tasks: list[dict], verification: dict | None = None) -> Ok:
    data: dict = {"service_slug": "test", "tasks": tasks}
    if verification is not None:
        data["verification"] = verification
    return Ok(data)


def _quality(passed: bool, check_results: list[dict] | None = None) -> Ok:
    return Ok({
        "service_slug": "test",
        "level": "service",
        "gate_result": {
            "passed": passed,
            "check_results": check_results or [],
        },
    })


# ── T007: Status derivation tests ────────────────────────────────────


class TestDeriveServiceStatus:
    def test_derive_status_no_state_files(self) -> None:
        raw = ServiceRawState(slug="svc")
        assert derive_service_status(raw, dependencies_met=True) == "NOT_STARTED"

    def test_derive_status_pipeline_in_progress(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "plan", "status": "in-progress"},
            ]),
        )
        assert derive_service_status(raw, dependencies_met=True) == "PLANNING"

    def test_derive_status_execution_in_progress(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "plan", "status": "complete"},
                {"name": "tasks", "status": "complete"},
            ]),
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "in-progress"},
            ]),
        )
        assert derive_service_status(raw, dependencies_met=True) == "IN_PROGRESS"

    def test_derive_status_all_complete(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "plan", "status": "complete"},
                {"name": "tasks", "status": "complete"},
            ]),
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "completed"},
            ]),
            quality=_quality(passed=True),
        )
        assert derive_service_status(raw, dependencies_met=True) == "COMPLETE"

    def test_derive_status_task_failed(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([{"name": "spec", "status": "complete"}]),
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "failed"},
            ]),
        )
        assert derive_service_status(raw, dependencies_met=True) == "FAILED"

    def test_derive_status_quality_gate_failed(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "plan", "status": "complete"},
                {"name": "tasks", "status": "complete"},
            ]),
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
            ]),
            quality=_quality(passed=False),
        )
        assert derive_service_status(raw, dependencies_met=True) == "FAILED"

    def test_derive_status_corrupt_state(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=Err("corrupt pipeline"),
        )
        assert derive_service_status(raw, dependencies_met=True) == "UNKNOWN"

    def test_derive_status_blocked_by_dependency(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "plan", "status": "in-progress"},
            ]),
        )
        assert derive_service_status(raw, dependencies_met=False) == "BLOCKED"

    def test_derive_status_priority_waterfall(self) -> None:
        """FAILED takes precedence over IN_PROGRESS."""
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([{"name": "spec", "status": "complete"}]),
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "in-progress"},
                {"task_id": "T003", "status": "failed"},
            ]),
        )
        # Has both in-progress and failed tasks — FAILED should win
        assert derive_service_status(raw, dependencies_met=True) == "FAILED"

    def test_derive_status_corrupt_execution_is_unknown(self) -> None:
        """Corrupt execution file → UNKNOWN regardless of good pipeline."""
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([{"name": "spec", "status": "complete"}]),
            execution=Err("corrupt execution"),
        )
        assert derive_service_status(raw, dependencies_met=True) == "UNKNOWN"

    def test_derive_status_corrupt_quality_is_unknown(self) -> None:
        """Corrupt quality file → UNKNOWN regardless of good pipeline + execution."""
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([{"name": "spec", "status": "complete"}]),
            execution=_execution([{"task_id": "T001", "status": "completed"}]),
            quality=Err("corrupt quality"),
        )
        assert derive_service_status(raw, dependencies_met=True) == "UNKNOWN"


# ── Lifecycle building tests ─────────────────────────────────────────


class TestBuildLifecycle:
    def test_all_none_when_no_state(self) -> None:
        raw = ServiceRawState(slug="svc")
        lc = build_lifecycle(raw, "microservice")
        assert lc.spec is None
        assert lc.plan is None
        assert lc.tasks is None
        assert lc.impl_percent is None
        assert lc.tests_passed is None
        assert lc.tests_total is None
        assert lc.docker is None

    def test_pipeline_maps_to_lifecycle(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            pipeline=_pipeline([
                {"name": "spec", "status": "complete"},
                {"name": "research", "status": "complete"},
                {"name": "plan", "status": "in-progress"},
                {"name": "tasks", "status": "pending"},
            ]),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.spec == "DONE"
        assert lc.plan == "WIP"
        assert lc.tasks is None  # pending maps to None

    def test_impl_percent_from_tasks(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "completed"},
                {"task_id": "T003", "status": "in-progress"},
                {"task_id": "T004", "status": "pending"},
            ]),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.impl_percent == 50

    def test_impl_percent_zero_tasks(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            execution=_execution([]),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.impl_percent == 0

    def test_impl_percent_none_when_no_execution(self) -> None:
        raw = ServiceRawState(slug="svc")
        lc = build_lifecycle(raw, "microservice")
        assert lc.impl_percent is None

    def test_test_counts_extracted(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            quality=_quality(
                passed=True,
                check_results=[
                    {
                        "checker_name": "pytest",
                        "passed": True,
                        "category": "coverage",
                        "output": "Tests: 45 passed, 3 failed",
                    },
                ],
            ),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.tests_passed == 45
        assert lc.tests_total == 48

    def test_test_counts_none_without_quality(self) -> None:
        raw = ServiceRawState(slug="svc")
        lc = build_lifecycle(raw, "microservice")
        assert lc.tests_passed is None
        assert lc.tests_total is None

    def test_docker_ok(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            quality=_quality(
                passed=True,
                check_results=[
                    {
                        "checker_name": "docker_checker",
                        "passed": True,
                        "category": "docker",
                        "output": "OK",
                    },
                ],
            ),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.docker == "OK"

    def test_docker_fail(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            quality=_quality(
                passed=False,
                check_results=[
                    {
                        "checker_name": "docker_checker",
                        "passed": False,
                        "category": "docker",
                        "output": "Build failed",
                    },
                ],
            ),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.docker == "FAIL"

    def test_boundary_compliance(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            quality=_quality(
                passed=True,
                check_results=[
                    {
                        "checker_name": "boundary_checker",
                        "passed": True,
                        "category": "boundary",
                        "output": "All checks passed",
                    },
                ],
            ),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.boundary_compliance == "OK"

    def test_impl_percent_100_all_completed(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            execution=_execution([
                {"task_id": "T001", "status": "completed"},
                {"task_id": "T002", "status": "completed"},
                {"task_id": "T003", "status": "completed"},
            ]),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.impl_percent == 100

    def test_test_output_no_failures(self) -> None:
        raw = ServiceRawState(
            slug="svc",
            quality=_quality(
                passed=True,
                check_results=[
                    {
                        "checker_name": "pytest",
                        "passed": True,
                        "category": "coverage",
                        "output": "Tests: 20 passed",
                    },
                ],
            ),
        )
        lc = build_lifecycle(raw, "microservice")
        assert lc.tests_passed == 20
        assert lc.tests_total == 20
