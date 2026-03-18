"""Unit tests for MetricsCalculator (Feature 012 — Phases 3-5)."""

from __future__ import annotations

from specforge.core.metrics_calculator import (
    aggregate_quality,
    build_lifecycle,
    calculate_phase_progress,
    derive_service_status,
)
from specforge.core.result import Err, Ok
from specforge.core.status_collector import ServiceRawState
from specforge.core.status_models import (
    LifecyclePhases,
    ServiceStatusRecord,
)


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


# ── Helpers for Phase Progress + Quality tests ────────────────────────


def _svc_record(
    slug: str,
    status: str,
    impl_percent: int | None = None,
    phase_index: int | None = None,
    features: tuple[str, ...] = ("F001",),
    tests_passed: int | None = None,
    tests_total: int | None = None,
) -> ServiceStatusRecord:
    return ServiceStatusRecord(
        slug=slug,
        display_name=slug.title(),
        features=features,
        lifecycle=LifecyclePhases(impl_percent=impl_percent,
                                  tests_passed=tests_passed,
                                  tests_total=tests_total),
        overall_status=status,
        phase_index=phase_index,
    )


def _orch_data(phases: list[dict]) -> dict:
    return {"architecture": "microservice", "status": "in-progress", "phases": phases}


def _orch_phase(
    index: int,
    services: list[str],
    label: str = "",
) -> dict:
    return {
        "index": index,
        "label": label or f"Phase {index}",
        "services": [{"slug": s} for s in services],
    }


# ── T013: Phase progress tests ───────────────────────────────────────


class TestCalculatePhaseProgress:
    def test_calculate_phase_progress_all_complete(self) -> None:
        orch = _orch_data([_orch_phase(0, ["svc-a", "svc-b"])])
        statuses = {
            "svc-a": _svc_record("svc-a", "COMPLETE"),
            "svc-b": _svc_record("svc-b", "COMPLETE"),
        }
        result = calculate_phase_progress(orch, statuses)
        assert len(result) == 1
        assert result[0].completion_percent == 100.0
        assert result[0].status == "complete"

    def test_calculate_phase_progress_partial(self) -> None:
        orch = _orch_data([_orch_phase(0, ["svc-a", "svc-b"])])
        statuses = {
            "svc-a": _svc_record("svc-a", "COMPLETE"),
            "svc-b": _svc_record("svc-b", "IN_PROGRESS", impl_percent=50),
        }
        result = calculate_phase_progress(orch, statuses)
        assert len(result) == 1
        assert 0 < result[0].completion_percent < 100.0
        assert result[0].status == "in-progress"

    def test_calculate_phase_progress_blocked(self) -> None:
        orch = _orch_data([
            _orch_phase(0, ["svc-a"]),
            _orch_phase(1, ["svc-b"]),
        ])
        statuses = {
            "svc-a": _svc_record("svc-a", "IN_PROGRESS", impl_percent=50),
            "svc-b": _svc_record("svc-b", "NOT_STARTED"),
        }
        result = calculate_phase_progress(orch, statuses)
        assert len(result) == 2
        # Phase 1 should be blocked by phase 0
        assert result[1].status == "blocked"
        assert result[1].blocked_by == 0

    def test_calculate_phase_progress_no_orchestration_state(self) -> None:
        statuses = {"svc-a": _svc_record("svc-a", "COMPLETE")}
        result = calculate_phase_progress(None, statuses)
        assert result == ()

    def test_calculate_phase_progress_monolith(self) -> None:
        # Monolith: no phases in orch_data
        orch = _orch_data([])
        statuses = {"mono": _svc_record("mono", "COMPLETE")}
        result = calculate_phase_progress(orch, statuses)
        assert result == ()

    def test_phase_service_details(self) -> None:
        orch = _orch_data([_orch_phase(0, ["svc-a", "svc-b"])])
        statuses = {
            "svc-a": _svc_record("svc-a", "COMPLETE"),
            "svc-b": _svc_record("svc-b", "IN_PROGRESS", impl_percent=60),
        }
        result = calculate_phase_progress(orch, statuses)
        details = result[0].service_details
        assert len(details) == 2
        slugs = {d.slug for d in details}
        assert slugs == {"svc-a", "svc-b"}
        for d in details:
            if d.slug == "svc-b":
                assert d.status == "IN_PROGRESS"
                assert d.impl_percent == 60

    def test_calculate_phase_progress_not_started_services_reduce_percent(
        self,
    ) -> None:
        orch = _orch_data([_orch_phase(0, ["a", "b", "c"])])
        statuses = {
            "a": _svc_record("a", "COMPLETE"),
            "b": _svc_record("b", "NOT_STARTED"),
            "c": _svc_record("c", "NOT_STARTED"),
        }
        result = calculate_phase_progress(orch, statuses)
        # 1 complete (100) + 2 not started (0 each) → ~33%
        assert 30.0 <= result[0].completion_percent <= 36.0

    def test_calculate_phase_progress_multi_feature_service_no_double_count(
        self,
    ) -> None:
        orch = _orch_data([_orch_phase(0, ["svc-a"])])
        statuses = {
            "svc-a": _svc_record(
                "svc-a", "IN_PROGRESS",
                impl_percent=50,
                features=("F001", "F002", "F003"),
            ),
        }
        result = calculate_phase_progress(orch, statuses)
        # Only 1 service, counted once despite multiple features
        assert len(result[0].services) == 1
        assert len(result[0].service_details) == 1


# ── T017: Quality aggregation tests ──────────────────────────────────


