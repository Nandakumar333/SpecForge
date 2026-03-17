"""Tests for monolith & modular-monolith edge case generation (T019 + T020)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.edge_case_analyzer import EdgeCaseAnalyzer
from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_patterns import PatternLoader
from specforge.core.service_context import FeatureInfo, ServiceContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STANDARD_CATEGORIES = {
    "concurrency",
    "data_boundary",
    "state_machine",
    "ui_ux",
    "security",
    "data_migration",
}

_MICROSERVICE_CATEGORIES = {
    "service_unavailability",
    "network_partition",
    "eventual_consistency",
    "distributed_transaction",
    "version_skew",
    "data_ownership",
}

_SEVERITY_MATRIX_MONOLITH = {
    "security": "high",
    "concurrency": "high",
    "data_boundary": "medium",
    "state_machine": "medium",
    "ui_ux": "low",
    "data_migration": "low",
}

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_patterns():
    loader = PatternLoader()
    result = loader.load_patterns()
    assert result.ok
    return result.value


def _make_context(
    slug="auth-module",
    name="Auth Module",
    architecture="monolithic",
    features=(),
) -> ServiceContext:
    if not features:
        features = (
            FeatureInfo(
                id="001",
                name="auth",
                display_name="Authentication",
                description="User login",
                priority="P1",
                category="core",
            ),
        )
    return ServiceContext(
        service_slug=slug,
        service_name=name,
        architecture=architecture,
        project_description="MyApp",
        domain="web",
        features=features,
        dependencies=(),
        events=(),
        output_dir=Path("/tmp/features") / slug,
    )


def _make_analyzer(patterns, architecture):
    return EdgeCaseAnalyzer(
        patterns=patterns,
        arch_filter=ArchitectureEdgeCaseFilter(architecture),
        budget=EdgeCaseBudget(),
    )


def _three_features():
    return (
        FeatureInfo(
            id="001", name="auth", display_name="Authentication",
            description="User login", priority="P1", category="core",
        ),
        FeatureInfo(
            id="002", name="billing", display_name="Billing",
            description="Payments", priority="P1", category="core",
        ),
        FeatureInfo(
            id="003", name="reports", display_name="Reports",
            description="Reporting", priority="P2", category="analytics",
        ),
    )


# ===================================================================
# T019 — Monolith edge case generation
# ===================================================================


class TestMonolithEdgeCases:
    """Monolithic architecture: only standard-category cases + feature interaction."""

    def test_single_feature_produces_6_cases(self, all_patterns) -> None:
        """1 feature → exactly 6 standard-category cases, no feature-interaction."""
        ctx = _make_context(architecture="monolithic")
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        report = result.value
        assert report.total_count == 6

    def test_multi_feature_produces_more(self, all_patterns) -> None:
        """3 features → 6 standard + 2 feature-interaction = 8 generated.

        Budget = 6 + 2*max(0,2) = 10, so all 8 fit.
        """
        ctx = _make_context(
            architecture="monolithic", features=_three_features(),
        )
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        report = result.value
        assert report.total_count > 6
        assert report.total_count == 8

    def test_only_standard_categories(self, all_patterns) -> None:
        """Every edge case category belongs to the 6 standard categories."""
        ctx = _make_context(architecture="monolithic")
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        categories = {ec.category for ec in result.value.edge_cases}
        assert categories <= _STANDARD_CATEGORIES

    def test_no_distributed_system_categories(self, all_patterns) -> None:
        """Zero cases with any microservice-only category."""
        ctx = _make_context(
            architecture="monolithic", features=_three_features(),
        )
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        categories = {ec.category for ec in result.value.edge_cases}
        assert categories.isdisjoint(_MICROSERVICE_CATEGORIES)

    def test_severity_matches_monolith_matrix(self, all_patterns) -> None:
        """Standard cases carry the correct severity from SEVERITY_MATRIX_MONOLITH."""
        ctx = _make_context(architecture="monolithic")
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        # With 1 feature there are no feature-interaction cases,
        # so all 6 cases are the standard ones.
        for ec in result.value.edge_cases:
            expected = _SEVERITY_MATRIX_MONOLITH[ec.category]
            assert ec.severity == expected, (
                f"category={ec.category}: expected severity "
                f"'{expected}', got '{ec.severity}'"
            )

    def test_all_ids_sequential(self, all_patterns) -> None:
        """IDs run EC-001 … EC-NNN with no gaps."""
        ctx = _make_context(
            architecture="monolithic", features=_three_features(),
        )
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        ids = [ec.id for ec in result.value.edge_cases]
        n = len(ids)
        expected = [f"EC-{i:03d}" for i in range(1, n + 1)]
        assert ids == expected

    def test_report_architecture_field(self, all_patterns) -> None:
        """Report carries the architecture from the service context."""
        ctx = _make_context(architecture="monolithic")
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        assert result.value.architecture == "monolithic"

    def test_affected_services_is_self(self, all_patterns) -> None:
        """Standard monolith cases reference only the service itself."""
        ctx = _make_context(architecture="monolithic")
        analyzer = _make_analyzer(all_patterns, "monolithic")
        result = analyzer.analyze(ctx)
        assert result.ok
        for ec in result.value.edge_cases:
            assert ctx.service_slug in ec.affected_services


# ===================================================================
# T020 — Modular-monolith edge case generation
# ===================================================================


class TestModularMonolithEdgeCases:
    """Modular-monolith: standard cases + interface_contract_violation."""

    def test_includes_interface_contract_violation(self, all_patterns) -> None:
        """At least one case has category 'interface_contract_violation'."""
        ctx = _make_context(architecture="modular-monolith")
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        categories = {ec.category for ec in result.value.edge_cases}
        assert "interface_contract_violation" in categories

    def test_interface_contract_severity_is_high(self, all_patterns) -> None:
        """interface_contract_violation case has severity 'high'."""
        ctx = _make_context(architecture="modular-monolith")
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        ic_cases = [
            ec for ec in result.value.edge_cases
            if ec.category == "interface_contract_violation"
        ]
        assert ic_cases, "Expected at least one interface_contract_violation case"
        for ec in ic_cases:
            assert ec.severity == "high"

    def test_no_microservice_categories(self, all_patterns) -> None:
        """Zero cases with any microservice-only category."""
        ctx = _make_context(
            architecture="modular-monolith", features=_three_features(),
        )
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        categories = {ec.category for ec in result.value.edge_cases}
        assert categories.isdisjoint(_MICROSERVICE_CATEGORIES)

    def test_total_count_two_features(self, all_patterns) -> None:
        """2 features → 6 standard + 1 interface + 1 feature-interaction = 8.

        Budget = 6 + 2*max(0,1) = 8, so all 8 fit.
        """
        features = _three_features()[:2]
        ctx = _make_context(architecture="modular-monolith", features=features)
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        assert result.value.total_count == 8

    def test_ids_sequential(self, all_patterns) -> None:
        """IDs run EC-001 … EC-NNN with no gaps."""
        ctx = _make_context(architecture="modular-monolith")
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        ids = [ec.id for ec in result.value.edge_cases]
        expected = [f"EC-{i:03d}" for i in range(1, len(ids) + 1)]
        assert ids == expected

    def test_report_architecture_field(self, all_patterns) -> None:
        """Report carries the modular-monolith architecture."""
        ctx = _make_context(architecture="modular-monolith")
        analyzer = _make_analyzer(all_patterns, "modular-monolith")
        result = analyzer.analyze(ctx)
        assert result.ok
        assert result.value.architecture == "modular-monolith"
