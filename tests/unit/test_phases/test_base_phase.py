"""Unit tests for BasePhase template method."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import MonolithAdapter
from specforge.core.phases.base_phase import BasePhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _make_ctx(tmp_path: Path) -> ServiceContext:
    return ServiceContext(
        service_slug="test-service",
        service_name="Test Service",
        architecture="monolithic",
        project_description="Test",
        domain="test",
        features=(FeatureInfo("001", "auth", "Auth", "Login", "P0", "foundation"),),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


class ConcretePhase(BasePhase):
    """Concrete test implementation of BasePhase."""

    @property
    def name(self) -> str:
        return "spec"

    @property
    def artifact_filename(self) -> str:
        return "spec.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: Any,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "project_name": service_ctx.project_description,
            "date": "2026-03-16",
            "feature_name": service_ctx.service_name,
        }


class TestBasePhase:
    """Tests for BasePhase.run()."""

    def test_run_renders_and_writes(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        adapter = MonolithAdapter()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Spec\nContent here")
        registry = MagicMock()

        phase = ConcretePhase()
        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok
        artifact_path = result.value
        assert artifact_path.exists()
        assert artifact_path.name == "spec.md"
        content = artifact_path.read_text(encoding="utf-8")
        assert "Spec" in content

    def test_run_creates_output_dir(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "nested" / "dir"
        ctx = ServiceContext(
            service_slug="test",
            service_name="Test",
            architecture="monolithic",
            project_description="Test",
            domain="test",
            features=(FeatureInfo("001", "a", "A", "Desc", "P0", "core"),),
            dependencies=(),
            events=(),
            output_dir=out_dir,
        )
        renderer = MagicMock()
        renderer.render.return_value = Ok("content")

        phase = ConcretePhase()
        result = phase.run(ctx, MonolithAdapter(), renderer, MagicMock(), {})

        assert result.ok
        assert out_dir.exists()
