"""Rule data for PythonPlugin — separated to keep plugin class <200 lines."""

from __future__ import annotations

from specforge.plugins.stack_plugin_base import PluginRule

# ── Microservice Backend Rules ───────────────────────────────────────

MICROSERVICE_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-PYTHON-MS-001",
        title="FastAPI Per-Service Application",
        severity="ERROR",
        scope="service entry points",
        description=(
            "Each microservice MUST have its own FastAPI application "
            "instance with isolated routers and dependency injection."
        ),
        thresholds={"max_apps_per_service": "1"},
        example_correct=(
            "# order_service/main.py\n"
            "app = FastAPI(title='Order Service')"
        ),
        example_incorrect=(
            "# shared/main.py\n"
            "app = FastAPI()  # single app for all services"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MS-002",
        title="Multi-Stage Docker Container Build",
        severity="ERROR",
        scope="Dockerfile per service",
        description=(
            "Each microservice MUST use a multi-stage Docker build with "
            "python:slim base image for minimal production images."
        ),
        thresholds={"min_build_stages": "2"},
        example_correct=(
            "FROM python:3.11-slim AS builder\n"
            "FROM python:3.11-slim AS runtime"
        ),
        example_incorrect="FROM python:3.11\nRUN pip install -r requirements.txt",
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MS-003",
        title="SQLAlchemy Per-Service Model Isolation",
        severity="ERROR",
        scope="ORM models and sessions",
        description=(
            "Each microservice MUST define its own SQLAlchemy models and "
            "session factory. Shared Base metadata across services is forbidden."
        ),
        thresholds={"max_shared_bases": "0"},
        example_correct=(
            "# order_service/models.py\n"
            "Base = declarative_base()\n"
            "class Order(Base): ..."
        ),
        example_incorrect=(
            "# shared/models.py\n"
            "class Order(SharedBase): ...  # SharedBase used by multiple services"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MS-004",
        title="Celery/Dramatiq Task Queue Integration",
        severity="WARNING",
        scope="async task processing",
        description=(
            "Asynchronous cross-service operations SHOULD use Celery or "
            "Dramatiq task queues with explicit task registration."
        ),
        thresholds={"max_unregistered_tasks": "0"},
        example_correct=(
            "@celery_app.task(name='orders.process_payment')\n"
            "def process_payment(order_id: str): ..."
        ),
        example_incorrect=(
            "# Direct HTTP call for async operation\n"
            "requests.post('http://payment-service/process', json=data)"
        ),
    ),
]

# ── Monolith Backend Rules ───────────────────────────────────────────

MONOLITH_BACKEND_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="BACK-PYTHON-MO-001",
        title="Single Application Entry Point",
        severity="ERROR",
        scope="application startup",
        description=(
            "The monolith MUST have a single application entry point "
            "with centralized configuration and middleware registration."
        ),
        thresholds={"max_entry_points": "1"},
        example_correct=(
            "# app/main.py\n"
            "app = FastAPI(title='MyApp')\n"
            "app.include_router(orders.router)"
        ),
        example_incorrect=(
            "# Multiple separate FastAPI apps running independently\n"
            "orders_app = FastAPI()\npayments_app = FastAPI()"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MO-002",
        title="Shared SQLAlchemy Model Base",
        severity="WARNING",
        scope="ORM model definitions",
        description=(
            "All domain models SHOULD inherit from a single SQLAlchemy "
            "declarative Base for unified migration management."
        ),
        thresholds={"max_bases": "1"},
        example_correct=(
            "# app/models/base.py\n"
            "Base = declarative_base()\n"
            "# app/models/order.py\n"
            "class Order(Base): ..."
        ),
        example_incorrect=(
            "OrderBase = declarative_base()\n"
            "UserBase = declarative_base()  # separate bases"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MO-003",
        title="Layered Package Structure",
        severity="ERROR",
        scope="package organization",
        description=(
            "The monolith MUST follow layered architecture with separate "
            "packages for API, services, models, and repositories."
        ),
        thresholds={"required_layers": "api,services,models"},
        example_correct=(
            "app/api/routes.py\n"
            "app/services/order_service.py\n"
            "app/models/order.py"
        ),
        example_incorrect=(
            "app/orders.py  # mixes routes, logic, and data access"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MO-004",
        title="Synchronous In-Process Communication",
        severity="WARNING",
        scope="module interaction",
        description=(
            "Modules within the monolith SHOULD communicate via direct "
            "function calls or service layer methods, not HTTP or queues."
        ),
        thresholds={"max_internal_http_calls": "0"},
        example_correct="result = order_service.get_order(order_id)",
        example_incorrect=(
            "result = httpx.get(f'http://localhost/api/orders/{order_id}')"
        ),
    ),
]

# ── Modular Monolith Backend Rules ───────────────────────────────────

MODULAR_MONOLITH_BACKEND_RULES: list[PluginRule] = [
    *MONOLITH_BACKEND_RULES,
    PluginRule(
        rule_id="BACK-PYTHON-MM-001",
        title="Module Boundary Enforcement via Interface Contracts",
        severity="ERROR",
        scope="cross-module imports",
        description=(
            "Each module MUST expose functionality only through public "
            "interface contracts (Protocol classes or ABCs). Direct "
            "imports of internal module classes are forbidden."
        ),
        thresholds={"max_boundary_violations": "0"},
        example_correct=(
            "# modules/orders/contracts.py\n"
            "class OrderServiceProtocol(Protocol):\n"
            "    def get_order(self, id: str) -> OrderDTO: ..."
        ),
        example_incorrect=(
            "# modules/shipping/service.py\n"
            "from modules.orders.internal.models import Order  # direct import"
        ),
    ),
    PluginRule(
        rule_id="BACK-PYTHON-MM-002",
        title="Module Package Isolation",
        severity="WARNING",
        scope="package structure",
        description=(
            "Each module SHOULD be a self-contained Python package with "
            "explicit __init__.py exports and internal subpackages."
        ),
        thresholds={"min_module_packages": "2"},
        example_correct=(
            "modules/orders/__init__.py  # public API only\n"
            "modules/orders/internal/  # private implementation"
        ),
        example_incorrect=(
            "modules/orders.py  # flat file, no encapsulation"
        ),
    ),
]

# ── Microservice Database Rules ──────────────────────────────────────

MICROSERVICE_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-PYTHON-MS-001",
        title="Database-Per-Service Pattern",
        severity="ERROR",
        scope="database provisioning",
        description=(
            "Each microservice MUST own its database or schema. "
            "No shared database tables across service boundaries."
        ),
        thresholds={"max_shared_tables": "0"},
        example_correct="DATABASE_URL=postgresql://db/order_service_db",
        example_incorrect="DATABASE_URL=postgresql://db/shared_app_db",
    ),
    PluginRule(
        rule_id="DB-PYTHON-MS-002",
        title="Alembic Migration Per Service",
        severity="WARNING",
        scope="migration scripts",
        description=(
            "Each service SHOULD manage its own Alembic migration "
            "environment independently of other services."
        ),
        thresholds={"migrations_per_service": "separate"},
        example_correct="alembic -c order_service/alembic.ini upgrade head",
        example_incorrect="alembic -c shared/alembic.ini upgrade head",
    ),
]

