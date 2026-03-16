"""DatamodelPhase — Phase 3a: generate data-model.md with boundary scoping."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from specforge.core.config import SHARED_ENTITIES_PATH
from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


class DatamodelPhase(BasePhase):
    """Generate data-model.md scoped to service boundary."""

    @property
    def name(self) -> str:
        return "datamodel"

    @property
    def artifact_filename(self) -> str:
        return "data-model.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build data model context with adapter scoping."""
        dm_ctx = adapter.get_datamodel_context(service_ctx)
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
            "datamodel_context": dm_ctx,
            "input_artifacts": input_artifacts,
        }

    def _post_render(
        self, service_ctx: ServiceContext, artifact_path: Path
    ) -> None:
        """Create shared_entities.md for monolith/modular-monolith."""
        if service_ctx.architecture == "microservice":
            return
        project_root = _find_project_root(service_ctx.output_dir)
        shared_path = project_root / SHARED_ENTITIES_PATH
        if not shared_path.exists():
            shared_path.parent.mkdir(parents=True, exist_ok=True)
            shared_path.write_text(
                _shared_entities_stub(service_ctx), encoding="utf-8"
            )


def _find_project_root(output_dir: Path) -> Path:
    """Derive project root from output dir (.specforge/features/<slug>)."""
    return output_dir.parent.parent.parent


def _shared_entities_stub(service_ctx: ServiceContext) -> str:
    """Generate initial shared_entities.md content."""
    lines = [
        "# Shared Entities",
        "",
        f"Project: {service_ctx.project_description}",
        f"Architecture: {service_ctx.architecture}",
        "",
        "## Entities Spanning Multiple Modules",
        "",
        "<!-- Add shared entities here as modules are specified -->",
        "",
    ]
    return "\n".join(lines)
