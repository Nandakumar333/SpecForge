"""PlanPhase — Phase 4: generate plan.md with prompt injection and arch sections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


class PlanPhase(BasePhase):
    """Generate plan.md with governance prompt injection."""

    def __init__(
        self,
        prompt_context: str = "",
    ) -> None:
        self._prompt_context = prompt_context

    @property
    def name(self) -> str:
        return "plan"

    @property
    def artifact_filename(self) -> str:
        return "plan.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build plan context with adapter sections and prompts."""
        return {
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
            "adapter_sections": adapter.get_plan_sections(),
            "prompt_context": self._prompt_context,
            "input_artifacts": input_artifacts,
        }