# ── Monolith Database Rules ──────────────────────────────────────────

MONOLITH_DATABASE_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="DB-PYTHON-MO-001",
        title="Unified Alembic Migration Pipeline",
        severity="ERROR",
        scope="database migrations",
        description=(
            "All database migrations MUST be managed through a single "
            "Alembic migration environment."
        ),
        thresholds={"migration_envs": "1"},
        example_correct="alembic upgrade head  # single migration env",
        example_incorrect=(
            "Multiple alembic.ini files for different modules"
        ),
    ),
    PluginRule(
        rule_id="DB-PYTHON-MO-002",
        title="Schema-Based Module Separation",
        severity="WARNING",
        scope="database schema design",
        description=(
            "Domain modules SHOULD use separate database schemas "
            "within the single database for logical isolation."
        ),
        thresholds={"min_schemas": "1"},
        example_correct=(
            "class Order(Base):\n"
            '    __table_args__ = {"schema": "ordering"}'
        ),
        example_incorrect=(
            "class Order(Base):\n"
            '    __tablename__ = "orders"  # default public schema'
        ),
    ),
]

# ── Microservice CI/CD Rules ────────────────────────────────────────

MICROSERVICE_CICD_RULES: list[PluginRule] = [
    PluginRule(
        rule_id="CICD-PYTHON-MS-001",
        title="Independent Service Build Pipelines",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "Each microservice MUST have its own build pipeline that "
            "triggers only on changes within its directory."
        ),
        thresholds={"pipelines_per_service": "1"},
        example_correct=(
            "trigger:\n  paths:\n    - services/order_service/**"
        ),
        example_incorrect=(
            "trigger:\n  paths:\n    - '**'  # triggers on all changes"
        ),
    ),
    PluginRule(
        rule_id="CICD-PYTHON-MS-002",
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
        rule_id="CICD-PYTHON-MO-001",
        title="Unified Build Pipeline",
        severity="ERROR",
        scope="CI/CD configuration",
        description=(
            "The monolith MUST have a single build pipeline that "
            "runs linting, tests, and packaging for the entire project."
        ),
        thresholds={"pipeline_count": "1"},
        example_correct="pip install -e . && pytest && ruff check .",
        example_incorrect=(
            "Separate pipelines for each module within the monolith"
        ),
    ),
    PluginRule(
        rule_id="CICD-PYTHON-MO-002",
        title="Full Test Suite Execution",
        severity="WARNING",
        scope="test pipeline step",
        description=(
            "CI pipeline SHOULD run the complete pytest suite to "
            "ensure all modules are tested together."
        ),
        thresholds={"test_scope": "full"},
        example_correct="pytest tests/ --cov=app",
        example_incorrect="pytest tests/orders/  # misses other modules",
    ),
]
