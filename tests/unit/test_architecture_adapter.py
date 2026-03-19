"""Unit tests for ArchitectureAdapter protocol and 3 implementations."""

from __future__ import annotations

from pathlib import Path

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
    create_adapter,
)
from specforge.core.service_context import (
    EventInfo,
    FeatureInfo,
    ServiceContext,
    ServiceDependency,
)


def _make_context(architecture: str = "microservice") -> ServiceContext:
    """Build a minimal ServiceContext for testing."""
    return ServiceContext(
        service_slug="ledger-service",
        service_name="Ledger Service",
        architecture=architecture,
        project_description="Finance app",
        domain="finance",
        features=(
            FeatureInfo("002", "accounts", "Accounts", "Account mgmt", "P1", "core"),
            FeatureInfo("003", "transactions", "Transactions", "Txn mgmt", "P1", "core"),
        ),
        dependencies=(
            ServiceDependency(
                "identity-service", "Identity Service",
                "sync-rest", True, "Auth validation",
            ),
        ),
        events=(
            EventInfo("txn.created", "ledger-service", ("identity-service",), "Txn data"),
        ),
        output_dir=Path(".specforge/features/ledger-service"),
    )


class TestCreateAdapter:
    """Tests for create_adapter() factory."""

    def test_microservice(self) -> None:
        adapter = create_adapter("microservice")
        assert isinstance(adapter, MicroserviceAdapter)

    def test_monolithic(self) -> None:
        adapter = create_adapter("monolithic")
        assert isinstance(adapter, MonolithAdapter)

    def test_modular_monolith(self) -> None:
        adapter = create_adapter("modular-monolith")
        assert isinstance(adapter, ModularMonolithAdapter)

    def test_unknown_defaults_to_monolith(self) -> None:
        adapter = create_adapter("unknown")
        assert isinstance(adapter, MonolithAdapter)


class TestMicroserviceAdapter:
    """Tests for MicroserviceAdapter."""

    def test_get_context_includes_deps(self) -> None:
        adapter = MicroserviceAdapter()
        ctx = _make_context("microservice")
        result = adapter.get_context(ctx)
        assert "dependencies" in result
        assert len(result["dependencies"]) == 1
        assert "communication_patterns" in result
        assert "events" in result

    def test_get_datamodel_context(self) -> None:
        adapter = MicroserviceAdapter()
        ctx = _make_context("microservice")
        result = adapter.get_datamodel_context(ctx)
        assert result["entity_scope"] == "isolated"
        assert result["cross_service_ref"] == "api_contract"
        assert result["shared_entities"] is False

    def test_get_research_extras(self) -> None:
        adapter = MicroserviceAdapter()
        extras = adapter.get_research_extras()
        assert len(extras) >= 2
        topics = [e["topic"] for e in extras]
        assert any("service mesh" in t.lower() or "api" in t.lower() for t in topics)

    def test_get_plan_sections_has_5(self) -> None:
        adapter = MicroserviceAdapter()
        sections = adapter.get_plan_sections()
        assert len(sections) == 5
        titles = [s["title"] for s in sections]
        assert "Containerization" in titles
        assert "Health Checks" in titles
        assert "Service Registration" in titles
        assert "Circuit Breakers" in titles
        assert "API Gateway" in titles

    def test_get_task_extras(self) -> None:
        adapter = MicroserviceAdapter()
        tasks = adapter.get_task_extras()
        assert len(tasks) >= 3

    def test_get_edge_case_extras(self) -> None:
        adapter = MicroserviceAdapter()
        cases = adapter.get_edge_case_extras()
        assert len(cases) >= 4
        names = [c["name"] for c in cases]
        assert "Service Down" in names
        assert "Network Partition" in names

    def test_get_checklist_extras(self) -> None:
        adapter = MicroserviceAdapter()
        items = adapter.get_checklist_extras()
        assert len(items) >= 2

    def test_serialize_for_prompt_contains_architecture_terms(self) -> None:
        adapter = MicroserviceAdapter()
        result = adapter.serialize_for_prompt()
        assert "## Architecture: Microservice" in result
        assert "Docker container" in result
        assert "health check endpoint" in result
        assert "gRPC" in result
        assert "circuit breaker" in result
        assert "service discovery" in result


