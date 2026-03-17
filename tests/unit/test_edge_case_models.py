"""Tests for edge case data models (Feature 007)."""

from __future__ import annotations

import dataclasses

import pytest

from specforge.core.edge_case_models import (
    EdgeCase,
    EdgeCasePattern,
    EdgeCaseReport,
    make_edge_case_id,
)


@pytest.fixture()
def sample_edge_case() -> EdgeCase:
    """Reusable EdgeCase instance for multiple tests."""
    return EdgeCase(
        id="EC-001",
        category="concurrency",
        severity="high",
        scenario="Two users update the same record simultaneously",
        trigger="Concurrent PUT requests on the same resource",
        affected_services=("order-service", "inventory-service"),
        handling_strategy="Optimistic locking with version field",
        test_suggestion="Send parallel updates and verify conflict response",
    )


@pytest.fixture()
def sample_pattern() -> EdgeCasePattern:
    """Reusable EdgeCasePattern instance for multiple tests."""
    return EdgeCasePattern(
        category="data_boundary",
        scenario_template="Field {{field}} receives {{boundary_value}}",
        trigger_template="User submits {{boundary_value}} for {{field}}",
        handling_strategies=("validate input", "return 422"),
        severity_microservice="medium",
        severity_monolith="low",
        test_template="Submit {{boundary_value}} and assert rejection",
        applicable_patterns=("crud", "form-submission"),
    )


class TestEdgeCaseFrozen:
    """EdgeCase is a frozen dataclass — mutation must raise."""

    def test_cannot_mutate_field(self, sample_edge_case: EdgeCase) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_edge_case.severity = "low"  # type: ignore[misc]


class TestEdgeCaseFieldAccess:
    """All fields must be accessible and match construction parameters."""

    def test_all_fields_match(self, sample_edge_case: EdgeCase) -> None:
        assert sample_edge_case.id == "EC-001"
        assert sample_edge_case.category == "concurrency"
        assert sample_edge_case.severity == "high"
        assert sample_edge_case.scenario == "Two users update the same record simultaneously"
        assert sample_edge_case.trigger == "Concurrent PUT requests on the same resource"
        assert sample_edge_case.affected_services == ("order-service", "inventory-service")
        assert sample_edge_case.handling_strategy == "Optimistic locking with version field"
        assert sample_edge_case.test_suggestion == "Send parallel updates and verify conflict response"


class TestEdgeCaseAffectedServicesType:
    """affected_services must be a tuple."""

    def test_is_tuple(self, sample_edge_case: EdgeCase) -> None:
        assert isinstance(sample_edge_case.affected_services, tuple)


class TestEdgeCasePatternFrozen:
    """EdgeCasePattern is a frozen dataclass — mutation must raise."""

    def test_cannot_mutate_field(self, sample_pattern: EdgeCasePattern) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_pattern.category = "security"  # type: ignore[misc]


class TestEdgeCasePatternFields:
    """All EdgeCasePattern fields match construction parameters."""

    def test_all_fields_match(self, sample_pattern: EdgeCasePattern) -> None:
        assert sample_pattern.category == "data_boundary"
        assert sample_pattern.scenario_template == "Field {{field}} receives {{boundary_value}}"
        assert sample_pattern.trigger_template == "User submits {{boundary_value}} for {{field}}"
        assert sample_pattern.handling_strategies == ("validate input", "return 422")
        assert sample_pattern.severity_microservice == "medium"
        assert sample_pattern.severity_monolith == "low"
        assert sample_pattern.test_template == "Submit {{boundary_value}} and assert rejection"
        assert sample_pattern.applicable_patterns == ("crud", "form-submission")


class TestEdgeCasePatternTupleFields:
    """Tuple-typed fields must actually be tuples."""

    def test_handling_strategies_is_tuple(self, sample_pattern: EdgeCasePattern) -> None:
        assert isinstance(sample_pattern.handling_strategies, tuple)

    def test_applicable_patterns_is_tuple(self, sample_pattern: EdgeCasePattern) -> None:
        assert isinstance(sample_pattern.applicable_patterns, tuple)


class TestEdgeCasePatternSeverityNone:
    """Severity fields accept None when not applicable."""

    def test_severity_microservice_can_be_none(self) -> None:
        pattern = EdgeCasePattern(
            category="ui_ux",
            scenario_template="template",
            trigger_template="trigger",
            handling_strategies=("fallback",),
            severity_microservice=None,
            severity_monolith="low",
            test_template="test",
            applicable_patterns=(),
        )
        assert pattern.severity_microservice is None

    def test_severity_monolith_can_be_none(self) -> None:
        pattern = EdgeCasePattern(
            category="ui_ux",
            scenario_template="template",
            trigger_template="trigger",
            handling_strategies=("fallback",),
            severity_microservice="high",
            severity_monolith=None,
            test_template="test",
            applicable_patterns=(),
        )
        assert pattern.severity_monolith is None


class TestEdgeCaseReportFrozen:
    """EdgeCaseReport is a frozen dataclass — mutation must raise."""

    def test_cannot_mutate_field(self, sample_edge_case: EdgeCase) -> None:
        report = EdgeCaseReport(
            service_slug="order-service",
            architecture="microservice",
            edge_cases=(sample_edge_case,),
            total_count=1,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.total_count = 99  # type: ignore[misc]


class TestEdgeCaseReportCounts:
    """EdgeCaseReport total_count semantics."""

    def test_total_count_matches_len(self, sample_edge_case: EdgeCase) -> None:
        cases = (sample_edge_case,) * 3
        report = EdgeCaseReport(
            service_slug="inventory-service",
            architecture="monolith",
            edge_cases=cases,
            total_count=3,
        )
        assert report.total_count == len(report.edge_cases) == 3

    def test_empty_report(self) -> None:
        report = EdgeCaseReport(
            service_slug="empty-service",
            architecture="monolith",
            edge_cases=(),
            total_count=0,
        )
        assert report.total_count == 0
        assert len(report.edge_cases) == 0


class TestMakeEdgeCaseId:
    """make_edge_case_id returns EC-NNN formatted strings."""

    def test_single_digit(self) -> None:
        assert make_edge_case_id(1) == "EC-001"

    def test_double_digit(self) -> None:
        assert make_edge_case_id(10) == "EC-010"

    def test_triple_digit(self) -> None:
        assert make_edge_case_id(100) == "EC-100"
