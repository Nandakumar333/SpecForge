"""Tests for architecture edge case filter (Feature 007)."""

from __future__ import annotations

import warnings

import pytest

from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_models import EdgeCasePattern


def _make_pattern(category: str) -> EdgeCasePattern:
    """Build a minimal EdgeCasePattern with the given category."""
    return EdgeCasePattern(
        category=category,
        scenario_template=f"{category} scenario",
        trigger_template=f"{category} trigger",
        handling_strategies=("retry",),
        severity_microservice=None,
        severity_monolith=None,
        test_template=f"{category} test",
        applicable_patterns=(),
    )


@pytest.fixture()
def all_patterns() -> tuple[EdgeCasePattern, ...]:
    """One pattern per category — 13 total (6 standard + 6 microservice + 1 modular-monolith)."""
    cats = [
        "concurrency",
        "data_boundary",
        "state_machine",
        "ui_ux",
        "security",
        "data_migration",
        "service_unavailability",
        "network_partition",
        "eventual_consistency",
        "distributed_transaction",
        "version_skew",
        "data_ownership",
        "interface_contract_violation",
    ]
    return tuple(_make_pattern(c) for c in cats)


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


class TestMicroserviceFilter:
    """Microservice architecture keeps every category."""

    def test_keeps_all_13(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("microservice")
        result = flt.filter_patterns(all_patterns)
        assert len(result) == 13


class TestMonolithFilter:
    """Monolithic architecture keeps only the 6 standard categories."""

    def test_keeps_standard_count(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("monolithic")
        result = flt.filter_patterns(all_patterns)
        assert len(result) == 6

    def test_keeps_only_standard_categories(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("monolithic")
        result = flt.filter_patterns(all_patterns)
        result_cats = {p.category for p in result}
        assert result_cats == _STANDARD_CATEGORIES

    def test_excludes_microservice_categories(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("monolithic")
        result = flt.filter_patterns(all_patterns)
        result_cats = {p.category for p in result}
        assert result_cats.isdisjoint(_MICROSERVICE_CATEGORIES)

    def test_excludes_interface_contract_violation(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("monolithic")
        result = flt.filter_patterns(all_patterns)
        result_cats = {p.category for p in result}
        assert "interface_contract_violation" not in result_cats


class TestModularMonolithFilter:
    """Modular-monolith keeps standard + interface_contract_violation."""

    def test_keeps_standard_plus_extra(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("modular-monolith")
        result = flt.filter_patterns(all_patterns)
        assert len(result) == 7

    def test_excludes_microservice_categories(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("modular-monolith")
        result = flt.filter_patterns(all_patterns)
        result_cats = {p.category for p in result}
        assert result_cats.isdisjoint(_MICROSERVICE_CATEGORIES)


class TestUnknownArchitectureFallback:
    """Unknown architecture falls back to monolith behaviour with a warning."""

    def test_falls_back_to_monolith_count(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("serverless")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = flt.filter_patterns(all_patterns)
        assert len(result) == 6

    def test_emits_user_warning(
        self, all_patterns: tuple[EdgeCasePattern, ...]
    ) -> None:
        flt = ArchitectureEdgeCaseFilter("serverless")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            flt.filter_patterns(all_patterns)
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "Unknown architecture" in str(caught[0].message)
