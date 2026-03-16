"""TasksPhase — Phase 6: generate tasks.md with arch-specific tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


class TasksPhase(BasePhase):
    """Generate tasks.md with ordered implementation tasks."""

    @property
    def name(self) -> str:
        return "tasks"

    @property
    def artifact_filename(self) -> str:
        return "tasks.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build tasks context with adapter extras."""
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
            "adapter_tasks": adapter.get_task_extras(),
            "input_artifacts": input_artifacts,
        }
