"""Unit tests for ClarificationRecorder — spec file annotation and persistence."""

from __future__ import annotations

import re
from pathlib import Path

from specforge.core.clarification_models import (
    AmbiguityMatch,
    ClarificationAnswer,
    ClarificationQuestion,
    SuggestedAnswer,
)
from specforge.core.clarification_recorder import ClarificationRecorder


def _make_recorder() -> ClarificationRecorder:
    """Return a default ClarificationRecorder."""
    return ClarificationRecorder()


def _make_question(
    *,
    qid: str = "CQ-001",
    category: str = "domain",
    question_text: str = "What does 'appropriately' mean for transaction processing?",
) -> ClarificationQuestion:
    return ClarificationQuestion(
        id=qid,
        category=category,
        context_excerpt="Transactions are handled appropriately.",
        question_text=question_text,
        suggested_answers=(
            SuggestedAnswer(
                label="A",
                text="Use industry-standard rules",
                implications="Requires domain expert review",
            ),
        ),
        source_match=AmbiguityMatch(
            text="appropriately",
            line_number=5,
            category=category,
            pattern_type="vague_term",
            confidence=1.0,
        ),
        impact_rank=1,
    )


def _make_answer(
    *,
    question_id: str = "CQ-001",
    answer_text: str = "Use industry-standard validation rules",
    is_custom: bool = False,
) -> ClarificationAnswer:
    return ClarificationAnswer(
        question_id=question_id,
        answer_text=answer_text,
        is_custom=is_custom,
        answered_at="2025-01-15T10:00:00",
    )


def _make_spec_text(*, with_clarifications: bool = False) -> str:
    """Return a minimal spec with an optional existing Clarifications section."""
    base = (
        "# Ledger Service Spec\n"
        "\n"
        "## Overview\n"
        "\n"
        "The ledger service manages financial data.\n"
        "\n"
        "## Requirements\n"
        "\n"
        "Transactions should be validated.\n"
    )
    if with_clarifications:
        base += (
            "\n"
            "## Clarifications\n"
            "\n"
            "### Session 2025-01-10\n"
            "\n"
            "- Q: [domain] What is a valid account? → A: Any active bank account\n"
        )
    base += "\n## Assumptions\n\nAll users are authenticated.\n"
    return base


def _write_spec(tmp_path: Path, text: str) -> Path:
    """Write spec text to a temp file and return the path."""
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(text, encoding="utf-8")
    return spec_file


