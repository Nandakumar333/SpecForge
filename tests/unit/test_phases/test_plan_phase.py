"""Unit tests for PlanPhase with prompt injection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.plan_phase import PlanPhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="ledger-service",
        service_name="Ledger Service",
        architecture=arch,
        project_description="Finance app",
        domain="finance",
        features=(FeatureInfo("002", "accts", "Accounts", "Acct mgmt", "P1", "core"),),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


class TestPlanPhase:
    def test_microservice_has_5_sections(self, tmp_path: Path) -> None:
        phase = PlanPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert len(ctx["adapter_sections"]) == 5

    def test_monolith_no_docker(self, tmp_path: Path) -> None:
        phase = PlanPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        titles = [s["title"] for s in ctx["adapter_sections"]]
        assert "Containerization" not in titles
        assert "Shared Database" in titles

    def test_modular_monolith_has_boundary(self, tmp_path: Path) -> None:
        phase = PlanPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), ModularMonolithAdapter(), {}
        )
        titles = [s["title"] for s in ctx["adapter_sections"]]
        assert "Module Boundary Enforcement" in titles

    def test_prompt_context_injected(self, tmp_path: Path) -> None:
        phase = PlanPhase(prompt_context="Governance rules here")
        ctx = phase._build_context(
            _ctx(tmp_path), MicroserviceAdapter(), {}
        )
        assert ctx["prompt_context"] == "Governance rules here"

    def test_no_prompt_context_graceful(self, tmp_path: Path) -> None:
        """FR-065: graceful degradation when governance files absent."""
        phase = PlanPhase(prompt_context="")
        ctx = phase._build_context(
            _ctx(tmp_path), MicroserviceAdapter(), {}
        )
        assert ctx["prompt_context"] == ""

    def test_run_writes_plan(self, tmp_path: Path) -> None:
        phase = PlanPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Plan")
        result = phase.run(
            _ctx(tmp_path), MicroserviceAdapter(), renderer, MagicMock(), {}
        )
        assert result.ok
        assert (tmp_path / "plan.md").exists()
