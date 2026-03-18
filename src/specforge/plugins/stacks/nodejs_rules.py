"""Rule data for NodejsPlugin — separated to keep plugin class <200 lines."""

from __future__ import annotations

from specforge.plugins.stack_plugin_base import PluginRule

# ── Microservice Backend Rules ───────────────────────────────────────

MICROSERVICE_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-NODEJS-MS-001",
        title="Express/Fastify Per-Service Application",
        severity="ERROR",
        scope="service entry points",
        description=(
            "Each microservice MUST have its own Express or Fastify "
            "application instance with isolated route registration."
        ),
        thresholds={"max_apps_per_service": "1"},
        example_correct=(
            "// order-service/src/app.ts\n"
            "const app = express();\n"
            "app.use('/orders', orderRoutes);"
        ),
        example_incorrect=(
            "// shared/app.ts\n"
            "const app = express();  // single app for all services"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MS-002",
        title="Multi-Stage Docker Container Build",
        severity="ERROR",
        scope="Dockerfile per service",
        description=(
            "Each microservice MUST use a multi-stage Docker build with "
            "node:alpine base image for minimal production images."
        ),
        thresholds={"min_build_stages": "2"},
        example_correct=(
            "FROM node:20-alpine AS builder\n"
            "FROM node:20-alpine AS runtime"
        ),
        example_incorrect="FROM node:20\nRUN npm install && npm start",
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MS-003",
        title="Prisma/TypeORM Per-Service Schema Isolation",
        severity="ERROR",
        scope="ORM schema and client",
        description=(
            "Each microservice MUST define its own Prisma schema or "
            "TypeORM data source. Shared schemas across services are forbidden."
        ),
        thresholds={"max_shared_schemas": "0"},
        example_correct=(
            "// order-service/prisma/schema.prisma\n"
            "datasource db { url = env(\"ORDER_DB_URL\") }"
        ),
        example_incorrect=(
            "// shared/prisma/schema.prisma\n"
            "// Single schema used by multiple services"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MS-004",
        title="NATS/RabbitMQ Message Broker Integration",
        severity="WARNING",
        scope="async messaging",
        description=(
            "Asynchronous cross-service communication SHOULD use NATS or "
            "RabbitMQ message broker with explicit topic/queue bindings."
        ),
        thresholds={"max_unregistered_handlers": "0"},
        example_correct=(
            "nats.subscribe('order.created', (msg) => {\n"
            "  handleOrderCreated(msg.data);\n});"
        ),
        example_incorrect=(
            "// Direct HTTP call for async operation\n"
            "await fetch('http://payment-service/process', { method: 'POST' });"
        ),
    ),
]

# ── Monolith Backend Rules ───────────────────────────────────────────

