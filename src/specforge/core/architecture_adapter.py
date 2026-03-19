"""ArchitectureAdapter — protocol + 3 implementations for arch-specific behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from specforge.core.service_context import ServiceContext


@runtime_checkable
class ArchitectureAdapter(Protocol):
    """Protocol for architecture-specific artifact adaptation."""

    def get_context(self, ctx: ServiceContext) -> dict[str, Any]: ...
    def get_datamodel_context(self, ctx: ServiceContext) -> dict[str, Any]: ...
    def get_research_extras(self) -> list[dict[str, str]]: ...
    def get_plan_sections(self) -> list[dict[str, str]]: ...
    def get_task_extras(self) -> list[dict[str, str]]: ...
    def get_edge_case_extras(self) -> list[dict[str, str]]: ...
    def get_checklist_extras(self) -> list[dict[str, str]]: ...
    def serialize_for_prompt(self) -> str: ...


class MicroserviceAdapter:
    """Adapter for microservice architecture."""

    def get_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Add dependencies, communication patterns, events."""
        return {
            "dependencies": [
                {
                    "target": d.target_slug,
                    "name": d.target_name,
                    "pattern": d.pattern,
                    "required": d.required,
                    "description": d.description,
                }
                for d in ctx.dependencies
            ],
            "communication_patterns": list({d.pattern for d in ctx.dependencies}),
            "events": [
                {
                    "name": e.name,
                    "producer": e.producer,
                    "consumers": list(e.consumers),
                }
                for e in ctx.events
            ],
        }

    def get_datamodel_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Isolated entity scope with API contract references."""
        return {
            "entity_scope": "isolated",
            "cross_service_ref": "api_contract",
            "shared_entities": False,
        }

    def get_research_extras(self) -> list[dict[str, str]]:
        """Service mesh, API versioning, distributed tracing."""
        return [
            {
                "topic": "Service mesh and API gateway evaluation",
                "description": "Evaluate service mesh options and API gateway routing",
            },
            {
                "topic": "API versioning strategy",
                "description": "Define versioning for inter-service contracts",
            },
            {
                "topic": "Distributed tracing setup",
                "description": "Evaluate tracing infrastructure for request tracking",
            },
        ]

    def get_plan_sections(self) -> list[dict[str, str]]:
        """5 deployment concern sections."""
        return [
            {
                "title": "Containerization",
                "description": "Docker image build, registry, and deployment config",
            },
            {
                "title": "Health Checks",
                "description": "Liveness and readiness probe endpoints",
            },
            {
                "title": "Service Registration",
                "description": "Service discovery registration and DNS config",
            },
            {
                "title": "Circuit Breakers",
                "description": "Resilience patterns for inter-service calls",
            },
            {
                "title": "API Gateway",
                "description": "Route configuration and rate limiting",
            },
        ]

    def get_task_extras(self) -> list[dict[str, str]]:
        """Container, registration, contract test tasks."""
        return [
            {
                "name": "Container build",
                "description": "Create Dockerfile and build config",
            },
            {
                "name": "Service registration",
                "description": "Register with service discovery",
            },
            {
                "name": "Contract tests",
                "description": "Write consumer-driven contract tests",
            },
        ]

    def get_edge_case_extras(self) -> list[dict[str, str]]:
        """Distributed system failure scenarios."""
        return [
            {
                "name": "Service Down",
                "description": "Dependent service unavailable",
            },
            {
                "name": "Network Partition",
                "description": "Network split between services",
            },
            {
                "name": "Eventual Consistency",
                "description": "Stale data during async propagation",
            },
            {
                "name": "Timeout Handling",
                "description": "Inter-service call exceeds timeout",
            },
        ]

    def get_checklist_extras(self) -> list[dict[str, str]]:
        """API contract and deployment readiness."""
        return [
            {
                "description": "API contract matches consumer expectations",
            },
            {
                "description": "Deployment pipeline includes health check verification",
            },
        ]

    def serialize_for_prompt(self) -> str:
        """Serialize microservice context for LLM prompt injection."""
        return (
            "## Architecture: Microservice\n\n"
            "This service is part of a microservice architecture:\n"
            "- Each service runs in its own Docker container\n"
            "- Inter-service communication via REST, gRPC, or async events\n"
            "- Required: health check endpoint at /health, readiness probe\n"
            "- Service isolation: no shared database; use API contracts\n"
            "- Include: circuit breaker patterns, service discovery, "
            "container orchestration config\n"
            "- Consider: API gateway routing, distributed tracing, "
            "service mesh evaluation"
        )


class MonolithAdapter:
    """Adapter for monolithic architecture."""

    def get_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Add module context and shared infrastructure."""
        return {
            "module_context": {
                "module_name": ctx.service_name,
                "module_slug": ctx.service_slug,
            },
            "shared_infrastructure": {
                "database": "shared",
                "auth": "shared middleware",
            },
        }

    def get_datamodel_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Module-scoped with shared table references."""
        return {
            "entity_scope": "module",
            "cross_service_ref": "shared_table",
            "shared_entities": True,
        }

    def get_research_extras(self) -> list[dict[str, str]]:
        """Shared resource and dependency analysis."""
        return [
            {
                "topic": "Shared resource contention analysis",
                "description": "Identify shared resources and contention risks",
            },
            {
                "topic": "Module dependency analysis",
                "description": "Map inter-module dependencies and coupling risks",
            },
        ]

    def get_plan_sections(self) -> list[dict[str, str]]:
        """Shared infrastructure sections."""
        return [
            {
                "title": "Shared Database",
                "description": "Database schema shared across modules",
            },
            {
                "title": "Shared Auth Middleware",
                "description": "Authentication middleware shared by all modules",
            },
        ]

    def get_task_extras(self) -> list[dict[str, str]]:
        """Module integration tasks."""
        return [
            {
                "name": "Module integration",
                "description": "Wire module into shared infrastructure",
            },
        ]

    def get_edge_case_extras(self) -> list[dict[str, str]]:
        """Module boundary and contention scenarios."""
        return [
            {
                "name": "Module Boundary Violation",
                "description": "Direct cross-module access",
            },
            {
                "name": "Shared Resource Contention",
                "description": "Database lock contention",
            },
        ]

    def get_checklist_extras(self) -> list[dict[str, str]]:
        """Module isolation verification."""
        return [
            {
                "description": "Module isolation verified "
                "— no direct cross-module imports",
            },
        ]

    def serialize_for_prompt(self) -> str:
        """Serialize monolith context for LLM prompt injection."""
        return (
            "## Architecture: Monolithic\n\n"
            "This module is part of a monolithic application:\n"
            "- Shared database with other modules; define clear schema "
            "boundaries\n"
            "- Module boundaries enforced via interface contracts, not "
            "network calls\n"
            "- No Docker, no service mesh, no container orchestration\n"
            "- Shared middleware, authentication, and configuration\n"
            "- Use internal module imports for cross-module communication"
        )


class ModularMonolithAdapter:
    """Adapter for modular-monolith architecture.

    Extends MonolithAdapter with strict boundary enforcement.
    """

    def __init__(self) -> None:
        self._base = MonolithAdapter()

    def get_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Monolith context plus boundary enforcement flag."""
        base = self._base.get_context(ctx)
        base["strict_boundaries"] = True
        return base

    def get_datamodel_context(self, ctx: ServiceContext) -> dict[str, Any]:
        """Strict module scope with no cross-module DB access."""
        return {
            "entity_scope": "strict_module",
            "cross_service_ref": "interface_contract",
            "shared_entities": True,
            "no_cross_module_db": True,
        }

    def get_research_extras(self) -> list[dict[str, str]]:
        """Monolith extras plus boundary enforcement."""
        return [
            *self._base.get_research_extras(),
            {
                "topic": "Module boundary enforcement strategy",
                "description": "Define enforcement for strict module boundaries",
            },
            {
                "topic": "Interface versioning approach",
                "description": "Version module public interfaces for compatibility",
            },
        ]

    def get_plan_sections(self) -> list[dict[str, str]]:
        """Monolith sections plus boundary enforcement."""
        return [
            *self._base.get_plan_sections(),
            {
                "title": "Module Boundary Enforcement",
                "description": "Strict module boundary rules and validation",
            },
        ]

    def get_task_extras(self) -> list[dict[str, str]]:
        """Monolith tasks plus interface definition."""
        return [
            *self._base.get_task_extras(),
            {
                "name": "Interface definition",
                "description": "Define module public interface",
            },
        ]

    def get_edge_case_extras(self) -> list[dict[str, str]]:
        """Monolith cases plus interface violations."""
        return [
            *self._base.get_edge_case_extras(),
            {
                "name": "Interface Contract Violation",
                "description": "Module breaks its published interface contract",
            },
        ]

    def get_checklist_extras(self) -> list[dict[str, str]]:
        """Monolith items plus cross-module DB check."""
        return [
            *self._base.get_checklist_extras(),
            {
                "description": "No cross-module direct DB access "
                "— all access via interfaces",
            },
        ]

    def serialize_for_prompt(self) -> str:
        """Serialize modular-monolith context for LLM prompt injection."""
        return (
            "## Architecture: Modular Monolith\n\n"
            "This module is part of a modular-monolith application:\n"
            "- Strict module boundaries enforced via interface contracts\n"
            "- No cross-module direct database access\n"
            "- Module public interfaces must be versioned\n"
            "- Shared database with schema boundaries per module\n"
            "- No Docker, no service mesh, no container orchestration\n"
            "- Shared middleware, authentication, and configuration\n"
            "- All cross-module communication via defined interfaces"
        )


def create_adapter(architecture: str) -> ArchitectureAdapter:
    """Factory function to create the correct adapter."""
    adapters: dict[str, type] = {
        "microservice": MicroserviceAdapter,
        "modular-monolith": ModularMonolithAdapter,
        "monolithic": MonolithAdapter,
    }
    cls = adapters.get(architecture, MonolithAdapter)
    return cls()
