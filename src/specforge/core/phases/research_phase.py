"""ResearchPhase — Phase 2: generate research.md with arch-specific questions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext


class ResearchPhase(BasePhase):
    """Generate research.md using spec.md as input context."""

    @property
    def name(self) -> str:
        return "research"

    @property
    def artifact_filename(self) -> str:
        return "research.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build research context with adapter extras."""
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
            "adapter_research_extras": adapter.get_research_extras(),
            "input_artifacts": input_artifacts,
        }

    def _build_prompt(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, str]:
        """Build extra LLM prompt context for research generation."""
        extras = adapter.get_research_extras()
        topic_lines = "\n".join(
            f"- {e.get('topic', e.get('title', ''))}: "
            f"{e.get('description', e.get('detail', ''))}"
            for e in extras
        ) if extras else "No architecture-specific research topics."

        dep_lines = "\n".join(
            f"- {d.target_name} ({d.pattern}): {d.description}"
            for d in service_ctx.dependencies
        ) if service_ctx.dependencies else "No external dependencies."

        return {
            "tech_stack_questions": (
                f"Architecture: {service_ctx.architecture}\n"
                f"Investigate technology choices and trade-offs for "
                f"'{service_ctx.service_name}' in this architecture style."
            ),
            "integration_concerns": (
                f"Service dependencies to research:\n{dep_lines}"
            ),
            "adapter_research_topics": (
                f"Architecture-specific research areas:\n{topic_lines}"
            ),
        }