class TestMonolithAdapter:
    """Tests for MonolithAdapter."""

    def test_get_context_includes_module(self) -> None:
        adapter = MonolithAdapter()
        ctx = _make_context("monolithic")
        result = adapter.get_context(ctx)
        assert "module_context" in result
        assert "shared_infrastructure" in result

    def test_get_datamodel_context(self) -> None:
        adapter = MonolithAdapter()
        ctx = _make_context("monolithic")
        result = adapter.get_datamodel_context(ctx)
        assert result["entity_scope"] == "module"
        assert result["cross_service_ref"] == "shared_table"
        assert result["shared_entities"] is True

    def test_get_research_extras(self) -> None:
        adapter = MonolithAdapter()
        extras = adapter.get_research_extras()
        assert len(extras) >= 1

    def test_get_plan_sections_no_docker(self) -> None:
        adapter = MonolithAdapter()
        sections = adapter.get_plan_sections()
        titles = [s["title"] for s in sections]
        assert "Containerization" not in titles
        assert "Shared Database" in titles

    def test_get_task_extras_no_container(self) -> None:
        adapter = MonolithAdapter()
        tasks = adapter.get_task_extras()
        names = [t["name"] for t in tasks]
        assert not any("container" in n.lower() for n in names)

    def test_get_edge_case_extras(self) -> None:
        adapter = MonolithAdapter()
        cases = adapter.get_edge_case_extras()
        names = [c["name"] for c in cases]
        assert "Module Boundary Violation" in names

    def test_get_checklist_extras(self) -> None:
        adapter = MonolithAdapter()
        items = adapter.get_checklist_extras()
        assert len(items) >= 1

    def test_serialize_for_prompt_contains_architecture_terms(self) -> None:
        adapter = MonolithAdapter()
        result = adapter.serialize_for_prompt()
        assert "## Architecture: Monolithic" in result
        assert "Shared database" in result
        assert "No Docker" in result
        assert "internal module imports" in result


class TestModularMonolithAdapter:
    """Tests for ModularMonolithAdapter."""

    def test_inherits_monolith_plan_sections(self) -> None:
        adapter = ModularMonolithAdapter()
        sections = adapter.get_plan_sections()
        titles = [s["title"] for s in sections]
        assert "Shared Database" in titles
        assert "Module Boundary Enforcement" in titles

    def test_get_datamodel_context_strict(self) -> None:
        adapter = ModularMonolithAdapter()
        ctx = _make_context("modular-monolith")
        result = adapter.get_datamodel_context(ctx)
        assert result["entity_scope"] == "strict_module"
        assert result["cross_service_ref"] == "interface_contract"
        assert result["shared_entities"] is True
        assert result["no_cross_module_db"] is True

    def test_get_research_extras_adds_boundary(self) -> None:
        adapter = ModularMonolithAdapter()
        extras = adapter.get_research_extras()
        topics = [e["topic"] for e in extras]
        assert any("boundary" in t.lower() or "interface" in t.lower() for t in topics)

    def test_get_edge_case_extras_adds_interface(self) -> None:
        adapter = ModularMonolithAdapter()
        cases = adapter.get_edge_case_extras()
        names = [c["name"] for c in cases]
        assert "Module Boundary Violation" in names
        assert "Interface Contract Violation" in names

    def test_get_checklist_extras_adds_db_check(self) -> None:
        adapter = ModularMonolithAdapter()
        items = adapter.get_checklist_extras()
        descs = [i["description"] for i in items]
        assert any("cross-module" in d.lower() and "db" in d.lower() for d in descs)

    def test_no_containerization(self) -> None:
        adapter = ModularMonolithAdapter()
        sections = adapter.get_plan_sections()
        titles = [s["title"] for s in sections]
        assert "Containerization" not in titles

    def test_serialize_for_prompt_contains_architecture_terms(self) -> None:
        adapter = ModularMonolithAdapter()
        result = adapter.serialize_for_prompt()
        assert "## Architecture: Modular Monolith" in result
        assert "Strict module boundaries" in result
        assert "interface contracts" in result
        assert "No Docker" in result
        assert "schema boundaries per module" in result