class TestAggregateQuality:
    def test_aggregate_quality_service_counts_by_status(self) -> None:
        services = (
            _svc_record("a", "COMPLETE"),
            _svc_record("b", "IN_PROGRESS"),
            _svc_record("c", "PLANNING"),
            _svc_record("d", "NOT_STARTED"),
            _svc_record("e", "BLOCKED"),
            _svc_record("f", "FAILED"),
            _svc_record("g", "UNKNOWN"),
        )
        q = aggregate_quality(services, "microservice", {})
        assert q.services_total == 7
        assert q.services_complete == 1
        assert q.services_in_progress == 1
        assert q.services_planning == 1
        assert q.services_not_started == 1
        assert q.services_blocked == 1
        assert q.services_failed == 1
        assert q.services_unknown == 1
        total = (
            q.services_complete + q.services_in_progress + q.services_planning
            + q.services_not_started + q.services_blocked
            + q.services_failed + q.services_unknown
        )
        assert total == q.services_total

    def test_aggregate_quality_task_counts(self) -> None:
        services = (_svc_record("a", "IN_PROGRESS"),)
        raw_states = {
            "a": ServiceRawState(
                slug="a",
                execution=Ok({"tasks": [
                    {"task_id": "T1", "status": "completed"},
                    {"task_id": "T2", "status": "completed"},
                    {"task_id": "T3", "status": "failed"},
                    {"task_id": "T4", "status": "in-progress"},
                ]}),
            ),
        }
        q = aggregate_quality(services, "microservice", raw_states)
        assert q.tasks_total == 4
        assert q.tasks_complete == 2
        assert q.tasks_failed == 1

    def test_aggregate_quality_coverage_average(self) -> None:
        services = (
            _svc_record("a", "COMPLETE"),
            _svc_record("b", "IN_PROGRESS"),
            _svc_record("c", "NOT_STARTED"),
        )
        raw_states = {
            "a": ServiceRawState(
                slug="a",
                quality=Ok({"gate_result": {"check_results": [
                    {"checker_name": "coverage_checker", "output": "Coverage: 80%"},
                ]}}),
            ),
            "b": ServiceRawState(
                slug="b",
                quality=Ok({"gate_result": {"check_results": [
                    {"checker_name": "coverage_checker", "output": "Coverage: 60%"},
                ]}}),
            ),
            # c has no quality → excluded from avg
        }
        q = aggregate_quality(services, "microservice", raw_states)
        assert q.coverage_avg == 70.0

    def test_aggregate_quality_docker_metrics_microservice_only(self) -> None:
        services = (_svc_record("a", "COMPLETE"), _svc_record("b", "COMPLETE"))
        raw_states = {
            "a": ServiceRawState(
                slug="a",
                quality=Ok({"gate_result": {"check_results": [
                    {"checker_name": "docker_checker", "passed": True},
                ]}}),
            ),
            "b": ServiceRawState(
                slug="b",
                quality=Ok({"gate_result": {"check_results": [
                    {"checker_name": "docker_checker", "passed": False},
                ]}}),
            ),
        }
        q = aggregate_quality(services, "microservice", raw_states)
        assert q.docker_total == 2
        assert q.docker_built == 1
        assert q.docker_failing == 1

    def test_aggregate_quality_docker_metrics_none_for_monolith(self) -> None:
        services = (_svc_record("a", "COMPLETE"),)
        q = aggregate_quality(services, "monolithic", {})
        assert q.docker_built is None
        assert q.docker_total is None
        assert q.docker_failing is None

    def test_aggregate_quality_contract_results(self) -> None:
        services = (_svc_record("a", "COMPLETE"),)
        raw_states = {
            "a": ServiceRawState(
                slug="a",
                quality=Ok({"gate_result": {"check_results": [
                    {"checker_name": "contract_checker", "passed": True},
                    {"checker_name": "contract_checker", "passed": True},
                    {"checker_name": "contract_checker", "passed": False},
                ]}}),
            ),
        }
        q = aggregate_quality(services, "microservice", raw_states)
        assert q.contract_total == 3
        assert q.contract_passed == 2

    def test_aggregate_quality_autofix_rate(self) -> None:
        services = (_svc_record("a", "COMPLETE"),)
        raw_states = {
            "a": ServiceRawState(
                slug="a",
                execution=Ok({"tasks": [
                    {"task_id": "T1", "status": "completed",
                     "fix_attempts": [
                         {"success": True},
                         {"success": False},
                         {"success": True},
                     ]},
                    {"task_id": "T2", "status": "completed",
                     "fix_attempts": [{"success": True}]},
                ]}),
            ),
        }
        q = aggregate_quality(services, "microservice", raw_states)
        # 3 success / 4 total = 0.75
        assert q.autofix_success_rate == 0.75

    def test_aggregate_quality_no_reports(self) -> None:
        services = (_svc_record("a", "NOT_STARTED"),)
        q = aggregate_quality(services, "microservice", {})
        assert q.tasks_total == 0
        assert q.tasks_complete == 0
        assert q.tasks_failed == 0
        assert q.coverage_avg is None
        assert q.docker_built is None
        assert q.docker_total is None
        assert q.autofix_success_rate is None

    def test_has_failures_true_when_any_failed(self) -> None:
        services = (
            _svc_record("a", "COMPLETE"),
            _svc_record("b", "FAILED"),
        )
        q = aggregate_quality(services, "microservice", {})
        assert q.services_failed > 0

    def test_has_failures_false_when_none_failed(self) -> None:
        services = (
            _svc_record("a", "COMPLETE"),
            _svc_record("b", "IN_PROGRESS"),
        )
        q = aggregate_quality(services, "microservice", {})
        assert q.services_failed == 0
