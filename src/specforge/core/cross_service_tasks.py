"""CrossServiceTaskGenerator — shared infrastructure tasks (Feature 008)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specforge.core.config import (
    CROSS_SERVICE_CATEGORIES,
    CROSS_SERVICE_SCOPE,
    CROSS_SERVICE_TARGET,
    CROSS_SERVICE_TASK_PREFIX,
)
from specforge.core.result import Ok, Result
from specforge.core.task_models import TaskFile, TaskItem

if TYPE_CHECKING:
    from specforge.core.service_context import ServiceContext

_DESCRIPTIONS: dict[str, str] = {
    "shared_contracts": "Set up shared contracts library (protobuf, event schemas)",
    "docker_compose": "Create Docker Compose file for all services",
    "message_broker": "Configure message broker (exchanges, queues)",
    "api_gateway": "Configure API gateway master routing",
    "shared_auth": "Implement shared authentication middleware",
}

_EFFORTS: dict[str, str] = {
    "shared_contracts": "M",
    "docker_compose": "S",
    "message_broker": "M",
    "api_gateway": "S",
    "shared_auth": "L",
}


class CrossServiceTaskGenerator:
    """Generates shared infrastructure tasks for cross-service concerns."""

    def generate(
        self,
        services: list[ServiceContext],
        architecture: str,
    ) -> Result:
        """Generate a TaskFile for cross-service infrastructure."""
        allowed = CROSS_SERVICE_SCOPE.get(architecture, ())
        if not allowed:
            return Ok(self._empty_file(architecture))
        has_events = self._has_async_events(services)
        has_endpoints = self._has_endpoints(services)
        tasks = self._build_tasks(allowed, has_events, has_endpoints)
        return Ok(self._build_file(tasks, architecture))

    def _has_async_events(
        self, services: list[ServiceContext],
    ) -> bool:
        """Check if any service declares async events."""
        return any(len(s.events) > 0 for s in services)

    def _has_endpoints(
        self, services: list[ServiceContext],
    ) -> bool:
        """Check if any service has REST/gRPC communication."""
        for s in services:
            for d in s.dependencies:
                if "rest" in d.pattern or "grpc" in d.pattern:
                    return True
        return True  # services typically have endpoints

    def _build_tasks(
        self,
        allowed: tuple[str, ...],
        has_events: bool,
        has_endpoints: bool,
    ) -> list[TaskItem]:
        """Generate task items for allowed categories."""
        tasks: list[TaskItem] = []
        counter = 1
        for cat in CROSS_SERVICE_CATEGORIES:
            if cat not in allowed:
                continue
            if cat == "message_broker" and not has_events:
                continue
            if cat == "api_gateway" and not has_endpoints:
                continue
            tasks.append(TaskItem(
                id=f"{CROSS_SERVICE_TASK_PREFIX}{counter:03d}",
                description=_DESCRIPTIONS.get(cat, cat),
                phase=0,
                layer=cat,
                dependencies=(),
                parallel=False,
                effort=_EFFORTS.get(cat, "M"),
                user_story="",
                file_paths=(f"infrastructure/{cat}/",),
                service_scope=CROSS_SERVICE_TARGET,
                governance_rules=(),
                commit_message=f"feat(infra): {cat.replace('_', ' ')}",
            ))
            counter += 1
        return tasks

    def _build_file(
        self,
        tasks: list[TaskItem],
        architecture: str,
    ) -> TaskFile:
        """Build a TaskFile from cross-service tasks."""
        return TaskFile(
            target_name=CROSS_SERVICE_TARGET,
            architecture=architecture,
            tasks=tuple(tasks),
            phases=((0, tuple(tasks)),) if tasks else (),
            total_count=len(tasks),
        )

    def _empty_file(self, architecture: str) -> TaskFile:
        """Return an empty TaskFile for monolithic architecture."""
        return TaskFile(
            target_name=CROSS_SERVICE_TARGET,
            architecture=architecture,
            tasks=(),
            phases=(),
            total_count=0,
        )
