"""Tests for TaskGenerator — main task generation orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specforge.core.result import Err, Ok
from specforge.core.service_context import (
    EventInfo,
    FeatureInfo,
    ServiceContext,
    ServiceDependency,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "task_generation"


def _load_manifest(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _ctx(
    slug: str,
    arch: str = "microservice",
    features: tuple[FeatureInfo, ...] = (),
    deps: tuple[ServiceDependency, ...] = (),
    events: tuple[EventInfo, ...] = (),
    tmp_path: Path | None = None,
) -> ServiceContext:
    if not features:
        features = (
            FeatureInfo("001", "auth", "Auth", "Desc", "P0", "core"),
        )
    return ServiceContext(
        service_slug=slug,
        service_name=slug.replace("-", " ").title(),
        architecture=arch,
        project_description="Test",
        domain="test",
        features=features,
        dependencies=deps,
        events=events,
        output_dir=tmp_path or Path("/tmp/test"),
    )


def _identity_ctx(tmp_path: Path | None = None) -> ServiceContext:
    """identity-service: 0 deps, 0 events."""
    return _ctx(
        "identity-service",
        features=(
            FeatureInfo("001", "auth", "Auth", "JWT auth", "P0", "foundation"),
            FeatureInfo("002", "profile", "Profile", "Profiles", "P1", "core"),
        ),
        tmp_path=tmp_path,
    )


def _ledger_ctx(tmp_path: Path | None = None) -> ServiceContext:
    """ledger-service: 1 dep on identity, 1 event."""
    return _ctx(
        "ledger-service",
        features=(
            FeatureInfo("003", "accounts", "Accounts", "Desc", "P0", "core"),
            FeatureInfo("004", "txns", "Transactions", "Desc", "P0", "core"),
            FeatureInfo("005", "recon", "Reconciliation", "Desc", "P2", "support"),
        ),
        deps=(
            ServiceDependency(
                "identity-service", "Identity", "sync-grpc", True, "Auth",
            ),
        ),
        events=(
            EventInfo("TransactionCreated", "ledger-service",
                      ("analytics-service",), "tx data"),
        ),
        tmp_path=tmp_path,
    )


def _analytics_ctx(tmp_path: Path | None = None) -> ServiceContext:
    """analytics-service: 3 deps, 2 events."""
    return _ctx(
        "analytics-service",
        features=(
            FeatureInfo("006", "insights", "Insights", "Desc", "P1", "core"),
        ),
        deps=(
            ServiceDependency(
                "identity-service", "Identity", "sync-grpc", True, "Auth",
            ),
            ServiceDependency(
                "ledger-service", "Ledger", "sync-grpc", True, "Query txns",
            ),
            ServiceDependency(
                "notification-service", "Notify", "sync-rest", False, "Alerts",
            ),
        ),
        events=(
            EventInfo("TransactionCreated", "ledger-service",
                      ("analytics-service",), "tx data"),
            EventInfo("AnalyticsRequested", "analytics-service",
                      ("ledger-service",), "report request"),
        ),
        tmp_path=tmp_path,
    )


def _make_generator():
    """Create a TaskGenerator with mocked dependencies."""
    from specforge.core.task_generator import TaskGenerator

    mock_loader = MagicMock()
    mock_loader.load_for_feature.return_value = Err("No governance files")
    return TaskGenerator(prompt_loader=mock_loader)


class TestIdentityService:
    """identity-service: 0 deps → steps 6, 8, 10 omitted."""

    def test_generates_tasks(self) -> None:
        gen = _make_generator()
        ctx = _identity_ctx()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        assert result.ok

    def test_no_communication_clients(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _identity_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        tf = result.value
        cats = [t.layer for t in tf.tasks]
        assert "communication_clients" not in cats

    def test_no_contract_tests(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _identity_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        tf = result.value
        cats = [t.layer for t in tf.tasks]
        assert "contract_tests" not in cats

    def test_no_event_handlers(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _identity_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        tf = result.value
        cats = [t.layer for t in tf.tasks]
        assert "event_handlers" not in cats

    def test_file_paths_use_service_prefix(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _identity_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        for task in result.value.tasks:
            for fp in task.file_paths:
                assert "identity-service" in fp or fp.startswith("infrastructure/")

    def test_sequential_task_ids(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _identity_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        ids = [t.id for t in result.value.tasks]
        for i, tid in enumerate(ids):
            assert tid == f"T{i + 1:03d}"


class TestLedgerService:
    """ledger-service: 1 dep on identity → step 6 present."""

    def test_communication_clients_present(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        tf = result.value
        comm_tasks = [t for t in tf.tasks if t.layer == "communication_clients"]
        assert len(comm_tasks) >= 1

    def test_comm_client_mentions_identity(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        comm_tasks = [t for t in result.value.tasks
                      if t.layer == "communication_clients"]
        descs = " ".join(t.description for t in comm_tasks)
        assert "identity-service" in descs.lower() or "identity" in descs.lower()

    def test_comm_client_depends_on_service_layer(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        tf = result.value
        svc_task = next(t for t in tf.tasks if t.layer == "service_layer")
        comm_tasks = [t for t in tf.tasks if t.layer == "communication_clients"]
        for ct in comm_tasks:
            assert svc_task.id in ct.dependencies

    def test_contract_tests_present(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        ct = [t for t in result.value.tasks if t.layer == "contract_tests"]
        assert len(ct) >= 1

    def test_event_handlers_present(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        eh = [t for t in result.value.tasks if t.layer == "event_handlers"]
        assert len(eh) >= 1


class TestAnalyticsService:
    """analytics-service: 3 deps, 2 events."""

    def test_three_comm_client_tasks(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _analytics_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        comm_tasks = [t for t in result.value.tasks
                      if t.layer == "communication_clients"]
        assert len(comm_tasks) == 3

    def test_two_event_handler_tasks(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _analytics_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        eh = [t for t in result.value.tasks if t.layer == "event_handlers"]
        assert len(eh) == 2

    def test_three_contract_test_tasks(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _analytics_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        ct = [t for t in result.value.tasks if t.layer == "contract_tests"]
        assert len(ct) == 3

    def test_comm_clients_effort_bumped(self) -> None:
        """3 deps > threshold 2 → bump M to L."""
        gen = _make_generator()
        result = gen.generate_for_service(
            _analytics_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        comm_tasks = [t for t in result.value.tasks
                      if t.layer == "communication_clients"]
        for ct in comm_tasks:
            assert ct.effort in ("L", "XL")


class TestStepFiltering:
    """FR-014: Omit inapplicable tasks."""

    def test_no_deps_omits_comm_clients(self) -> None:
        gen = _make_generator()
        ctx = _ctx("no-deps-svc", deps=())
        result = gen.generate_for_service(
            ctx, (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        cats = [t.layer for t in result.value.tasks]
        assert "communication_clients" not in cats

    def test_no_events_omits_event_handlers(self) -> None:
        gen = _make_generator()
        ctx = _ctx("no-events-svc", events=())
        result = gen.generate_for_service(
            ctx, (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        cats = [t.layer for t in result.value.tasks]
        assert "event_handlers" not in cats

    def test_no_deps_omits_contract_tests(self) -> None:
        gen = _make_generator()
        ctx = _ctx("no-deps-svc", deps=())
        result = gen.generate_for_service(
            ctx, (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        cats = [t.layer for t in result.value.tasks]
        assert "contract_tests" not in cats


class TestTaskCap:
    """FR-018: 50-task cap."""

    def test_under_cap(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_service(
            _ledger_ctx(),
            (FIXTURES / "sample_plan.md").read_text(encoding="utf-8"),
        )
        assert result.value.total_count <= 50


class TestMonolithMode:
    """US3: Monolith 7-step sequence, no microservice concerns."""

    def _mono_ctx(
        self, slug: str = "auth", arch: str = "monolithic",
    ) -> ServiceContext:
        return ServiceContext(
            service_slug=slug, service_name="Auth Module",
            architecture=arch, project_description="Test",
            domain="test",
            features=(
                FeatureInfo("001", "auth", "Auth", "Session auth", "P0", "core"),
                FeatureInfo("002", "profile", "Profile", "Profiles", "P1", "core"),
            ),
            dependencies=(), events=(), output_dir=Path("/tmp"),
        )

    def test_monolith_7_categories(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        assert result.ok
        cats = sorted(set(t.layer for t in result.value.tasks))
        expected = sorted([
            "folder_structure", "domain_models", "database",
            "repo_service", "controllers", "tests",
        ])
        # boundary_interface is conditional on modular-monolith
        assert cats == expected

    def test_no_microservice_categories(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        forbidden = {
            "communication_clients", "event_handlers", "health_checks",
            "contract_tests", "container_optimization", "gateway_config",
            "scaffolding",
        }
        cats = {t.layer for t in result.value.tasks}
        assert cats & forbidden == set()

    def test_shared_dbcontext_in_database_task(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        db_tasks = [t for t in result.value.tasks if t.layer == "database"]
        assert len(db_tasks) >= 1
        desc = db_tasks[0].description.lower()
        assert "shared" in desc or "dbcontext" in desc.replace(" ", "")

    def test_modular_monolith_has_boundary_interface(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx("auth", "modular-monolith")
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        cats = [t.layer for t in result.value.tasks]
        assert "boundary_interface" in cats

    def test_plain_monolith_no_boundary_interface(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx("auth", "monolithic")
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        cats = [t.layer for t in result.value.tasks]
        assert "boundary_interface" not in cats

    def test_module_file_paths(self) -> None:
        gen = _make_generator()
        ctx = self._mono_ctx()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        result = gen.generate_for_service(ctx, plan)
        for task in result.value.tasks:
            for fp in task.file_paths:
                assert "auth" in fp


class TestDeterminism:
    """Same input → same task order every time."""

    def test_deterministic_output(self) -> None:
        gen = _make_generator()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        ctx = _ledger_ctx()
        results = []
        for _ in range(5):
            result = gen.generate_for_service(ctx, plan)
            results.append([t.id for t in result.value.tasks])
        assert all(r == results[0] for r in results)


class TestGenerateForProject:
    """US5: Full project generation with cross-service infra."""

    def test_cross_service_file_included(self) -> None:
        gen = _make_generator()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        services = [_identity_ctx(), _ledger_ctx(), _analytics_ctx()]
        result = gen.generate_for_project(services, plan)
        assert result.ok
        assert "cross-service-infra" in result.value.generated_files

    def test_all_services_in_output(self) -> None:
        gen = _make_generator()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        services = [_identity_ctx(), _ledger_ctx()]
        result = gen.generate_for_project(services, plan)
        names = result.value.generated_files
        assert "identity-service" in names
        assert "ledger-service" in names

    def test_empty_services_returns_error(self) -> None:
        gen = _make_generator()
        result = gen.generate_for_project([], "plan")
        assert not result.ok

    def test_monolith_no_cross_service(self) -> None:
        gen = _make_generator()
        plan = (FIXTURES / "sample_plan.md").read_text(encoding="utf-8")
        mono = _ctx("auth", arch="monolithic")
        result = gen.generate_for_project([mono], plan)
        assert result.ok
        assert "cross-service-infra" not in result.value.generated_files
