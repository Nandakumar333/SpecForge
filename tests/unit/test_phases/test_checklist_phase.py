"""Unit tests for ChecklistPhase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.checklist_phase import ChecklistPhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="test", service_name="Test", architecture=arch,
        project_description="Test", domain="test",
        features=(FeatureInfo("001", "a", "A", "Desc", "P0", "core"),),
        dependencies=(), events=(), output_dir=tmp_path,
    )


class TestChecklistPhase:
    def test_microservice_checklist(self, tmp_path: Path) -> None:
        phase = ChecklistPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        items = ctx["adapter_checklist"]
        assert len(items) >= 2

    def test_monolith_checklist(self, tmp_path: Path) -> None:
        phase = ChecklistPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        descs = [i["description"] for i in ctx["adapter_checklist"]]
        assert any("module" in d.lower() for d in descs)

    def test_modular_monolith_boundary_check(self, tmp_path: Path) -> None:
        phase = ChecklistPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), ModularMonolithAdapter(), {}
        )
        descs = [i["description"] for i in ctx["adapter_checklist"]]
        assert any("cross-module" in d.lower() and "db" in d.lower() for d in descs)

    def test_run_writes_artifact(self, tmp_path: Path) -> None:
        phase = ChecklistPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Checklist")
        result = phase.run(
            _ctx(tmp_path), MicroserviceAdapter(), renderer, MagicMock(), {}
        )
        assert result.ok
        assert (tmp_path / "checklist.md").exists()
