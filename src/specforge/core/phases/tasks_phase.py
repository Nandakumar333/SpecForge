"""TasksPhase — Phase 6: generate tasks.md with arch-specific tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specforge.core.phases.base_phase import BasePhase
from specforge.core.task_generator import TaskGenerator

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.prompt_loader import PromptLoader
    from specforge.core.service_context import ServiceContext


class TasksPhase(BasePhase):
    """Generate tasks.md with ordered implementation tasks."""

    def __init__(self, prompt_loader: PromptLoader | None = None) -> None:
        self._prompt_loader = prompt_loader

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
        """Build tasks context using TaskGenerator pipeline."""
        plan_content = input_artifacts.get("plan", "")
        tasks_data: list[dict[str, Any]] = []
        phases_data: list[dict[str, Any]] = []

        if self._prompt_loader is not None:
            gen = TaskGenerator(self._prompt_loader)
            result = gen.generate_for_service(service_ctx, plan_content)
            if result.ok:
                tf = result.value
                tasks_data = [self._task_to_dict(t) for t in tf.tasks]
                phases_data = self._phases_to_list(tf.phases)

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
            "generated_tasks": tasks_data,
            "generated_phases": phases_data,
            "input_artifacts": input_artifacts,
        }

    @staticmethod
    def _task_to_dict(task: Any) -> dict[str, Any]:
        """Convert a TaskItem to a template-friendly dict."""
        return {
            "id": task.id,
            "description": task.description,
            "layer": task.layer,
            "effort": task.effort,
            "parallel": task.parallel,
            "dependencies": task.dependencies,
            "file_paths": task.file_paths,
            "governance_rules": task.governance_rules,
            "commit_message": task.commit_message,
            "service_scope": task.service_scope,
        }

    @staticmethod
    def _phases_to_list(
        phases: tuple[tuple[int, tuple[Any, ...]], ...],
    ) -> list[dict[str, Any]]:
        """Convert phase grouping to template-friendly dicts."""
        result: list[dict[str, Any]] = []
        for phase_num, phase_tasks in phases:
            result.append({
                "number": phase_num,
                "tasks": [TasksPhase._task_to_dict(t) for t in phase_tasks],
            })
        return result
