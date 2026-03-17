"""Tests for PromptRuleChecker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import logging

import pytest

from specforge.core.checkers.prompt_rule_checker import PromptRuleChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory
from specforge.core.result import Ok


# ── Fake models for test isolation ────────────────────────────────────


@dataclass(frozen=True)
class FakeThreshold:
    key: str
    value: str


@dataclass(frozen=True)
class FakeRule:
    rule_id: str
    title: str
    description: str
    thresholds: tuple


@dataclass(frozen=True)
class FakeFileMeta:
    domain: str
    stack: str
    version: str
    precedence: int
    checksum: str


@dataclass(frozen=True)
class FakePromptFile:
    path: Path
    meta: FakeFileMeta
    rules: tuple
    raw_content: str


@dataclass(frozen=True)
class FakePromptSet:
    files: dict
    precedence: list
    feature_id: str


class FakeLoader:
    """Fake prompt loader that returns a configured PromptSet."""

    def __init__(self, prompt_set: FakePromptSet) -> None:
        self._ps = prompt_set

    def load_for_feature(self, feature_id: str) -> Ok:
        return Ok(self._ps)


def _make_prompt_set(
    rules: tuple = (),
) -> FakePromptSet:
    """Build a FakePromptSet with given rules in one file."""
    meta = FakeFileMeta("test", "python", "1.0", 1, "abc")
    pfile = FakePromptFile(
        path=Path("test.md"),
        meta=meta,
        rules=rules,
        raw_content="",
    )
    return FakePromptSet(
        files={"test": pfile},
        precedence=["test"],
        feature_id="feat-001",
    )


# ── Properties ────────────────────────────────────────────────────────


class TestProperties:
    def test_name(self) -> None:
        assert PromptRuleChecker().name == "prompt-rule"

    def test_category_is_lint(self) -> None:
        assert PromptRuleChecker().category == ErrorCategory.LINT

    def test_levels(self) -> None:
        assert PromptRuleChecker().levels == (CheckLevel.TASK,)

    def test_applicable_all(self) -> None:
        checker = PromptRuleChecker()
        assert checker.is_applicable("monolithic")


# ── No loader → skipped ──────────────────────────────────────────────


class TestNoLoader:
    def test_no_loader_skips(self) -> None:
        checker = PromptRuleChecker(prompt_loader=None)
        result = checker.check([], None)
        assert result.ok
        assert result.value.skipped is True
        assert result.value.skip_reason == "No prompt loader configured"
        assert result.value.passed is True


# ── Threshold extraction ──────────────────────────────────────────────


class TestThresholdExtraction:
    def test_known_thresholds_extracted(self) -> None:
        rules = (
            FakeRule(
                rule_id="R001",
                title="Line limit",
                description="Keep functions short",
                thresholds=(
                    FakeThreshold("max_function_lines", "30"),
                    FakeThreshold("max_class_lines", "200"),
                ),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert result.value.passed is True
        assert "line-limit:function=30" in result.value.output
        assert "line-limit:class=200" in result.value.output

    def test_coverage_threshold_extracted(self) -> None:
        rules = (
            FakeRule(
                rule_id="R002",
                title="Coverage",
                description="Minimum coverage",
                thresholds=(
                    FakeThreshold("min_coverage_percent", "80"),
                ),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert "coverage=80" in result.value.output

    def test_extracted_thresholds_property(self) -> None:
        rules = (
            FakeRule(
                rule_id="R001",
                title="Limits",
                description="Size limits",
                thresholds=(
                    FakeThreshold("max_function_lines", "25"),
                    FakeThreshold("min_coverage_percent", "90"),
                ),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        checker.check([], None)
        thresholds = checker.extracted_thresholds
        assert thresholds == {
            "line-limit:function": "25",
            "coverage": "90",
        }

    def test_extracted_thresholds_empty_before_check(self) -> None:
        checker = PromptRuleChecker()
        assert checker.extracted_thresholds == {}

    def test_unknown_threshold_logged_and_added_to_tier2(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        rules = (
            FakeRule(
                rule_id="R099",
                title="Custom",
                description="Custom rule",
                thresholds=(
                    FakeThreshold("max_widget_count", "10"),
                ),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        with caplog.at_level(logging.WARNING):
            result = checker.check([], None)
        assert result.ok
        assert result.value.passed is True
        assert "Unmapped threshold key: max_widget_count" in caplog.text
        assert "Tier 2 context" in result.value.output
        assert "max_widget_count=10" in result.value.output


# ── Tier 2 descriptive rules ─────────────────────────────────────────


class TestTier2Rules:
    def test_tier2_rules_collected(self) -> None:
        rules = (
            FakeRule(
                rule_id="R010",
                title="Code style",
                description="Follow PEP 8 naming conventions",
                thresholds=(),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert "Tier 2 context" in result.value.output
        assert "R010" in result.value.output
        assert "Code style" in result.value.output

    def test_mixed_tier1_and_tier2(self) -> None:
        rules = (
            FakeRule(
                rule_id="R001",
                title="Limits",
                description="Size limits",
                thresholds=(
                    FakeThreshold("max_function_lines", "25"),
                ),
            ),
            FakeRule(
                rule_id="R020",
                title="Naming",
                description="Use snake_case",
                thresholds=(),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert "Tier 1 thresholds" in result.value.output
        assert "Tier 2 context" in result.value.output


# ── Multi-domain extraction ──────────────────────────────────────────


def _make_multi_domain_prompt_set(
    domain_rules: dict[str, tuple],
) -> FakePromptSet:
    """Build a FakePromptSet with rules across multiple governance domains."""
    files: dict[str, FakePromptFile] = {}
    for domain, rules in domain_rules.items():
        meta = FakeFileMeta(domain, "python", "1.0", 1, "abc")
        pfile = FakePromptFile(
            path=Path(f"{domain}.md"),
            meta=meta,
            rules=rules,
            raw_content="",
        )
        files[domain] = pfile
    return FakePromptSet(
        files=files,
        precedence=list(domain_rules.keys()),
        feature_id="feat-001",
    )


class TestMultipleDomains:
    def test_thresholds_from_different_domains(self) -> None:
        domain_rules = {
            "backend": (
                FakeRule(
                    rule_id="B01",
                    title="Function size",
                    description="Limit function length",
                    thresholds=(FakeThreshold("max_function_lines", "30"),),
                ),
            ),
            "testing": (
                FakeRule(
                    rule_id="T01",
                    title="Coverage",
                    description="Minimum coverage",
                    thresholds=(FakeThreshold("min_coverage_percent", "80"),),
                ),
            ),
        }
        ps = _make_multi_domain_prompt_set(domain_rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert "line-limit:function=30" in result.value.output
        assert "coverage=80" in result.value.output
        assert checker.extracted_thresholds["line-limit:function"] == "30"
        assert checker.extracted_thresholds["coverage"] == "80"


# ── Check always passes ──────────────────────────────────────────────


class TestAlwaysPasses:
    def test_passes_with_no_rules(self) -> None:
        ps = _make_prompt_set(rules=())
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert result.value.passed is True

    def test_passes_with_unknown_thresholds(self) -> None:
        rules = (
            FakeRule(
                rule_id="R099",
                title="Custom",
                description="Custom rule",
                thresholds=(FakeThreshold("unknown_key", "42"),),
            ),
        )
        ps = _make_prompt_set(rules=rules)
        checker = PromptRuleChecker(prompt_loader=FakeLoader(ps))
        result = checker.check([], None)
        assert result.ok
        assert result.value.passed is True
