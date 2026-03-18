"""Rule data for DotnetPlugin — separated to keep plugin class <200 lines."""

from __future__ import annotations

from specforge.plugins.stack_plugin_base import PluginRule

# ── Microservice Backend Rules ───────────────────────────────────────

MICROSERVICE_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-DOTNET-MS-001",
        title="Per-Service DbContext Isolation",
        severity="ERROR",
        scope="all EF Core DbContext classes",
        description=(
            "Each microservice MUST define its own DbContext scoped to its "
            "bounded context. Cross-service DbContext sharing is forbidden."
        ),
        thresholds={"max_dbcontexts_per_service": "1"},
        example_correct="public class OrderDbContext : DbContext { ... }",
        example_incorrect=(
            "public class SharedDbContext : DbContext "
            "{ /* used by multiple services */ }"
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MS-002",
        title="Multi-Stage Docker Container Build",
        severity="ERROR",
        scope="Dockerfile per service",
        description=(
            "Each microservice MUST use a multi-stage Docker build with "
            "separate SDK, publish, and runtime stages for minimal images."
        ),
        thresholds={"min_build_stages": "3"},
        example_correct=(
            "FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build\n"
            "FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime"
        ),
        example_incorrect="FROM mcr.microsoft.com/dotnet/sdk:8.0\nRUN dotnet publish",
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MS-003",
        title="gRPC Proto Contract Definitions",
        severity="WARNING",
        scope="inter-service communication",
        description=(
            "Synchronous inter-service calls SHOULD use gRPC with shared "
            ".proto contract files in a dedicated contracts project."
        ),
        thresholds={"proto_location": "src/Contracts/Protos/"},
        example_correct='syntax = "proto3";\nservice OrderService { ... }',
        example_incorrect=(
            "var client = new HttpClient();\n"
            'await client.GetAsync("http://order-service/api/orders");'
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MS-004",
        title="MassTransit Event Handler Registration",
        severity="ERROR",
        scope="async messaging consumers",
        description=(
            "All asynchronous event handlers MUST be registered via "
            "MassTransit consumers with explicit queue/topic bindings."
        ),
        thresholds={"max_unregistered_handlers": "0"},
        example_correct=(
            "cfg.ReceiveEndpoint(\"order-created\", e => {\n"
            "    e.ConfigureConsumer<OrderCreatedConsumer>(ctx);\n});"
        ),
        example_incorrect=(
            "bus.Publish(new OrderCreated());\n"
            "// No consumer registration"
        ),
    ),
]

# ── Monolith Backend Rules ───────────────────────────────────────────

MONOLITH_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-DOTNET-MO-001",
        title="Single DbContext with Module Schemas",
        severity="ERROR",
        scope="EF Core DbContext",
        description=(
            "The monolith MUST use a single DbContext with schema-based "
            "separation for different domain modules."
        ),
        thresholds={"max_dbcontexts": "1"},
        example_correct=(
            "public class AppDbContext : DbContext {\n"
            '    modelBuilder.HasDefaultSchema("orders");\n}'
        ),
        example_incorrect=(
            "public class OrderDbContext : DbContext { }\n"
            "public class UserDbContext : DbContext { }"
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MO-002",
        title="MediatR Command/Query Separation",
        severity="WARNING",
        scope="application layer handlers",
        description=(
            "Business operations SHOULD use MediatR for command/query "
            "separation via IRequest<T> and IRequestHandler<T>."
        ),
        thresholds={"min_handler_coverage": "80%"},
        example_correct=(
            "public record CreateOrderCommand : IRequest<OrderDto>;\n"
            "public class CreateOrderHandler : "
            "IRequestHandler<CreateOrderCommand, OrderDto>"
        ),
        example_incorrect=(
            "public class OrderController {\n"
            "    public IActionResult Create() { /* inline logic */ }\n}"
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MO-003",
        title="Layered Architecture Enforcement",
        severity="ERROR",
        scope="project references",
        description=(
            "The monolith MUST follow layered architecture: API -> Application "
            "-> Domain -> Infrastructure. No reverse dependencies allowed."
        ),
        thresholds={"max_reverse_deps": "0"},
        example_correct=(
            "// API references Application\n"
            "// Application references Domain\n"
            "// Infrastructure references Domain"
        ),
        example_incorrect=(
            "// Domain references Infrastructure\n"
            "// Circular dependency"
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MO-004",
        title="Synchronous In-Process Communication",
        severity="WARNING",
        scope="module communication",
        description=(
            "Modules within the monolith SHOULD communicate via direct "
            "method calls or mediator pattern, not HTTP or message queues."
        ),
        thresholds={"max_http_internal_calls": "0"},
        example_correct="await _mediator.Send(new GetOrderQuery(id));",
        example_incorrect=(
            'await _httpClient.GetAsync("http://localhost/api/orders");'
        ),
    ),
]

# ── Modular Monolith Backend Rules ───────────────────────────────────

MODULAR_MONOLITH_BACKEND_RULES: list[PluginRule] = [
    *MONOLITH_BACKEND_RULES,
    PluginRule(
        rule_id="BACK-DOTNET-MM-001",
        title="Module Boundary Enforcement via Interface Contracts",
        severity="ERROR",
        scope="cross-module dependencies",
        description=(
            "Each module MUST expose functionality only through public "
            "interface contracts. Direct class references across module "
            "boundaries are forbidden."
        ),
        thresholds={"max_boundary_violations": "0"},
        example_correct=(
            "// Orders.Contracts/IOrderService.cs\n"
            "public interface IOrderService { Task<OrderDto> GetAsync(Guid id); }"
        ),
        example_incorrect=(
            "// Shipping references Orders.Internal directly\n"
            "var order = new Orders.Internal.OrderEntity();"
        ),
    ),
    PluginRule(
        rule_id="BACK-DOTNET-MM-002",
        title="Module Assembly Isolation",
        severity="WARNING",
        scope="project structure",
        description=(
            "Each module SHOULD be a separate assembly (project) with "
            "explicit interface contract projects for cross-module deps."
        ),
        thresholds={"min_module_projects": "2"},
        example_correct=(
            "src/Modules/Orders/Orders.Core/\n"
            "src/Modules/Orders/Orders.Contracts/"
        ),
        example_incorrect=(
            "src/Modules/Orders/ (single project with all concerns)"
        ),
    ),
]

# ── Microservice Database Rules ──────────────────────────────────────

MICROSERVICE_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-DOTNET-MS-001",
        title="Database-Per-Service Pattern",
        severity="ERROR",
        scope="database provisioning",
        description=(
            "Each microservice MUST own its database or schema. "
            "No shared database tables across service boundaries."
        ),
        thresholds={"max_shared_tables": "0"},
        example_correct="ConnectionStrings__OrderDb=Server=db;Database=orders;",
        example_incorrect="ConnectionStrings__SharedDb=Server=db;Database=app;",
    ),
    PluginRule(
        rule_id="DB-DOTNET-MS-002",
        title="EF Core Migration Per Service",
        severity="WARNING",
        scope="migration scripts",
        description=(
            "Each service SHOULD manage its own EF Core migrations "
            "independently of other services."
        ),
        thresholds={"migrations_per_service": "separate"},
        example_correct="dotnet ef migrations add Init --project OrderService",
        example_incorrect="dotnet ef migrations add Init --project SharedMigrations",
    ),
]

