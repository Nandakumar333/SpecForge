"""EdgecasePhase — Phase 3b: generate edge-cases.md with arch-specific scenarios."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from specforge.core.edge_case_analyzer import EdgeCaseAnalyzer
from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_models import EdgeCase
from specforge.core.edge_case_patterns import PatternLoader
from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


def _edge_case_to_dict(ec: EdgeCase) -> dict[str, Any]:
    """Convert an EdgeCase dataclass to a plain dict for templates."""
    return {
        "id": ec.id,
        "category": ec.category,
        "severity": ec.severity,
        "scenario": ec.scenario,
        "trigger": ec.trigger,
        "affected_services": list(ec.affected_services),
        "handling_strategy": ec.handling_strategy,
        "test_suggestion": ec.test_suggestion,
    }


class EdgecasePhase(BasePhase):
    """Generate edge-cases.md with architecture-specific failure scenarios."""

    @property
    def name(self) -> str:
        return "edgecase"

    @property
    def artifact_filename(self) -> str:
        return "edge-cases.md"

    def _template_name(self) -> str:
        return "edge-cases"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build edge case context with adapter extras and analyzer results."""
        ctx: dict[str, Any] = {
            "project_name": service_ctx.project_description,
            "date": "",
            "feature_name": service_ctx.service_name,
            "service": {
                "slug": service_ctx.service_slug,
                "name": service_ctx.service_name,
            },
            "architecture": service_ctx.architecture,
            "features": [
                {"display_name": f.display_name, "description": f.description}
                for f in service_ctx.features
            ],
            "adapter_edge_cases": adapter.get_edge_case_extras(),
            "input_artifacts": input_artifacts,
        }
        edge_cases = self._analyzer_edge_cases(service_ctx)
        if edge_cases is not None:
            ctx["edge_cases"] = edge_cases
        return ctx

    def _analyzer_edge_cases(
        self,
        service_ctx: ServiceContext,
    ) -> list[dict[str, Any]] | None:
        """Run EdgeCaseAnalyzer; return list of dicts or None on failure."""
        loader = PatternLoader()
        load_result = loader.load_patterns()
        if not load_result.ok:
            warnings.warn(
                f"Edge case pattern loading failed: {load_result.error}",
                UserWarning,
                stacklevel=2,
            )
            return None
        arch_filter = ArchitectureEdgeCaseFilter(service_ctx.architecture)
        budget = EdgeCaseBudget()
        analyzer = EdgeCaseAnalyzer(load_result.value, arch_filter, budget)
        result = analyzer.analyze(service_ctx)
        if not result.ok:
            warnings.warn(
                f"Edge case analysis failed: {result.error}",
                UserWarning,
                stacklevel=2,
            )
            return None
        return [_edge_case_to_dict(ec) for ec in result.value.edge_cases]
