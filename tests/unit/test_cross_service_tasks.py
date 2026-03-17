"""Tests for CrossServiceTaskGenerator — shared infrastructure tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.service_context import (
    EventInfo,
    FeatureInfo,
    ServiceContext,
    ServiceDependency,
)


def _ctx(
    slug: str,
    arch: str = "microservice",
    deps: tuple[ServiceDependency, ...] = (),
    events: tuple[EventInfo, ...] = (),
) -> ServiceContext:
    return ServiceContext(
        service_slug=slug, service_name=slug, architecture=arch,
        project_description="Test", domain="test",
        features=(FeatureInfo("001", "a", "A", "D", "P0", "core"),),
        dependencies=deps, events=events, output_dir=Path("/tmp"),
    )


def _three_services() -> list[ServiceContext]:
    """PersonalFinance microservice fixture."""
    return [
        _ctx("identity-service"),
        _ctx("ledger-service", deps=(
            ServiceDependency("identity-service", "Identity", "sync-grpc", True, "Auth"),
        ), events=(
            EventInfo("TransactionCreated", "ledger-service", ("analytics-service",), "data"),
        )),
        _ctx("analytics-service", deps=(
            ServiceDependency("identity-service", "Identity", "sync-grpc", True, "Auth"),
            ServiceDependency("ledger-service", "Ledger", "sync-grpc", True, "Query"),
            ServiceDependency("notification-service", "Notify", "sync-rest", False, "Alert"),
        ), events=(
            EventInfo("TransactionCreated", "ledger-service", ("analytics-service",), "data"),
            EventInfo("AnalyticsRequested", "analytics-service", ("ledger-service",), "report"),
        )),
    ]


class TestCrossServiceGenerate:
    """CrossServiceTaskGenerator.generate() tests."""

    def test_five_categories_for_microservice(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        gen = CrossServiceTaskGenerator()
        result = gen.generate(_three_services(), "microservice")
        assert result.ok
        tf = result.value
        assert tf.target_name == "cross-service-infra"
        cats = [t.layer for t in tf.tasks]
        assert "shared_contracts" in cats
        assert "docker_compose" in cats
        assert "shared_auth" in cats

    def test_xt_prefix(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        gen = CrossServiceTaskGenerator()
        result = gen.generate(_three_services(), "microservice")
        for task in result.value.tasks:
            assert task.id.startswith("X-T")

    def test_each_category_once(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        gen = CrossServiceTaskGenerator()
        result = gen.generate(_three_services(), "microservice")
        cats = [t.layer for t in result.value.tasks]
        assert len(cats) == len(set(cats))


class TestCrossServiceFiltering:
    """Conditional cross-service task filtering."""

    def test_no_broker_without_events(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        services = [_ctx("svc-a"), _ctx("svc-b")]
        gen = CrossServiceTaskGenerator()
        result = gen.generate(services, "microservice")
        cats = [t.layer for t in result.value.tasks]
        assert "message_broker" not in cats

    def test_broker_with_events(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        gen = CrossServiceTaskGenerator()
        result = gen.generate(_three_services(), "microservice")
        cats = [t.layer for t in result.value.tasks]
        assert "message_broker" in cats


class TestCrossServiceArchGuard:
    """Architecture-specific cross-service behavior."""

    def test_monolithic_returns_empty(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        services = [_ctx("auth", "monolithic")]
        gen = CrossServiceTaskGenerator()
        result = gen.generate(services, "monolithic")
        assert result.ok
        assert result.value.total_count == 0

    def test_microservice_returns_full(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        gen = CrossServiceTaskGenerator()
        result = gen.generate(_three_services(), "microservice")
        assert result.value.total_count >= 3

    def test_modular_monolith_subset(self) -> None:
        from specforge.core.cross_service_tasks import CrossServiceTaskGenerator

        services = [_ctx("auth", "modular-monolith"), _ctx("billing", "modular-monolith")]
        gen = CrossServiceTaskGenerator()
        result = gen.generate(services, "modular-monolith")
        cats = [t.layer for t in result.value.tasks]
        assert "shared_contracts" in cats
        assert "shared_auth" in cats
        assert "docker_compose" not in cats
        assert "api_gateway" not in cats
        assert "message_broker" not in cats
