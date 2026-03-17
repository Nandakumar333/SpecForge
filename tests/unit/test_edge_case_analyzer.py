"""Tests for MicroserviceEdgeCaseAnalyzer (T014, T015, T016, T018)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.edge_case_analyzer import EdgeCaseAnalyzer
from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_models import EdgeCaseReport
from specforge.core.edge_case_patterns import PatternLoader
from specforge.core.service_context import (
    EventInfo,
    FeatureInfo,
    ServiceContext,
    ServiceDependency,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_patterns():
    loader = PatternLoader()
    result = loader.load_patterns()
    assert result.ok
    return result.value


def _make_context(
    slug="ledger-service",
    name="Ledger Service",
    architecture="microservice",
    deps=(),
    events=(),
    features=(),
) -> ServiceContext:
    if not features:
        features = (
            FeatureInfo(
                id="001",
                name="transactions",
                display_name="Transaction Processing",
                description="Handle transactions",
                priority="P1",
                category="core",
            ),
        )
    return ServiceContext(
        service_slug=slug,
        service_name=name,
        architecture=architecture,
        project_description="PersonalFinance",
        domain="finance",
        features=features,
        dependencies=deps,
        events=events,
        output_dir=Path("/tmp/features") / slug,
    )


def _make_analyzer(patterns, architecture="microservice"):
    return EdgeCaseAnalyzer(
        patterns=patterns,
        arch_filter=ArchitectureEdgeCaseFilter(architecture),
        budget=EdgeCaseBudget(),
    )


def _run(patterns, **ctx_kwargs) -> EdgeCaseReport:
    """Shorthand: build context + analyzer, run analysis, return report."""
    ctx = _make_context(**ctx_kwargs)
    result = _make_analyzer(patterns, ctx_kwargs.get("architecture", "microservice")).analyze(ctx)
    assert result.ok
    return result.value


# ---------------------------------------------------------------------------
# T014 — Dependency-based edge cases
# ---------------------------------------------------------------------------


class TestDependencyEdgeCases:
    """T014 — Edge cases generated from service dependencies."""

    @pytest.fixture()
    def required_sync_dep(self):
        return ServiceDependency(
            target_slug="identity-service",
            target_name="Identity Service",
            pattern="sync-rest",
            required=True,
            description="Authenticate users",
        )

    def test_required_sync_rest_produces_critical_severity(
        self, all_patterns, required_sync_dep,
    ):
        report = _run(all_patterns, deps=(required_sync_dep,))
        assert any(ec.severity == "critical" for ec in report.edge_cases)

    def test_service_unavailability_mentions_target(
        self, all_patterns, required_sync_dep,
    ):
        report = _run(all_patterns, deps=(required_sync_dep,))
        assert any(
            ec.category == "service_unavailability"
            and "identity" in ec.scenario.lower()
            for ec in report.edge_cases
        )

    def test_handling_strategy_includes_circuit_breaker(
        self, all_patterns, required_sync_dep,
    ):
        report = _run(all_patterns, deps=(required_sync_dep,))
        assert any(
            "circuit_breaker" in ec.handling_strategy
            for ec in report.edge_cases
        )

    def test_affected_services_includes_both(
        self, all_patterns, required_sync_dep,
    ):
        report = _run(all_patterns, deps=(required_sync_dep,))
        assert any(
            "Ledger Service" in ec.affected_services
            and "Identity Service" in ec.affected_services
            for ec in report.edge_cases
        )

    def test_test_suggestion_mentions_target(
        self, all_patterns, required_sync_dep,
    ):
        report = _run(all_patterns, deps=(required_sync_dep,))
        assert any(
            "identity" in ec.test_suggestion.lower()
            for ec in report.edge_cases
        )

    def test_optional_sync_dep_produces_high(self, all_patterns):
        dep = ServiceDependency(
            target_slug="cache-service",
            target_name="Cache Service",
            pattern="sync-rest",
            required=False,
            description="Cache lookup",
        )
        report = _run(all_patterns, deps=(dep,))
        dep_cats = {"service_unavailability", "version_skew"}
        dep_cases = [ec for ec in report.edge_cases if ec.category in dep_cats]
        assert any(ec.severity == "high" for ec in dep_cases)

    def test_async_event_dep_produces_network_partition(self, all_patterns):
        dep = ServiceDependency(
            target_slug="notification-service",
            target_name="Notification Service",
            pattern="async-event",
            required=True,
            description="Send notifications",
        )
        report = _run(all_patterns, deps=(dep,))
        assert any(
            ec.category == "network_partition" for ec in report.edge_cases
        )

    def test_async_event_dep_severity_high_when_required(self, all_patterns):
        dep = ServiceDependency(
            target_slug="notification-service",
            target_name="Notification Service",
            pattern="async-event",
            required=True,
            description="Send notifications",
        )
        report = _run(all_patterns, deps=(dep,))
        microservice_cats = {
            "service_unavailability",
            "network_partition",
            "eventual_consistency",
            "distributed_transaction",
            "version_skew",
        }
        dep_cases = [
            ec for ec in report.edge_cases if ec.category in microservice_cats
        ]
        assert any(ec.severity == "high" for ec in dep_cases)


# ---------------------------------------------------------------------------
# T015 — Event-based edge cases
# ---------------------------------------------------------------------------


class TestEventEdgeCases:
    """T015 — Edge cases generated from event topology."""

    def test_eventual_consistency_per_consumer(self, all_patterns):
        event = EventInfo(
            name="transaction.created",
            producer="ledger-service",
            consumers=("analytics-service", "notification-service"),
            payload_summary="Transaction data",
        )
        report = _run(all_patterns, events=(event,))
        ec_cases = [
            ec for ec in report.edge_cases
            if ec.category == "eventual_consistency"
        ]
        assert len(ec_cases) >= 2

    def test_distributed_transaction_with_multi_consumer(self, all_patterns):
        event = EventInfo(
            name="transaction.created",
            producer="ledger-service",
            consumers=("analytics-service", "notification-service"),
            payload_summary="Transaction data",
        )
        report = _run(all_patterns, events=(event,))
        dt_cases = [
            ec for ec in report.edge_cases
            if ec.category == "distributed_transaction"
        ]
        assert len(dt_cases) >= 1

    def test_single_consumer_no_distributed_transaction(self, all_patterns):
        event = EventInfo(
            name="transaction.created",
            producer="ledger-service",
            consumers=("analytics-service",),
            payload_summary="Transaction data",
        )
        report = _run(all_patterns, events=(event,))
        dt_cases = [
            ec for ec in report.edge_cases
            if ec.category == "distributed_transaction"
        ]
        assert len(dt_cases) == 0

    def test_producer_gets_event_cases(self, all_patterns):
        event = EventInfo(
            name="transaction.created",
            producer="ledger-service",
            consumers=("analytics-service",),
            payload_summary="Transaction data",
        )
        report = _run(all_patterns, events=(event,))
        assert any(
            "transaction.created" in ec.scenario.lower()
            for ec in report.edge_cases
        )

    def test_consumer_gets_stale_data_case(self, all_patterns):
        event = EventInfo(
            name="user.updated",
            producer="identity-service",
            consumers=("ledger-service",),
            payload_summary="User profile data",
        )
        report = _run(all_patterns, events=(event,))
        ec_cases = [
            ec for ec in report.edge_cases
            if ec.category == "eventual_consistency"
        ]
        assert len(ec_cases) >= 1

    def test_dual_role_gets_both(self, all_patterns):
        event_produced = EventInfo(
            name="tx.created",
            producer="ledger-service",
            consumers=("analytics-service",),
            payload_summary="Transaction data",
        )
        event_consumed = EventInfo(
            name="user.updated",
            producer="identity-service",
            consumers=("ledger-service",),
            payload_summary="User profile data",
        )
        report = _run(all_patterns, events=(event_produced, event_consumed))
        ec_cases = [
            ec for ec in report.edge_cases
            if ec.category == "eventual_consistency"
        ]
        # 1 from producer role (per consumer) + 1 from consumer role (stale data)
        assert len(ec_cases) >= 2


# ---------------------------------------------------------------------------
# T016 — Edge cases and special scenarios
# ---------------------------------------------------------------------------


class TestSpecialScenarios:
    """T016 — Dangling refs, circular deps, budget cap, IDs, feature interaction."""

    def test_dangling_service_reference(self, all_patterns):
        dep = ServiceDependency(
            target_slug="phantom-service",
            target_name="phantom-service",
            pattern="sync-rest",
            required=True,
            description="Unknown dependency",
        )
        report = _run(all_patterns, deps=(dep,))
        assert any(
            "(service not found in manifest)" in ec.scenario
            for ec in report.edge_cases
        )

    def test_circular_dependency(self, all_patterns):
        dep_a = ServiceDependency(
            target_slug="billing-service",
            target_name="Billing Service",
            pattern="sync-rest",
            required=True,
            description="Process payments",
        )
        dep_b = ServiceDependency(
            target_slug="billing-service",
            target_name="Billing Service",
            pattern="sync-rest",
            required=True,
            description="Verify balance",
        )
        report = _run(all_patterns, deps=(dep_a, dep_b))
        assert any(
            "Circular dependency" in ec.scenario
            for ec in report.edge_cases
        )

    def test_zero_dep_microservice_omits_interservice(self, all_patterns):
        report = _run(all_patterns, deps=(), events=())
        interservice_categories = {
            "service_unavailability",
            "network_partition",
            "eventual_consistency",
            "distributed_transaction",
            "version_skew",
            "data_ownership",
        }
        report_categories = {ec.category for ec in report.edge_cases}
        assert report_categories.isdisjoint(interservice_categories)

    def test_budget_cap_enforced(self, all_patterns):
        deps = tuple(
            ServiceDependency(
                target_slug=f"svc-{i}",
                target_name=f"Service {i}",
                pattern="sync-rest",
                required=True,
                description=f"Dependency {i}",
            )
            for i in range(13)
        )
        report = _run(all_patterns, deps=deps)
        assert report.total_count <= 30

    def test_ids_sequential(self, all_patterns):
        report = _run(all_patterns)
        expected = [f"EC-{i:03d}" for i in range(1, report.total_count + 1)]
        actual = [ec.id for ec in report.edge_cases]
        assert actual == expected

    def test_all_ids_unique(self, all_patterns):
        dep = ServiceDependency(
            target_slug="identity-service",
            target_name="Identity Service",
            pattern="sync-rest",
            required=True,
            description="Auth",
        )
        report = _run(all_patterns, deps=(dep,))
        ids = [ec.id for ec in report.edge_cases]
        assert len(set(ids)) == len(ids)

    def test_feature_interaction_cases_with_3_features(self, all_patterns):
        features = (
            FeatureInfo(
                id="001",
                name="accounts",
                display_name="Account Management",
                description="Manage accounts",
                priority="P1",
                category="core",
            ),
            FeatureInfo(
                id="002",
                name="transactions",
                display_name="Transaction Processing",
                description="Handle transactions",
                priority="P1",
                category="core",
            ),
            FeatureInfo(
                id="003",
                name="reports",
                display_name="Financial Reports",
                description="Generate reports",
                priority="P2",
                category="reporting",
            ),
        )
        report = _run(all_patterns, features=features)
        interaction_cases = [
            ec
            for ec in report.edge_cases
            if "compete for shared resources" in ec.scenario
        ]
        assert len(interaction_cases) >= 2

    def test_single_feature_no_interaction(self, all_patterns):
        report = _run(all_patterns)
        interaction_cases = [
            ec
            for ec in report.edge_cases
            if "compete for shared resources" in ec.scenario
        ]
        assert len(interaction_cases) == 0


# ---------------------------------------------------------------------------
# T018 — End-to-end integration
# ---------------------------------------------------------------------------


class TestEndToEndPersonalFinance:
    """T018 — Full PersonalFinance-like topology through the analyzer."""

    def test_full_analysis(self, all_patterns):
        identity_dep = ServiceDependency(
            target_slug="identity-service",
            target_name="Identity Service",
            pattern="sync-rest",
            required=True,
            description="Authenticate users",
        )
        planning_dep = ServiceDependency(
            target_slug="planning-service",
            target_name="Planning Service",
            pattern="sync-rest",
            required=False,
            description="Budget planning",
        )
        event = EventInfo(
            name="transaction.created",
            producer="ledger-service",
            consumers=("analytics-service", "notification-service"),
            payload_summary="Transaction payload",
        )
        features = (
            FeatureInfo(
                id="001",
                name="accounts",
                display_name="Account Management",
                description="Manage accounts",
                priority="P1",
                category="core",
            ),
            FeatureInfo(
                id="002",
                name="transactions",
                display_name="Transaction Processing",
                description="Handle transactions",
                priority="P1",
                category="core",
            ),
            FeatureInfo(
                id="003",
                name="reports",
                display_name="Financial Reports",
                description="Generate reports",
                priority="P2",
                category="reporting",
            ),
        )
        ctx = _make_context(
            deps=(identity_dep, planning_dep),
            events=(event,),
            features=features,
        )
        analyzer = _make_analyzer(all_patterns)
        result = analyzer.analyze(ctx)

        # Analysis succeeds
        assert result.ok
        report = result.value

        # Budget: 6 base + 2*2 deps + 1*1 event_role + 2*2 extra_features = 15
        assert report.total_count == 15

        # Sequential IDs EC-001 through EC-015
        expected_ids = [f"EC-{i:03d}" for i in range(1, 16)]
        actual_ids = [ec.id for ec in report.edge_cases]
        assert actual_ids == expected_ids

        # At least 1 critical severity from required sync-rest dependency
        assert any(ec.severity == "critical" for ec in report.edge_cases)

        # Key microservice categories present
        categories = {ec.category for ec in report.edge_cases}
        assert "service_unavailability" in categories
        assert "eventual_consistency" in categories

        # No duplicate IDs
        assert len(set(actual_ids)) == len(actual_ids)
