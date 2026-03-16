"""ChecklistPhase — Phase 5: generate checklist.md with adapter items."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


class ChecklistPhase(BasePhase):
    """Generate checklist.md for artifact validation."""

    @property
    def name(self) -> str:
        return "checklist"

    @property
    def artifact_filename(self) -> str:
        return "checklist.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build checklist context with adapter extras."""
        return {
            "project_name": service_ctx.project_description,
            "date": "",
            "feature_name": service_ctx.service_name,
            "service": {
                "slug": service_ctx.service_slug,
                "name": service_ctx.service_name,
            },
            "architecture": service_ctx.architecture,
            "adapter_checklist": adapter.get_checklist_extras(),
            "input_artifacts": input_artifacts,
        }
