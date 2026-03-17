"""Integration tests for EdgecasePhase — full pipeline with real templates."""

from __future__ import annotations

from pathlib import Path

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    MonolithAdapter,
)
from specforge.core.phases.edgecase_phase import EdgecasePhase
from specforge.core.service_context import FeatureInfo, ServiceContext
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer


def _registry_and_renderer() -> tuple[TemplateRegistry, TemplateRenderer]:
    """Create real registry + renderer backed by built-in templates."""
    registry = TemplateRegistry()
    registry.discover()
    renderer = TemplateRenderer(registry)
    return registry, renderer


def _service_ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="payments",
        service_name="Payments",
        architecture=arch,
        project_description="E-Commerce Platform",
        domain="commerce",
        features=(
            FeatureInfo("001", "checkout", "Checkout", "Process orders", "P0", "core"),
        ),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


class TestEdgecasePhaseIntegration:
    def test_phase_run_writes_edge_cases_md(self, tmp_path: Path) -> None:
        """Full phase run with TemplateRegistry + TemplateRenderer."""
        registry, renderer = _registry_and_renderer()
        phase = EdgecasePhase()
        ctx = _service_ctx(tmp_path, "microservice")
        adapter = MicroserviceAdapter()

        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok, f"Phase run failed: {getattr(result, 'error', '')}"
        md_path = tmp_path / "edge-cases.md"
        assert md_path.exists(), "edge-cases.md not written"
        content = md_path.read_text(encoding="utf-8")
        assert "Edge Cases" in content
        assert "Payments" in content
        assert "EC-" in content

    def test_monolith_phase_run_writes_standard_cases(self, tmp_path: Path) -> None:
        """Monolith produces edge-cases.md with standard categories only."""
        registry, renderer = _registry_and_renderer()
        phase = EdgecasePhase()
        ctx = _service_ctx(tmp_path, "monolithic")
        adapter = MonolithAdapter()

        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok, f"Phase run failed: {getattr(result, 'error', '')}"
        md_path = tmp_path / "edge-cases.md"
        assert md_path.exists(), "edge-cases.md not written"
        content = md_path.read_text(encoding="utf-8")
        assert "Edge Cases" in content
        assert "EC-" in content
        # Monolith should NOT have microservice-specific categories
        assert "network_partition" not in content
        assert "distributed_transaction" not in content
