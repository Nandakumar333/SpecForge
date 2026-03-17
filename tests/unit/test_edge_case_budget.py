"""Tests for edge case budget allocation (Feature 007)."""

from __future__ import annotations

import pytest

from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_models import EdgeCase


def _make_case(
    id_: str = "EC-001",
    severity: str = "medium",
    category: str = "concurrency",
) -> EdgeCase:
    """Build a minimal EdgeCase for testing."""
    return EdgeCase(
        id=id_,
        category=category,
        severity=severity,
        scenario="test scenario",
        trigger="test trigger",
        affected_services=("svc-a",),
        handling_strategy="retry",
        test_suggestion="test it",
    )


class TestAllocate:
    """EdgeCaseBudget.allocate computes: base + 2*deps + 1*events + 2*max(0, features-1), capped at 30."""

    def test_base_only(self) -> None:
        budget = EdgeCaseBudget()
        assert budget.allocate(0, 0, 1) == 6

    def test_with_deps(self) -> None:
        budget = EdgeCaseBudget()
        assert budget.allocate(2, 0, 1) == 10

    def test_with_events(self) -> None:
        budget = EdgeCaseBudget()
        assert budget.allocate(0, 3, 1) == 9

    def test_with_extra_features(self) -> None:
        budget = EdgeCaseBudget()
        assert budget.allocate(0, 0, 3) == 10

    def test_full_formula(self) -> None:
        budget = EdgeCaseBudget()
        # 6 + 2*2 + 1*1 + 2*max(0, 3-1) = 6 + 4 + 1 + 4 = 15
        assert budget.allocate(2, 1, 3) == 15

    def test_capped_at_30(self) -> None:
        budget = EdgeCaseBudget()
        assert budget.allocate(20, 10, 10) == 30

    def test_zero_features_means_zero_extra(self) -> None:
        budget = EdgeCaseBudget()
        # max(0, 0-1) = 0 → 6 + 0 + 0 + 0 = 6
        assert budget.allocate(0, 0, 0) == 6


class TestPrioritize:
    """EdgeCaseBudget.prioritize sorts by (severity_rank, category_priority), then truncates."""

    def test_sorts_by_severity(self) -> None:
        budget = EdgeCaseBudget()
        low = _make_case(id_="EC-001", severity="low")
        critical = _make_case(id_="EC-002", severity="critical")
        high = _make_case(id_="EC-003", severity="high")
        medium = _make_case(id_="EC-004", severity="medium")

        result = budget.prioritize((low, critical, high, medium), budget=10)
        assert [c.severity for c in result] == [
            "critical",
            "high",
            "medium",
            "low",
        ]

    def test_sorts_by_category_when_same_severity(self) -> None:
        budget = EdgeCaseBudget()
        # service_unavailability has priority 1, concurrency has priority 9
        conc = _make_case(id_="EC-001", severity="high", category="concurrency")
        svc = _make_case(id_="EC-002", severity="high", category="service_unavailability")

        result = budget.prioritize((conc, svc), budget=10)
        assert result[0].category == "service_unavailability"
        assert result[1].category == "concurrency"

    def test_truncates_to_budget(self) -> None:
        budget = EdgeCaseBudget()
        cases = tuple(_make_case(id_=f"EC-{i:03d}") for i in range(10))
        result = budget.prioritize(cases, budget=5)
        assert len(result) == 5

    def test_budget_larger_than_cases(self) -> None:
        budget = EdgeCaseBudget()
        cases = tuple(_make_case(id_=f"EC-{i:03d}") for i in range(3))
        result = budget.prioritize(cases, budget=10)
        assert len(result) == 3
