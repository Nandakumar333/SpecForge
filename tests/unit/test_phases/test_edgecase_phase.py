"""Unit tests for EdgecasePhase architecture-specific scenarios."""

from __future__ import annotations

from pathlib import Path

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.edgecase_phase import EdgecasePhase
from specforge.core.service_context import FeatureInfo, ServiceContext

_EXPECTED_EDGE_CASE_FIELDS = {
    "id", "category", "severity", "scenario", "trigger",
    "affected_services", "handling_strategy", "test_suggestion",
}


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="test", service_name="Test", architecture=arch,
        project_description="Test", domain="test",
        features=(FeatureInfo("001", "a", "A", "Desc", "P0", "core"),),
        dependencies=(), events=(), output_dir=tmp_path,
    )


class TestEdgecasePhase:
    def test_microservice_includes_distributed(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        names = [c["name"] for c in ctx["adapter_edge_cases"]]
        assert "Service Down" in names
        assert "Network Partition" in names
        assert "Eventual Consistency" in names
        assert "Timeout Handling" in names

    def test_monolith_boundary_violations(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        names = [c["name"] for c in ctx["adapter_edge_cases"]]
        assert "Module Boundary Violation" in names

    def test_modular_monolith_interface_violations(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), ModularMonolithAdapter(), {}
        )
        names = [c["name"] for c in ctx["adapter_edge_cases"]]
        assert "Module Boundary Violation" in names
        assert "Interface Contract Violation" in names

    def test_context_includes_edge_cases_key(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert "edge_cases" in ctx
        assert len(ctx["edge_cases"]) > 0

    def test_edge_cases_are_list_of_dicts(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert isinstance(ctx["edge_cases"], list)
        for ec in ctx["edge_cases"]:
            assert isinstance(ec, dict)
            assert "id" in ec
            assert "category" in ec
            assert "severity" in ec

    def test_monolith_has_edge_cases_key(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        assert "edge_cases" in ctx
        assert len(ctx["edge_cases"]) > 0

    def test_adapter_edge_cases_still_present(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert "adapter_edge_cases" in ctx
        assert isinstance(ctx["adapter_edge_cases"], list)
        assert len(ctx["adapter_edge_cases"]) > 0

    def test_edge_case_dict_has_all_fields(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        for ec in ctx["edge_cases"]:
            assert set(ec.keys()) == _EXPECTED_EDGE_CASE_FIELDS

    def test_affected_services_is_list(self, tmp_path: Path) -> None:
        phase = EdgecasePhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        for ec in ctx["edge_cases"]:
            assert isinstance(ec["affected_services"], list)
