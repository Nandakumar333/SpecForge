"""Unit tests for ResearchPhase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.research_phase import ResearchPhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="test", service_name="Test", architecture=arch,
        project_description="Test", domain="test",
        features=(FeatureInfo("001", "a", "A", "Desc", "P0", "core"),),
        dependencies=(), events=(), output_dir=tmp_path,
    )


class TestResearchPhase:
    def test_microservice_research_extras(self, tmp_path: Path) -> None:
        phase = ResearchPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        extras = ctx["adapter_research_extras"]
        topics = [e["topic"] for e in extras]
        assert any("api" in t.lower() or "service mesh" in t.lower() for t in topics)

    def test_monolith_research_extras(self, tmp_path: Path) -> None:
        phase = ResearchPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        extras = ctx["adapter_research_extras"]
        topics = [e["topic"] for e in extras]
        assert any("contention" in t.lower() or "dependency" in t.lower() for t in topics)

    def test_modular_monolith_research_extras(self, tmp_path: Path) -> None:
        phase = ResearchPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), ModularMonolithAdapter(), {}
        )
        extras = ctx["adapter_research_extras"]
        topics = [e["topic"] for e in extras]
        assert any("boundary" in t.lower() or "interface" in t.lower() for t in topics)

    def test_uses_spec_as_input(self, tmp_path: Path) -> None:
        phase = ResearchPhase()
        ctx = phase._build_context(
            _ctx(tmp_path), MicroserviceAdapter(),
            {"spec": "# Spec content"},
        )
        assert ctx["input_artifacts"]["spec"] == "# Spec content"

    def test_run_writes_artifact(self, tmp_path: Path) -> None:
        phase = ResearchPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Research")
        result = phase.run(
            _ctx(tmp_path), MicroserviceAdapter(), renderer, MagicMock(), {}
        )
        assert result.ok
        assert (tmp_path / "research.md").exists()