class TestRecordNewSection:
    """record() creates a new Clarifications section when none exists."""

    def test_creates_clarifications_heading(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question()
        a = _make_answer()
        result = recorder.record(spec_path, (a,), (q,))
        assert result.ok
        content = spec_path.read_text(encoding="utf-8")
        assert "## Clarifications" in content

    def test_inserts_before_assumptions(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question()
        a = _make_answer()
        recorder.record(spec_path, (a,), (q,))
        content = spec_path.read_text(encoding="utf-8")
        clar_pos = content.index("## Clarifications")
        assume_pos = content.index("## Assumptions")
        assert clar_pos < assume_pos


class TestRecordAppendExisting:
    """record() appends to existing Clarifications section."""

    def test_preserves_prior_session(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text(with_clarifications=True))
        q = _make_question(qid="CQ-002", question_text="How are transfers validated?")
        a = _make_answer(question_id="CQ-002", answer_text="Via double-entry")
        recorder.record(spec_path, (a,), (q,))
        content = spec_path.read_text(encoding="utf-8")
        # Old session entry preserved
        assert "What is a valid account?" in content
        # New entry present
        assert "Via double-entry" in content

    def test_does_not_duplicate_heading(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text(with_clarifications=True))
        q = _make_question()
        a = _make_answer()
        recorder.record(spec_path, (a,), (q,))
        content = spec_path.read_text(encoding="utf-8")
        assert content.count("## Clarifications") == 1


class TestRecordSessionSubsection:
    """record() creates a Session YYYY-MM-DD subsection."""

    def test_session_heading_present(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question()
        a = _make_answer()
        recorder.record(spec_path, (a,), (q,))
        content = spec_path.read_text(encoding="utf-8")
        assert re.search(r"### Session \d{4}-\d{2}-\d{2}", content)


class TestRecordEntryFormat:
    """record() writes entries in the correct Q/A format."""

    def test_entry_format(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question(category="domain")
        a = _make_answer()
        recorder.record(spec_path, (a,), (q,))
        content = spec_path.read_text(encoding="utf-8")
        # Format: - Q: [{category}] {question_text} → A: {answer_text}
        assert "- Q: [domain]" in content
        assert "→ A:" in content

    def test_multiple_answers_in_session(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q1 = _make_question(qid="CQ-001", category="domain")
        q2 = _make_question(
            qid="CQ-002",
            category="technical",
            question_text="Which database engine?",
        )
        a1 = _make_answer(question_id="CQ-001")
        a2 = _make_answer(
            question_id="CQ-002",
            answer_text="PostgreSQL 15",
        )
        recorder.record(spec_path, (a1, a2), (q1, q2))
        content = spec_path.read_text(encoding="utf-8")
        assert "- Q: [domain]" in content
        assert "- Q: [technical]" in content
        assert "PostgreSQL 15" in content


class TestRecordAtomicWrite:
    """record() uses atomic write — file content exists after write."""

    def test_file_content_after_write(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question()
        a = _make_answer()
        recorder.record(spec_path, (a,), (q,))
        # File must exist and contain both original and new content
        content = spec_path.read_text(encoding="utf-8")
        assert "## Overview" in content
        assert "## Clarifications" in content


class TestRecordReturnValues:
    """record() returns Ok(path) on success, Err on failure."""

    def test_returns_ok_with_path(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q = _make_question()
        a = _make_answer()
        result = recorder.record(spec_path, (a,), (q,))
        assert result.ok
        assert result.value == spec_path

    def test_returns_err_for_missing_file(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        missing = tmp_path / "nonexistent.md"
        q = _make_question()
        a = _make_answer()
        result = recorder.record(missing, (a,), (q,))
        assert not result.ok
        assert isinstance(result.error, str)


class TestRecordSkippedQuestions:
    """Skipped questions (those without an answer) are NOT recorded."""

    def test_unanswered_not_written(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        spec_path = _write_spec(tmp_path, _make_spec_text())
        q1 = _make_question(qid="CQ-001")
        q2 = _make_question(qid="CQ-002", question_text="Skipped question?")
        # Only answer for CQ-001; CQ-002 is skipped
        a1 = _make_answer(question_id="CQ-001")
        recorder.record(spec_path, (a1,), (q1, q2))
        content = spec_path.read_text(encoding="utf-8")
        assert "Skipped question?" not in content


class TestMarkRevalidation:
    """mark_revalidation() tags entries matching given categories."""

    def test_tags_service_boundary_entries(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        text = (
            "# Spec\n\n"
            "## Clarifications\n\n"
            "### Session 2025-01-10\n\n"
            "- Q: [service_boundary] Who owns categories? → A: Ledger service\n"
            "- Q: [domain] What is a valid account? → A: Active accounts\n"
        )
        spec_path = _write_spec(tmp_path, text)
        result = recorder.mark_revalidation(spec_path, ("service_boundary",))
        assert result.ok
        content = spec_path.read_text(encoding="utf-8")
        # service_boundary line should be tagged
        lines = content.splitlines()
        boundary_line = next(ln for ln in lines if "[service_boundary]" in ln)
        assert "[NEEDS RE-VALIDATION]" in boundary_line

    def test_tags_communication_entries(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        text = (
            "# Spec\n\n"
            "## Clarifications\n\n"
            "### Session 2025-01-10\n\n"
            "- Q: [communication] Sync or async? → A: Async events\n"
            "- Q: [domain] What is a transaction? → A: Debit or credit\n"
        )
        spec_path = _write_spec(tmp_path, text)
        result = recorder.mark_revalidation(spec_path, ("communication",))
        assert result.ok
        content = spec_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        comm_line = next(ln for ln in lines if "[communication]" in ln)
        assert "[NEEDS RE-VALIDATION]" in comm_line

    def test_preserves_domain_entries(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        text = (
            "# Spec\n\n"
            "## Clarifications\n\n"
            "### Session 2025-01-10\n\n"
            "- Q: [service_boundary] Who owns categories? → A: Ledger service\n"
            "- Q: [domain] What is a valid account? → A: Active accounts\n"
        )
        spec_path = _write_spec(tmp_path, text)
        recorder.mark_revalidation(spec_path, ("service_boundary",))
        content = spec_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        domain_line = next(ln for ln in lines if "[domain]" in ln)
        assert "[NEEDS RE-VALIDATION]" not in domain_line

    def test_returns_ok(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        text = (
            "# Spec\n\n"
            "## Clarifications\n\n"
            "### Session 2025-01-10\n\n"
            "- Q: [domain] What? → A: Something\n"
        )
        spec_path = _write_spec(tmp_path, text)
        result = recorder.mark_revalidation(spec_path, ("service_boundary",))
        assert result.ok

    def test_no_clarifications_section_returns_ok(self, tmp_path: Path) -> None:
        recorder = _make_recorder()
        text = "# Spec\n\n## Overview\n\nJust a spec.\n"
        spec_path = _write_spec(tmp_path, text)
        result = recorder.mark_revalidation(spec_path, ("service_boundary",))
        assert result.ok
