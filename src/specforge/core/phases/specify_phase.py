"""SpecifyPhase — Phase 1: generate spec.md with domain capability grouping."""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import FeatureInfo, ServiceContext

_CAPABILITY_THRESHOLD = 4


class SpecifyPhase(BasePhase):
    """Generate spec.md organized by domain capability."""

    @property
    def name(self) -> str:
        return "spec"

    @property
    def artifact_filename(self) -> str:
        return "spec.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build spec context with domain capabilities."""
        capabilities = _group_capabilities(service_ctx.features)
        ctx: dict[str, Any] = {
            "project_name": service_ctx.project_description,
            "date": "",
            "feature_name": service_ctx.service_name,
            "service": {
                "slug": service_ctx.service_slug,
                "name": service_ctx.service_name,
            },
            "architecture": service_ctx.architecture,
            "features": [_feature_dict(f) for f in service_ctx.features],
            "capabilities": capabilities,
        }
        ctx.update(adapter.get_context(service_ctx))
        return ctx


def _group_capabilities(
    features: tuple[FeatureInfo, ...],
) -> list[dict[str, Any]]:
    """Group features into domain capabilities."""
    if len(features) < _CAPABILITY_THRESHOLD:
        return [
            {
                "name": f.display_name,
                "features": [_feature_dict(f)],
            }
            for f in features
        ]
    sorted_feats = sorted(features, key=lambda f: f.category)
    groups: list[dict[str, Any]] = []
    for _cat, group_iter in groupby(sorted_feats, key=lambda f: f.category):
        group = list(group_iter)
        groups.append(
            {
                "name": group[0].display_name,
                "features": [_feature_dict(f) for f in group],
            }
        )
    return groups


def _feature_dict(f: FeatureInfo) -> dict[str, str]:
    """Convert FeatureInfo to template-friendly dict."""
    return {
        "id": f.id,
        "name": f.name,
        "display_name": f.display_name,
        "description": f.description,
        "priority": f.priority,
        "category": f.category,
    }
