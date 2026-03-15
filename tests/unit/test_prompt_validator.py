"""Unit tests for PromptValidator conflict detection — T028 through T031."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.config import GOVERNANCE_DOMAINS, PRECEDENCE_ORDER
from specforge.core.prompt_models import (
    ConflictEntry,
    ConflictReport,
    PromptFile,
    PromptFileMeta,
    PromptRule,
    PromptSet,
    PromptThreshold,
)


def _make_meta(
    domain: str,
    precedence: int,
    stack: str = "agnostic",
) -> PromptFileMeta:
    return PromptFileMeta(
        domain=domain,
        stack=stack,
        version="1.0",
        precedence=precedence,
        checksum="abc123",
    )


def _make_rule(
    rule_id: str,
    thresholds: tuple[PromptThreshold, ...] = (),
    description: str = "All code MUST comply.",
) -> PromptRule:
    return PromptRule(
        rule_id=rule_id,
        title="Test Rule",
        severity="ERROR",
        scope="all files",
        description=description,
        thresholds=thresholds,
        example_correct="correct",
        example_incorrect="incorrect",
    )


def _make_prompt_file(
    domain: str,
    precedence: int,
    rules: tuple[PromptRule, ...],
    stack: str = "agnostic",
) -> PromptFile:
    return PromptFile(
        path=Path(f"/tmp/{domain}.prompts.md"),
        meta=_make_meta(domain, precedence, stack),
        rules=rules,
        raw_content=f"# {domain}\n",
    )


def _make_prompt_set(files: dict[str, PromptFile]) -> PromptSet:
    return PromptSet(
        files=files,
        precedence=list(PRECEDENCE_ORDER),
        feature_id="feat-001",
    )


class TestPromptValidatorNoConflicts:
    """T028 — detect_conflicts() returns empty ConflictReport when no overlapping thresholds."""

    def test_no_conflicts_when_non_overlapping_thresholds(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "security": _make_prompt_file(
                "security", 1,
                rules=(_make_rule("SEC-001", thresholds=(
                    PromptThreshold("min_password_length", "12"),
                )),)
            ),
            "architecture": _make_prompt_file(
                "architecture", 2,
                rules=(_make_rule("ARCH-001", thresholds=(
                    PromptThreshold("max_class_lines", "200"),
                )),)
            ),
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_method_lines", "30"),
                )),)
            ),
            "frontend": _make_prompt_file(
                "frontend", 3,
                rules=(_make_rule("FRONT-001", thresholds=(
                    PromptThreshold("max_component_lines", "150"),
                )),)
            ),
            "database": _make_prompt_file(
                "database", 3,
                rules=(_make_rule("DB-001", thresholds=(
                    PromptThreshold("max_query_lines", "30"),
                )),)
            ),
            "testing": _make_prompt_file(
                "testing", 4,
                rules=(_make_rule("TEST-001", thresholds=(
                    PromptThreshold("min_coverage_pct", "80"),
                )),)
            ),
            "cicd": _make_prompt_file(
                "cicd", 5,
                rules=(_make_rule("CICD-001", thresholds=(
                    PromptThreshold("max_build_minutes", "10"),
                )),)
            ),
        }
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        assert isinstance(report, ConflictReport)
        assert not report.has_conflicts
        assert len(report.conflicts) == 0

    def test_no_conflicts_when_files_have_no_thresholds(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            domain: _make_prompt_file(
                domain, i + 1, rules=(_make_rule(f"RULE-{i:03d}", thresholds=()),)
            )
            for i, domain in enumerate(GOVERNANCE_DOMAINS)
        }
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        assert not report.has_conflicts


class TestPromptValidatorCrossPriorityConflict:
    """T029 — detect_conflicts() detects cross-priority conflict (architecture vs backend)."""

    def test_architecture_wins_over_backend_for_max_class_lines(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "architecture": _make_prompt_file(
                "architecture", 2,
                rules=(_make_rule("ARCH-001", thresholds=(
                    PromptThreshold("max_class_lines", "50"),
                )),)
            ),
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_class_lines", "200"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        assert report.has_conflicts
        assert len(report.conflicts) >= 1

        conflict = next(
            c for c in report.conflicts if c.threshold_key == "max_class_lines"
        )
        assert conflict.winning_domain == "architecture"
        assert conflict.winning_value == "50"
        assert not conflict.is_ambiguous

    def test_security_wins_over_architecture_for_shared_threshold(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "security": _make_prompt_file(
                "security", 1,
                rules=(_make_rule("SEC-001", thresholds=(
                    PromptThreshold("min_password_length", "16"),
                )),)
            ),
            "architecture": _make_prompt_file(
                "architecture", 2,
                rules=(_make_rule("ARCH-001", thresholds=(
                    PromptThreshold("min_password_length", "8"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        conflict = next(
            c for c in report.conflicts if c.threshold_key == "min_password_length"
        )
        assert conflict.winning_domain == "security"
        assert conflict.winning_value == "16"
        assert not conflict.is_ambiguous


class TestPromptValidatorAmbiguousConflict:
    """T030 — detect_conflicts() detects intra-priority ambiguous conflict."""

    def test_backend_vs_database_is_ambiguous(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_query_lines", "20"),
                )),)
            ),
            "database": _make_prompt_file(
                "database", 3,
                rules=(_make_rule("DB-001", thresholds=(
                    PromptThreshold("max_query_lines", "50"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        assert report.has_conflicts
        conflict = next(
            c for c in report.conflicts if c.threshold_key == "max_query_lines"
        )
        assert conflict.is_ambiguous
        assert conflict.winning_domain == "AMBIGUOUS"

    def test_frontend_vs_backend_equal_priority_is_ambiguous(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "frontend": _make_prompt_file(
                "frontend", 3,
                rules=(_make_rule("FRONT-001", thresholds=(
                    PromptThreshold("max_lines", "100"),
                )),)
            ),
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_lines", "200"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        conflict = next(
            c for c in report.conflicts if c.threshold_key == "max_lines"
        )
        assert conflict.is_ambiguous

    def test_ambiguous_conflict_has_suggested_resolution(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_query_lines", "20"),
                )),)
            ),
            "database": _make_prompt_file(
                "database", 3,
                rules=(_make_rule("DB-001", thresholds=(
                    PromptThreshold("max_query_lines", "50"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        conflict = next(
            c for c in report.conflicts if c.threshold_key == "max_query_lines"
        )
        assert len(conflict.suggested_resolution) > 0


class TestPromptValidatorAllConflictsReported:
    """T031 — detect_conflicts() reports ALL conflicts in one pass (not just first)."""

    def test_three_conflicts_reported_in_one_call(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        # Set up 3 threshold conflicts
        files = {
            "architecture": _make_prompt_file(
                "architecture", 2,
                rules=(_make_rule("ARCH-001", thresholds=(
                    PromptThreshold("max_class_lines", "50"),   # conflicts with backend
                    PromptThreshold("max_method_lines", "20"),  # conflicts with backend
                    PromptThreshold("max_query_lines", "10"),   # conflicts with database
                )),)
            ),
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_class_lines", "200"),
                    PromptThreshold("max_method_lines", "40"),
                )),)
            ),
            "database": _make_prompt_file(
                "database", 3,
                rules=(_make_rule("DB-001", thresholds=(
                    PromptThreshold("max_query_lines", "30"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        assert report.has_conflicts
        assert len(report.conflicts) == 3

    def test_conflict_report_counts_match_conflict_entries(self) -> None:
        from specforge.core.prompt_validator import PromptValidator

        files = {
            "backend": _make_prompt_file(
                "backend", 3,
                rules=(_make_rule("BACK-001", thresholds=(
                    PromptThreshold("max_lines", "30"),
                    PromptThreshold("max_complexity", "5"),
                )),)
            ),
            "frontend": _make_prompt_file(
                "frontend", 3,
                rules=(_make_rule("FRONT-001", thresholds=(
                    PromptThreshold("max_lines", "150"),
                    PromptThreshold("max_complexity", "10"),
                )),)
            ),
        }
        files.update({
            d: _make_prompt_file(d, 3, rules=())
            for d in GOVERNANCE_DOMAINS if d not in files
        })
        prompt_set = _make_prompt_set(files)
        validator = PromptValidator()
        report = validator.detect_conflicts(prompt_set)

        # 2 shared keys × 1 pair = 2 conflicts
        assert len(report.conflicts) == 2
        assert report.has_conflicts == (len(report.conflicts) > 0)
