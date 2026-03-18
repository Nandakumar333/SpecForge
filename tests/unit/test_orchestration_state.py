"""Unit tests for orchestration_state.py — pure function state management."""

from __future__ import annotations

from specforge.core.orchestration_state import (
    add_verification_result,
    compute_phase_status,
    create_initial_state,
    detect_resume_point,
    get_completed_services,
    load_state,
    mark_phase_in_progress,
    mark_service_completed,
    mark_service_failed,
    mark_shared_infra_complete,
    mark_shared_infra_failed,
    save_state,
)
from specforge.core.orchestrator_models import (
    OrchestrationPlan,
    OrchestrationState,
    Phase,
    PhaseState,
    ServiceStatus,
    VerificationResult,
)


def _make_plan(architecture: str = "microservice") -> OrchestrationPlan:
    return OrchestrationPlan(
        architecture=architecture,
        phases=(
            Phase(index=0, services=("identity-service", "admin-service")),
            Phase(index=1, services=("ledger-service", "portfolio-service")),
            Phase(index=2, services=("planning-service", "analytics-service")),
        ),
        total_services=6,
        shared_infra_required=architecture != "monolithic",
    )


class TestCreateInitialState:
    def test_microservice(self) -> None:
        plan = _make_plan("microservice")
        state = create_initial_state(plan)
        assert state.architecture == "microservice"
        assert state.status == "pending"
        assert state.shared_infra_status == "pending"
        assert len(state.phases) == 3
        for ps in state.phases:
            assert ps.status == "pending"
            assert len(ps.services) > 0
            for ss in ps.services:
                assert ss.status == "pending"

    def test_monolith(self) -> None:
        plan = _make_plan("monolithic")
        state = create_initial_state(plan)
        assert state.shared_infra_status == "skipped"


class TestMarkSharedInfra:
    def test_mark_complete(self) -> None:
        state = create_initial_state(_make_plan())
        updated = mark_shared_infra_complete(state)
        assert updated.shared_infra_status == "completed"
        assert updated.shared_infra_status == "completed"  # timestamp may update

    def test_mark_failed(self) -> None:
        state = create_initial_state(_make_plan())
        updated = mark_shared_infra_failed(state)
        assert updated.shared_infra_status == "failed"


class TestMarkPhaseInProgress:
    def test_phase_transition(self) -> None:
        state = create_initial_state(_make_plan())
        updated = mark_phase_in_progress(state, 0)
        assert updated.phases[0].status == "in-progress"
        assert updated.phases[0].started_at is not None


class TestMarkServiceCompleted:
    def test_service_completed(self) -> None:
        state = create_initial_state(_make_plan())
        state = mark_phase_in_progress(state, 0)
        updated = mark_service_completed(state, 0, "identity-service", 12, 12)
        svc = _find_service(updated, 0, "identity-service")
        assert svc.status == "completed"
        assert svc.tasks_completed == 12
        assert svc.tasks_total == 12
        assert svc.completed_at is not None


class TestMarkServiceFailed:
    def test_service_failed(self) -> None:
        state = create_initial_state(_make_plan())
        state = mark_phase_in_progress(state, 0)
        updated = mark_service_failed(state, 0, "identity-service", "build error")
        svc = _find_service(updated, 0, "identity-service")
        assert svc.status == "failed"
        assert svc.error == "build error"


class TestComputePhaseStatus:
    def test_all_completed(self) -> None:
        ps = PhaseState(
            index=0,
            services=(
                ServiceStatus(slug="a", status="completed"),
                ServiceStatus(slug="b", status="completed"),
            ),
        )
        assert compute_phase_status(ps) == "completed"

    def test_partial(self) -> None:
        ps = PhaseState(
            index=0,
            services=(
                ServiceStatus(slug="a", status="completed"),
                ServiceStatus(slug="b", status="failed"),
            ),
        )
        assert compute_phase_status(ps) == "partial"

    def test_all_failed(self) -> None:
        ps = PhaseState(
            index=0,
            services=(
                ServiceStatus(slug="a", status="failed"),
                ServiceStatus(slug="b", status="failed"),
            ),
        )
        assert compute_phase_status(ps) == "failed"

    def test_in_progress(self) -> None:
        ps = PhaseState(
            index=0,
            services=(
                ServiceStatus(slug="a", status="completed"),
                ServiceStatus(slug="b", status="in-progress"),
            ),
        )
        assert compute_phase_status(ps) == "in-progress"


class TestAddVerificationResult:
    def test_append(self) -> None:
        state = create_initial_state(_make_plan())
        vr = VerificationResult(after_phase=0, passed=True)
        updated = add_verification_result(state, vr)
        assert len(updated.verification_results) == 1
        assert updated.verification_results[0].passed is True


class TestSaveAndLoad:
    def test_round_trip(self, tmp_path) -> None:
        state = create_initial_state(_make_plan())
        path = tmp_path / ".specforge" / "orchestration-state.json"
        save_result = save_state(path, state)
        assert save_result.ok
        load_result = load_state(path)
        assert load_result.ok
        loaded = load_result.value
        assert loaded.architecture == state.architecture
        assert loaded.status == state.status
        assert len(loaded.phases) == len(state.phases)

    def test_atomic_write_creates_parent_dirs(self, tmp_path) -> None:
        state = create_initial_state(_make_plan())
        path = tmp_path / "deep" / "nested" / "state.json"
        result = save_state(path, state)
        assert result.ok
        assert path.exists()

    def test_load_missing_returns_err(self, tmp_path) -> None:
        result = load_state(tmp_path / "nonexistent.json")
        assert not result.ok


class TestGetCompletedServices:
    def test_completed_from_phase_0(self) -> None:
        state = create_initial_state(_make_plan())
        state = mark_phase_in_progress(state, 0)
        state = mark_service_completed(state, 0, "identity-service", 10, 10)
        state = mark_service_completed(state, 0, "admin-service", 8, 8)
        completed = get_completed_services(state)
        assert set(completed) == {"identity-service", "admin-service"}


class TestDetectResumePoint:
    def test_resume_from_partial_phase(self) -> None:
        state = create_initial_state(_make_plan())
        state = mark_phase_in_progress(state, 0)
        state = mark_service_completed(state, 0, "identity-service", 10, 10)
        # admin-service still pending
        phase_idx, svc_slug = detect_resume_point(state)
        assert phase_idx == 0
        assert svc_slug == "admin-service"

    def test_resume_from_next_phase(self) -> None:
        state = create_initial_state(_make_plan())
        state = mark_phase_in_progress(state, 0)
        state = mark_service_completed(state, 0, "identity-service", 10, 10)
        state = mark_service_completed(state, 0, "admin-service", 8, 8)
        phase_idx, svc_slug = detect_resume_point(state)
        assert phase_idx == 1
        assert svc_slug is None  # start phase 1 from beginning


def _find_service(
    state: OrchestrationState, phase_idx: int, slug: str,
) -> ServiceStatus:
    for svc in state.phases[phase_idx].services:
        if svc.slug == slug:
            return svc
    msg = f"Service {slug} not found in phase {phase_idx}"
    raise ValueError(msg)
