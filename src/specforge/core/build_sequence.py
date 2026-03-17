"""Architecture-specific build sequence definitions for Feature 008."""

from __future__ import annotations

from specforge.core.task_models import BuildStep

MICROSERVICE_BUILD_SEQUENCE: tuple[BuildStep, ...] = (
    BuildStep(
        1, "scaffolding",
        "Set up {service} project scaffold",
        "S", "src/{service}/",
        (), (),
    ),
    BuildStep(
        2, "domain_models",
        "Create domain models and value objects",
        "M", "src/{service}/domain/models/",
        (1,), (),
    ),
    BuildStep(
        3, "database",
        "Configure database context, migrations, seeds",
        "L", "src/{service}/infrastructure/data/",
        (2,), (),
    ),
    BuildStep(
        4, "repository",
        "Implement repository interfaces and implementations",
        "M", "src/{service}/infrastructure/repos/",
        (3,), (),
    ),
    BuildStep(
        5, "service_layer",
        "Implement service layer with validation",
        "L", "src/{service}/application/services/",
        (4,), (),
    ),
    BuildStep(
        6, "communication_clients",
        "Create communication clients for dependent services",
        "M", "src/{service}/infrastructure/clients/",
        (5,), (),
    ),
    BuildStep(
        7, "controllers",
        "Implement API controllers and middleware",
        "M", "src/{service}/api/controllers/",
        (5,), (6,),
    ),
    BuildStep(
        8, "event_handlers",
        "Implement event publishers and consumers",
        "M", "src/{service}/infrastructure/events/",
        (5,), (6, 7),
    ),
    BuildStep(
        9, "health_checks",
        "Add health check endpoints",
        "S", "src/{service}/api/health/",
        (7,), (8,),
    ),
    BuildStep(
        10, "contract_tests",
        "Write contract tests against dependencies",
        "L", "tests/{service}/contract/",
        (6,), (),
    ),
    BuildStep(
        11, "unit_tests",
        "Write unit tests for all layers",
        "L", "tests/{service}/unit/",
        (5,), (10,),
    ),
    BuildStep(
        12, "integration_tests",
        "Write integration tests",
        "XL", "tests/{service}/integration/",
        (11,), (),
    ),
    BuildStep(
        13, "container_optimization",
        "Optimize container build (multi-stage)",
        "S", "src/{service}/Dockerfile",
        (7,), (12,),
    ),
    BuildStep(
        14, "gateway_config",
        "Configure API gateway routes",
        "S", "infrastructure/gateway/",
        (7,), (13,),
    ),
)

MONOLITH_BUILD_SEQUENCE: tuple[BuildStep, ...] = (
    BuildStep(
        1, "folder_structure",
        "Set up {module} module folder structure",
        "S", "src/modules/{module}/",
        (), (),
    ),
    BuildStep(
        2, "domain_models",
        "Create domain models",
        "M", "src/modules/{module}/models/",
        (1,), (),
    ),
    BuildStep(
        3, "database",
        "Create database migrations (shared DbContext)",
        "M", "src/modules/{module}/migrations/",
        (2,), (),
    ),
    BuildStep(
        4, "repo_service",
        "Implement repository and service layers",
        "L", "src/modules/{module}/services/",
        (3,), (),
    ),
    BuildStep(
        5, "controllers",
        "Implement controllers",
        "M", "src/modules/{module}/controllers/",
        (4,), (),
    ),
    BuildStep(
        6, "boundary_interface",
        "Define module boundary interface",
        "M", "src/modules/{module}/contracts/",
        (4,), (5,),
    ),
    BuildStep(
        7, "tests",
        "Write unit and integration tests",
        "L", "tests/modules/{module}/",
        (5,), (),
    ),
)


def get_sequence(architecture: str) -> tuple[BuildStep, ...]:
    """Return the build sequence for the given architecture."""
    sequences = {
        "microservice": MICROSERVICE_BUILD_SEQUENCE,
        "monolithic": MONOLITH_BUILD_SEQUENCE,
        "modular-monolith": MONOLITH_BUILD_SEQUENCE,
    }
    return sequences.get(architecture, MONOLITH_BUILD_SEQUENCE)
