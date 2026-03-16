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