MONOLITH_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-NODEJS-MO-001",
        title="Single Application Entry Point",
        severity="ERROR",
        scope="application startup",
        description=(
            "The monolith MUST have a single application entry point "
            "with centralized middleware and route registration."
        ),
        thresholds={"max_entry_points": "1"},
        example_correct=(
            "// src/app.ts\n"
            "const app = express();\n"
            "app.use('/api/orders', orderRoutes);\n"
            "app.use('/api/users', userRoutes);"
        ),
        example_incorrect=(
            "// Multiple separate Express apps running independently\n"
            "const ordersApp = express();\nconst usersApp = express();"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MO-002",
        title="Shared Prisma Schema Definition",
        severity="WARNING",
        scope="ORM schema",
        description=(
            "All domain models SHOULD be defined in a single Prisma "
            "schema file for unified migration management."
        ),
        thresholds={"max_schemas": "1"},
        example_correct=(
            "// prisma/schema.prisma\n"
            "model Order { id Int @id }\n"
            "model User { id Int @id }"
        ),
        example_incorrect=(
            "// prisma/order.prisma and prisma/user.prisma\n"
            "// Separate schema files causing migration conflicts"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MO-003",
        title="Layered Directory Structure",
        severity="ERROR",
        scope="project organization",
        description=(
            "The monolith MUST follow layered architecture with separate "
            "directories for routes, services, models, and middleware."
        ),
        thresholds={"required_layers": "routes,services,models"},
        example_correct=(
            "src/routes/orderRoutes.ts\n"
            "src/services/orderService.ts\n"
            "src/models/order.ts"
        ),
        example_incorrect=(
            "src/orders.ts  // mixes routes, logic, and data access"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MO-004",
        title="Synchronous In-Process Communication",
        severity="WARNING",
        scope="module interaction",
        description=(
            "Modules within the monolith SHOULD communicate via direct "
            "function calls or service injection, not HTTP or message queues."
        ),
        thresholds={"max_internal_http_calls": "0"},
        example_correct="const order = await orderService.getOrder(id);",
        example_incorrect=(
            "const order = await fetch(`http://localhost/api/orders/${id}`);"
        ),
    ),
]

# ── Modular Monolith Backend Rules ───────────────────────────────────

MODULAR_MONOLITH_BACKEND_RULES: list[PluginRule] = [
    *MONOLITH_BACKEND_RULES,
    PluginRule(
        rule_id="BACK-NODEJS-MM-001",
        title="Module Boundary Enforcement via Interface Contracts",
        severity="ERROR",
        scope="cross-module imports",
        description=(
            "Each module MUST expose functionality only through public "
            "interface contracts (TypeScript interfaces/types). Direct "
            "imports of internal module files are forbidden."
        ),
        thresholds={"max_boundary_violations": "0"},
        example_correct=(
            "// modules/orders/contracts/index.ts\n"
            "export interface IOrderService {\n"
            "  getOrder(id: string): Promise<OrderDTO>;\n}"
        ),
        example_incorrect=(
            "// modules/shipping/service.ts\n"
            "import { OrderEntity } from '../orders/internal/entities';"
        ),
    ),
    PluginRule(
        rule_id="BACK-NODEJS-MM-002",
        title="Module Package Isolation",
        severity="WARNING",
        scope="package structure",
        description=(
            "Each module SHOULD be a self-contained directory with "
            "explicit index.ts barrel exports and internal subdirectories."
        ),
        thresholds={"min_module_dirs": "2"},
        example_correct=(
            "modules/orders/index.ts  // public API barrel\n"
            "modules/orders/internal/  // private implementation"
        ),
        example_incorrect=(
            "modules/orders.ts  // flat file, no encapsulation"
        ),
    ),
]

# ── Microservice Database Rules ──────────────────────────────────────

MICROSERVICE_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-NODEJS-MS-001",
        title="Database-Per-Service Pattern",
        severity="ERROR",
        scope="database provisioning",
        description=(
            "Each microservice MUST own its database or schema. "
            "No shared database tables across service boundaries."
        ),
        thresholds={"max_shared_tables": "0"},
        example_correct='DATABASE_URL="postgresql://db/order_service_db"',
        example_incorrect='DATABASE_URL="postgresql://db/shared_app_db"',
    ),
    PluginRule(
        rule_id="DB-NODEJS-MS-002",
        title="Prisma Migration Per Service",
        severity="WARNING",
        scope="migration scripts",
        description=(
            "Each service SHOULD manage its own Prisma migrations "
            "independently of other services."
        ),
        thresholds={"migrations_per_service": "separate"},
        example_correct=(
            "npx prisma migrate deploy "
            "--schema=order-service/prisma/schema.prisma"
        ),
        example_incorrect=(
            "npx prisma migrate deploy "
            "--schema=shared/prisma/schema.prisma"
        ),
    ),
]

# ── Monolith Database Rules ──────────────────────────────────────────

MONOLITH_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-NODEJS-MO-001",
        title="Unified Migration Pipeline",
        severity="ERROR",
        scope="database migrations",
        description=(
            "All database migrations MUST be managed through a single "
            "Prisma migration pipeline."
        ),
        thresholds={"migration_schemas": "1"},
        example_correct="npx prisma migrate deploy",
        example_incorrect=(
            "Multiple prisma schema files with separate migration dirs"
        ),
    ),
    PluginRule(
        rule_id="DB-NODEJS-MO-002",
        title="Schema-Based Module Separation",
        severity="WARNING",
        scope="database schema design",
        description=(
            "Domain modules SHOULD use naming prefixes or PostgreSQL "
            "schemas within the single database for logical isolation."
        ),
        thresholds={"min_prefixes": "1"},
        example_correct=(
            "model OrdersOrder {\n"
            '  @@map("orders_orders")\n}'
        ),
        example_incorrect=(
            "model Order {\n"
            '  @@map("orders")  // generic name, no module prefix\n}'
        ),
    ),
]

# ── Microservice CI/CD Rules ────────────────────────────────────────

MICROSERVICE_CICD_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="CICD-NODEJS-MS-001",
        title="Independent Service Build Pipelines",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "Each microservice MUST have its own build pipeline that "
            "triggers only on changes within its directory."
        ),
        thresholds={"pipelines_per_service": "1"},
        example_correct=(
            "trigger:\n  paths:\n    - services/order-service/**"
        ),
        example_incorrect=(
            "trigger:\n  paths:\n    - '**'  # triggers on all changes"
        ),
    ),
    PluginRule(
        rule_id="CICD-NODEJS-MS-002",
        title="Per-Service Image Tagging",
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
        rule_id="CICD-NODEJS-MO-001",
        title="Unified Build Pipeline",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "The monolith MUST have a single build pipeline that "
            "runs linting, tests, and build for the entire project."
        ),
        thresholds={"pipeline_count": "1"},
        example_correct="npm ci && npm run lint && npm test && npm run build",
        example_incorrect=(
            "Separate pipelines for each module within the monolith"
        ),
    ),
    PluginRule(
        rule_id="CICD-NODEJS-MO-002",
        title="Full Test Suite Execution",
        severity="WARNING",
        scope="test pipeline step",
        description=(
            "CI pipeline SHOULD run the complete test suite to "
            "ensure all modules are tested together."
        ),
        thresholds={"test_scope": "full"},
        example_correct="npm test  # runs all tests",
        example_incorrect=(
            "npm test -- --testPathPattern=orders"
            "  # misses other modules"
        ),
    ),
]
