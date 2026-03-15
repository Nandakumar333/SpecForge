"""Unit tests for prompt domain dataclass invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.prompt_models import (
    ConflictEntry,
    ConflictReport,
    ProjectMeta,
    PromptFile,
    PromptFileMeta,
    PromptRule,
    PromptSet,
    PromptThreshold,
)


class TestPromptThreshold:
    def test_frozen(self) -> None:
        t = PromptThreshold(key="min_coverage", value="80")
        with pytest.raises(AttributeError):
            t.key = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        t = PromptThreshold(key="max_lines", value="200")
        assert t.key == "max_lines"
        assert t.value == "200"


class TestPromptRule:
    def test_frozen(self) -> None:
        rule = _make_rule()
        with pytest.raises(AttributeError):
            rule.rule_id = "OTHER-001"  # type: ignore[misc]

    def test_empty_thresholds_tuple(self) -> None:
        rule = _make_rule(thresholds=())
        assert rule.thresholds == ()

    def test_thresholds_are_tuple(self) -> None:
        thresh = PromptThreshold(key="k", value="v")
        rule = _make_rule(thresholds=(thresh,))
        assert isinstance(rule.thresholds, tuple)
        assert len(rule.thresholds) == 1

    def test_severity_error(self) -> None:
        rule = _make_rule(severity="ERROR")
        assert rule.severity == "ERROR"

    def test_severity_warning(self) -> None:
        rule = _make_rule(severity="WARNING")
        assert rule.severity == "WARNING"

    def test_rule_id_stored(self) -> None:
        rule = _make_rule(rule_id="ARCH-001")
        assert rule.rule_id == "ARCH-001"


class TestPromptFileMeta:
    def test_frozen(self) -> None:
        meta = _make_meta()
        with pytest.raises(AttributeError):
            meta.domain = "other"  # type: ignore[misc]

    def test_precedence_int(self) -> None:
        meta = _make_meta(precedence=1)
        assert isinstance(meta.precedence, int)
        assert meta.precedence == 1

    def test_fields(self) -> None:
        meta = PromptFileMeta(
            domain="security",
            stack="agnostic",
            version="1.0",
            precedence=1,
            checksum="abc123",
        )
        assert meta.domain == "security"
        assert meta.stack == "agnostic"
        assert meta.version == "1.0"
        assert meta.precedence == 1
        assert meta.checksum == "abc123"


class TestPromptFile:
    def test_frozen(self) -> None:
        pf = _make_prompt_file()
        with pytest.raises(AttributeError):
            pf.raw_content = "changed"  # type: ignore[misc]

    def test_rules_are_tuple(self) -> None:
        pf = _make_prompt_file()
        assert isinstance(pf.rules, tuple)

    def test_path_stored(self) -> None:
        path = Path("/tmp/backend.prompts.md")
        pf = _make_prompt_file(path=path)
        assert pf.path == path


class TestPromptSet:
    def test_frozen(self) -> None:
        ps = PromptSet(files={}, precedence=[], feature_id="feat-001")
        with pytest.raises(AttributeError):
            ps.feature_id = "other"  # type: ignore[misc]

    def test_empty_files(self) -> None:
        ps = PromptSet(files={}, precedence=[], feature_id="feat-001")
        assert ps.files == {}

    def test_feature_id(self) -> None:
        ps = PromptSet(files={}, precedence=["security"], feature_id="feat-002")
        assert ps.feature_id == "feat-002"

    def test_precedence_list(self) -> None:
        order = ["security", "architecture"]
        ps = PromptSet(files={}, precedence=order, feature_id="x")
        assert ps.precedence == order


class TestConflictEntry:
    def test_frozen(self) -> None:
        ce = _make_conflict_entry()
        with pytest.raises(AttributeError):
            ce.threshold_key = "other"  # type: ignore[misc]

    def test_ambiguous_flag(self) -> None:
        ce = _make_conflict_entry(is_ambiguous=True, winning_domain="AMBIGUOUS")
        assert ce.is_ambiguous is True
        assert ce.winning_domain == "AMBIGUOUS"

    def test_non_ambiguous(self) -> None:
        ce = _make_conflict_entry(is_ambiguous=False, winning_domain="security")
        assert ce.is_ambiguous is False


class TestConflictReport:
    def test_frozen(self) -> None:
        cr = ConflictReport(conflicts=(), has_conflicts=False)
        with pytest.raises(AttributeError):
            cr.has_conflicts = True  # type: ignore[misc]

    def test_no_conflicts(self) -> None:
        cr = ConflictReport(conflicts=(), has_conflicts=False)
        assert not cr.has_conflicts
        assert len(cr.conflicts) == 0

    def test_has_conflicts_true(self) -> None:
        entry = _make_conflict_entry()
        cr = ConflictReport(conflicts=(entry,), has_conflicts=True)
        assert cr.has_conflicts
        assert len(cr.conflicts) == 1

    def test_conflicts_are_tuple(self) -> None:
        cr = ConflictReport(conflicts=(), has_conflicts=False)
        assert isinstance(cr.conflicts, tuple)


class TestProjectMeta:
    def test_frozen(self) -> None:
        pm = ProjectMeta(
            project_name="myapp",
            stack="dotnet",
            version="1.0",
            created_at="2026-03-15",
        )
        with pytest.raises(AttributeError):
            pm.project_name = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        pm = ProjectMeta(
            project_name="myapp",
            stack="dotnet",
            version="1.0",
            created_at="2026-03-15",
        )
        assert pm.project_name == "myapp"
        assert pm.stack == "dotnet"
        assert pm.version == "1.0"
        assert pm.created_at == "2026-03-15"


# ── helpers ────────────────────────────────────────────────────────────


def _make_rule(
    rule_id: str = "ARCH-001",
    title: str = "Single Responsibility",
    severity: str = "ERROR",
    scope: str = "class",
    description: str = "Classes MUST have one responsibility.",
    thresholds: tuple[PromptThreshold, ...] = (),
    example_correct: str = "class Foo: ...",
    example_incorrect: str = "class FooBar: ...",
) -> PromptRule:
    return PromptRule(
        rule_id=rule_id,
        title=title,
        severity=severity,
        scope=scope,
        description=description,
        thresholds=thresholds,
        example_correct=example_correct,
        example_incorrect=example_incorrect,
    )


def _make_meta(
    domain: str = "architecture",
    stack: str = "agnostic",
    version: str = "1.0",
    precedence: int = 2,
    checksum: str = "deadbeef",
) -> PromptFileMeta:
    return PromptFileMeta(
        domain=domain,
        stack=stack,
        version=version,
        precedence=precedence,
        checksum=checksum,
    )


def _make_prompt_file(
    path: Path = Path("/tmp/architecture.prompts.md"),
    rules: tuple[PromptRule, ...] = (),
) -> PromptFile:
    return PromptFile(
        path=path,
        meta=_make_meta(),
        rules=rules,
        raw_content="# Architecture Governance Prompt\n",
    )


def _make_conflict_entry(
    threshold_key: str = "max_class_lines",
    rule_id_a: str = "ARCH-001",
    domain_a: str = "architecture",
    value_a: str = "50",
    rule_id_b: str = "BACK-001",
    domain_b: str = "backend",
    value_b: str = "200",
    winning_domain: str = "architecture",
    winning_value: str = "50",
    is_ambiguous: bool = False,
    suggested_resolution: str = "Use architecture value (higher precedence).",
) -> ConflictEntry:
    return ConflictEntry(
        threshold_key=threshold_key,
        rule_id_a=rule_id_a,
        domain_a=domain_a,
        value_a=value_a,
        rule_id_b=rule_id_b,
        domain_b=domain_b,
        value_b=value_b,
        winning_domain=winning_domain,
        winning_value=winning_value,
        is_ambiguous=is_ambiguous,
        suggested_resolution=suggested_resolution,
    )
