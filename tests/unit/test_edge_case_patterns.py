"""Tests for YAML pattern loader (Feature 007)."""

from __future__ import annotations

import pytest

from specforge.core.edge_case_patterns import PatternLoader

ALL_CATEGORIES = frozenset({
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
})


@pytest.fixture(scope="module")
def loaded_patterns():
    """Load patterns once for the entire module."""
    loader = PatternLoader()
    result = loader.load_patterns()
    assert result.ok, f"Pattern loading failed: {result.error}"
    return result.value


class TestLoadPatternsResult:
    """load_patterns returns a successful Ok containing a tuple."""

    def test_returns_ok(self) -> None:
        loader = PatternLoader()
        result = loader.load_patterns()
        assert result.ok is True

    def test_value_is_tuple(self, loaded_patterns) -> None:
        assert isinstance(loaded_patterns, tuple)


class TestCategoryCoverage:
    """All 13 edge case categories must be represented."""

    def test_all_13_categories_present(self, loaded_patterns) -> None:
        categories = {p.category for p in loaded_patterns}
        assert categories == ALL_CATEGORIES


class TestPatternFieldsNonEmpty:
    """Every loaded pattern must have non-empty required fields."""

    def test_each_has_nonempty_category(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert p.category != "", f"Empty category in {p}"

    def test_each_has_nonempty_scenario_template(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert p.scenario_template != "", f"Empty scenario_template in {p}"

    def test_each_has_nonempty_trigger_template(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert p.trigger_template != "", f"Empty trigger_template in {p}"

    def test_each_has_nonempty_handling_strategies(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert len(p.handling_strategies) > 0, f"Empty handling_strategies in {p}"

    def test_each_has_nonempty_test_template(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert p.test_template != "", f"Empty test_template in {p}"


class TestPatternFieldTypes:
    """Type contracts on loaded pattern fields."""

    def test_applicable_patterns_is_tuple(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert isinstance(p.applicable_patterns, tuple), f"Not a tuple in {p}"

    def test_severity_fields_are_str_or_none(self, loaded_patterns) -> None:
        for p in loaded_patterns:
            assert isinstance(p.severity_microservice, (str, type(None))), (
                f"Bad severity_microservice type in {p}"
            )
            assert isinstance(p.severity_monolith, (str, type(None))), (
                f"Bad severity_monolith type in {p}"
            )


class TestCaching:
    """PatternLoader caches results across calls."""

    def test_second_call_returns_same_object(self) -> None:
        loader = PatternLoader()
        first = loader.load_patterns()
        second = loader.load_patterns()
        assert first.value is second.value


class TestPatternCount:
    """Minimum pattern count: 13 categories × 2 scenarios each."""

    def test_at_least_26_patterns(self, loaded_patterns) -> None:
        assert len(loaded_patterns) >= 26