# ── Monolith Database Rules ──────────────────────────────────────────

MONOLITH_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-DOTNET-MO-001",
        title="Unified Migration Pipeline",
        severity="ERROR",
        scope="database migrations",
        description=(
            "All database migrations MUST be managed through a single "
            "migration pipeline using EF Core migrations."
        ),
        thresholds={"migration_projects": "1"},
        example_correct=(
            "dotnet ef migrations add AddOrders "
            "--project App.Infrastructure"
        ),
        example_incorrect=(
            "Manual SQL scripts applied outside EF Core migration pipeline"
        ),
    ),
    PluginRule(
        rule_id="DB-DOTNET-MO-002",
        title="Schema-Based Module Separation",
        severity="WARNING",
        scope="database schema design",
        description=(
            "Domain modules SHOULD use separate database schemas "
            "within the single database for logical isolation."
        ),
        thresholds={"min_schemas": "1"},
        example_correct=(
            'modelBuilder.Entity<Order>().ToTable("Orders", schema: "ordering");'
        ),
        example_incorrect=(
            'modelBuilder.Entity<Order>().ToTable("Orders"); // default dbo schema'
        ),
    ),
]

# ── Microservice CI/CD Rules ────────────────────────────────────────

MICROSERVICE_CICD_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="CICD-DOTNET-MS-001",
        title="Independent Service Build Pipelines",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "Each microservice MUST have its own build pipeline that "
            "triggers only on changes within its directory."
        ),
        thresholds={"pipelines_per_service": "1"},
        example_correct=(
            "trigger:\n  paths:\n    - src/Services/OrderService/**"
        ),
        example_incorrect=(
            "trigger:\n  paths:\n    - src/**  # triggers on all changes"
        ),
    ),
    PluginRule(
        rule_id="CICD-DOTNET-MS-002",
        title="Container Image Tagging",
        severity="WARNING",
        scope="image registry",
        description=(
            "Built images SHOULD use semantic version tags and commit SHA "
            "for traceability. Latest-only tagging is discouraged."
        ),
        thresholds={"required_tags": "semver,sha"},
        example_correct="docker tag order-service:1.2.3 order-service:abc1234",
        example_incorrect="docker tag order-service:latest",
    ),
]

# ── Monolith CI/CD Rules ────────────────────────────────────────────

MONOLITH_CICD_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="CICD-DOTNET-MO-001",
        title="Unified Build Pipeline",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "The monolith MUST have a single build pipeline that "
            "compiles, tests, and packages the entire solution."
        ),
        thresholds={"pipeline_count": "1"},
        example_correct="dotnet build App.sln && dotnet test App.sln",
        example_incorrect=(
            "Separate pipelines for each project within the monolith"
        ),
    ),
    PluginRule(
        rule_id="CICD-DOTNET-MO-002",
        title="Solution-Level Test Execution",
        severity="WARNING",
        scope="test pipeline step",
        description=(
            "CI pipeline SHOULD run tests at the solution level to "
            "ensure all modules are tested together."
        ),
        thresholds={"test_scope": "solution"},
        example_correct="dotnet test App.sln --configuration Release",
        example_incorrect=(
            "dotnet test App.Api.Tests.csproj"
            "  # misses other test projects"
        ),
    ),
]
