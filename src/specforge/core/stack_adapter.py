"""Stack adapter — maps tech stack names to context variables."""

from __future__ import annotations

from specforge.core.template_models import StackProfile

_AGNOSTIC = StackProfile(
    stack_name="agnostic",
    stack_hint="Language-agnostic",
    conventions="Follow project-wide coding standards.",
    patterns="Apply recommended architectural patterns.",
    testing_hint="Write tests before implementation (TDD).",
)

_STACK_PROFILES: dict[str, StackProfile] = {
    "dotnet": StackProfile(
        stack_name="dotnet",
        stack_hint="C#/.NET",
        conventions=(
            "Microsoft C# coding conventions. "
            "Nullable reference types enabled. "
            "async/await for all I/O. "
            "Dependency injection via IServiceCollection."
        ),
        patterns=(
            "Clean Architecture with MediatR. "
            "Minimal APIs or Controller routing. "
            "FluentValidation. Serilog structured logging."
        ),
        testing_hint="xUnit + Moq + FluentAssertions.",
    ),
    "nodejs": StackProfile(
        stack_name="nodejs",
        stack_hint="Node.js/TypeScript",
        conventions=(
            "ESLint + Prettier. Strict TypeScript. "
            "async/await over callbacks. "
            "Barrel exports for module boundaries."
        ),
        patterns=(
            "Express or Fastify with middleware. "
            "Repository pattern with Prisma. "
            "Zod schemas for validation. Pino logging."
        ),
        testing_hint="Jest or Vitest + Supertest + testcontainers.",
    ),
    "python": StackProfile(
        stack_name="python",
        stack_hint="Python",
        conventions=(
            "PEP 8 + ruff. Type hints everywhere. "
            "pathlib.Path exclusively. "
            "Dataclasses or Pydantic models. "
            "Result[T, E] for recoverable errors."
        ),
        patterns=(
            "Clean Architecture with DI. "
            "Repository pattern with SQLAlchemy. "
            "Click for CLI. structlog for logging."
        ),
        testing_hint="pytest + pytest-cov + syrupy snapshots.",
    ),
    "go": StackProfile(
        stack_name="go",
        stack_hint="Go",
        conventions=(
            "Effective Go conventions. "
            "Error wrapping with fmt.Errorf. "
            "Interface-based abstractions. "
            "Struct embedding over inheritance."
        ),
        patterns=(
            "Standard library HTTP server. "
            "Repository pattern with sqlx. "
            "Cobra for CLI. zerolog for logging."
        ),
        testing_hint="testing package + testify + httptest.",
    ),
    "java": StackProfile(
        stack_name="java",
        stack_hint="Java",
        conventions=(
            "Google Java Style. "
            "Records for immutable data. "
            "Optional for nullable returns. "
            "Dependency injection via Spring."
        ),
        patterns=(
            "Spring Boot with layered architecture. "
            "JPA/Hibernate for data access. "
            "MapStruct for DTO mapping. SLF4J logging."
        ),
        testing_hint="JUnit 5 + Mockito + AssertJ + Testcontainers.",
    ),
}


class StackAdapter:
    """Maps tech stack names to StackProfile context variables."""

    @staticmethod
    def get_context(stack: str) -> StackProfile:
        """Get stack-specific context. Returns agnostic for unknown stacks."""
        return _STACK_PROFILES.get(stack, _AGNOSTIC)

    @staticmethod
    def supported_stacks() -> list[str]:
        """Return all known stack identifiers."""
        return list(_STACK_PROFILES.keys())
