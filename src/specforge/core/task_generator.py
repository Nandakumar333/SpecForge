"""TaskGenerator — main orchestrator for task generation (Feature 008)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from specforge.core.build_sequence import get_sequence
from specforge.core.config import (
    CONDITIONAL_STEPS,
    CROSS_SERVICE_TARGET,
    MAX_TASKS_PER_SERVICE,
    TASK_ID_PREFIX,
)
from specforge.core.cross_service_tasks import CrossServiceTaskGenerator
from specforge.core.dependency_resolver import DependencyResolver
from specforge.core.effort_estimator import EffortEstimator
from specforge.core.governance_reader import GovernanceReader
from specforge.core.result import Err, Ok, Result
from specforge.core.task_models import (
    BuildStep,
    GenerationSummary,
    TaskFile,
    TaskItem,
)

if TYPE_CHECKING:
    from specforge.core.prompt_loader import PromptLoader
    from specforge.core.service_context import ServiceContext


class TaskGenerator:
    """Generates ordered, dependency-aware task files per service."""

    def __init__(self, prompt_loader: PromptLoader) -> None:
        self._estimator = EffortEstimator()
        self._resolver = DependencyResolver()
        self._governance = GovernanceReader(prompt_loader)

    def generate_for_service(
        self, ctx: ServiceContext, plan_content: str,
    ) -> Result:
        """Generate a TaskFile for a single service/module."""
        sequence = get_sequence(ctx.architecture)
        filtered = self._filter_steps(sequence, ctx)
        tasks = self._generate_tasks(filtered, ctx)
        tasks = self._assign_effort(tasks, ctx)
        tasks = self._assign_governance(tasks, ctx)
        graph_result = self._resolver.build_graph(tasks)
        if not graph_result.ok:
            return graph_result
        graph = graph_result.value
        ordered = self._resolver.topological_sort(graph)
        ordered = self._resolver.mark_parallel(ordered, graph)
        ordered = self._renumber(ordered)
        if len(ordered) > MAX_TASKS_PER_SERVICE:
            ordered = ordered[:MAX_TASKS_PER_SERVICE]
        return Ok(self._build_task_file(ordered, ctx))

    def _filter_steps(
        self,
        sequence: tuple[BuildStep, ...],
        ctx: ServiceContext,
    ) -> list[BuildStep]:
        """Remove inapplicable steps based on service context."""
        result: list[BuildStep] = []
        for step in sequence:
            condition = CONDITIONAL_STEPS.get(step.category)
            if condition and not self._meets_condition(condition, ctx):
                continue
            result.append(step)
        return result

    def _meets_condition(
        self, condition: str, ctx: ServiceContext,
    ) -> bool:
        """Check whether a conditional step applies."""
        if condition == "dependencies":
            return len(ctx.dependencies) > 0
        if condition == "events":
            return len(ctx.events) > 0
        if condition == "modular-monolith":
            return ctx.architecture == "modular-monolith"
        if condition == "entities":
            return True  # assume entities if features exist
        return True

    def _generate_tasks(
        self,
        steps: list[BuildStep],
        ctx: ServiceContext,
    ) -> list[TaskItem]:
        """Create TaskItems from filtered build steps."""
        tasks: list[TaskItem] = []
        step_id_map: dict[int, str] = {}
        counter = 1

        for step in steps:
            sub_tasks = self._expand_step(step, ctx, counter, step_id_map)
            for t in sub_tasks:
                step_id_map[step.order] = (
                    step_id_map.get(step.order, t.id)
                )
                tasks.append(t)
                counter += 1
        return tasks

    def _expand_step(
        self,
        step: BuildStep,
        ctx: ServiceContext,
        counter: int,
        step_id_map: dict[int, str],
    ) -> list[TaskItem]:
        """Expand a BuildStep into one or more TaskItems."""
        slug = ctx.service_slug
        placeholder = "service" if "microservice" in ctx.architecture else "module"
        desc_base = step.description_template.replace(
            f"{{{placeholder}}}", slug,
        ).replace("{service}", slug).replace("{module}", slug)
        file_path = step.file_path_pattern.replace(
            "{service}", slug,
        ).replace("{module}", slug)

        deps = self._resolve_step_deps(step, step_id_map)

        if step.category == "communication_clients":
            return self._expand_comm_clients(
                step, ctx, counter, deps, file_path,
            )
        if step.category == "event_handlers":
            return self._expand_events(
                step, ctx, counter, deps, file_path,
            )
        if step.category == "contract_tests":
            return self._expand_contract_tests(
                step, ctx, counter, deps, file_path,
            )
        return [self._make_task(
            counter, desc_base, step, deps, (file_path,), ctx.service_slug,
        )]

    def _expand_comm_clients(
        self,
        step: BuildStep,
        ctx: ServiceContext,
        counter: int,
        base_deps: tuple[str, ...],
        base_path: str,
    ) -> list[TaskItem]:
        """One task per service dependency."""
        tasks: list[TaskItem] = []
        for dep in ctx.dependencies:
            pattern = dep.pattern.replace("sync-", "").replace("async-", "")
            desc = f"Create {dep.target_slug} {pattern} client"
            path = f"{base_path}{dep.target_slug}/"
            tasks.append(self._make_task(
                counter + len(tasks), desc, step,
                base_deps, (path,), ctx.service_slug,
            ))
        return tasks

    def _expand_events(
        self,
        step: BuildStep,
        ctx: ServiceContext,
        counter: int,
        base_deps: tuple[str, ...],
        base_path: str,
    ) -> list[TaskItem]:
        """One task per event the service produces or consumes."""
        tasks: list[TaskItem] = []
        for evt in ctx.events:
            role = "producer" if evt.producer == ctx.service_slug else "consumer"
            desc = f"Implement {evt.name} event {role}"
            path = f"{base_path}{evt.name}/"
            tasks.append(self._make_task(
                counter + len(tasks), desc, step,
                base_deps, (path,), ctx.service_slug,
            ))
        return tasks

    def _expand_contract_tests(
        self,
        step: BuildStep,
        ctx: ServiceContext,
        counter: int,
        base_deps: tuple[str, ...],
        base_path: str,
    ) -> list[TaskItem]:
        """One contract test per dependency."""
        tasks: list[TaskItem] = []
        for dep in ctx.dependencies:
            desc = f"Write contract tests for {dep.target_slug}"
            path = f"{base_path}{dep.target_slug}/"
            tasks.append(self._make_task(
                counter + len(tasks), desc, step,
                base_deps, (path,), ctx.service_slug,
            ))
        return tasks

    def _make_task(
        self,
        counter: int,
        description: str,
        step: BuildStep,
        deps: tuple[str, ...],
        paths: tuple[str, ...],
        scope: str,
    ) -> TaskItem:
        """Create a single TaskItem."""
        return TaskItem(
            id=f"{TASK_ID_PREFIX}{counter:03d}",
            description=description,
            phase=step.order,
            layer=step.category,
            dependencies=deps,
            parallel=False,
            effort=step.default_effort,
            user_story="",
            file_paths=paths,
            service_scope=scope,
            governance_rules=(),
            commit_message=f"feat({scope}): {description.lower()[:50]}",
        )

    def _resolve_step_deps(
        self,
        step: BuildStep,
        step_id_map: dict[int, str],
    ) -> tuple[str, ...]:
        """Convert BuildStep.depends_on order numbers to task IDs."""
        deps: list[str] = []
        for order in step.depends_on:
            tid = step_id_map.get(order)
            if tid:
                deps.append(tid)
        return tuple(deps)

    def _assign_effort(
        self,
        tasks: list[TaskItem],
        ctx: ServiceContext,
    ) -> list[TaskItem]:
        """Apply effort estimation to all tasks."""
        seq = get_sequence(ctx.architecture)
        step_map = {s.category: s for s in seq}
        result: list[TaskItem] = []
        for task in tasks:
            step = step_map.get(task.layer)
            if step:
                effort = self._estimator.estimate(
                    step, len(ctx.features), len(ctx.dependencies),
                )
                result.append(replace(task, effort=effort))
            else:
                result.append(task)
        return result

    def _assign_governance(
        self,
        tasks: list[TaskItem],
        ctx: ServiceContext,
    ) -> list[TaskItem]:
        """Add governance rule references to tasks."""
        result: list[TaskItem] = []
        for task in tasks:
            rules = self._governance.get_relevant_rules(
                task.layer, ctx.architecture,
            )
            result.append(replace(task, governance_rules=rules))
        return result

    def _renumber(self, tasks: list[TaskItem]) -> list[TaskItem]:
        """Re-assign sequential IDs after topological sort."""
        return [
            replace(t, id=f"{TASK_ID_PREFIX}{i + 1:03d}")
            for i, t in enumerate(tasks)
        ]

    def generate_for_project(
        self,
        services: list[ServiceContext],
        plan_content: str,
    ) -> Result:
        """Generate TaskFiles for all services + cross-service infra."""
        if not services:
            return Err("No services provided")
        arch = services[0].architecture
        cross_gen = CrossServiceTaskGenerator()
        cross_result = cross_gen.generate(services, arch)
        if not cross_result.ok:
            return cross_result
        files: list[TaskFile] = []
        cross_file = cross_result.value
        if cross_file.total_count > 0:
            files.append(cross_file)
        for svc in services:
            svc_result = self.generate_for_service(svc, plan_content)
            if not svc_result.ok:
                return svc_result
            files.append(svc_result.value)
        return Ok(GenerationSummary(
            generated_files=tuple(f.target_name for f in files),
            task_counts={f.target_name: f.total_count for f in files},
            cross_dependencies=self._collect_xdeps(cross_file, files),
            warnings=(),
        ))

    def _collect_xdeps(
        self,
        cross_file: TaskFile,
        all_files: list[TaskFile],
    ) -> tuple[str, ...]:
        """Collect cross-service dependency references."""
        xdeps: list[str] = []
        for ct in cross_file.tasks:
            xdeps.append(
                f"{CROSS_SERVICE_TARGET}/{ct.id}"
            )
        return tuple(xdeps)

    def _build_task_file(
        self,
        tasks: list[TaskItem],
        ctx: ServiceContext,
    ) -> TaskFile:
        """Group tasks into phases and build TaskFile."""
        phase_dict: dict[int, list[TaskItem]] = {}
        for t in tasks:
            phase_dict.setdefault(t.phase, []).append(t)
        phases = tuple(
            (p, tuple(ts)) for p, ts in sorted(phase_dict.items())
        )
        return TaskFile(
            target_name=ctx.service_slug,
            architecture=ctx.architecture,
            tasks=tuple(tasks),
            phases=phases,
            total_count=len(tasks),
        )
