"""ClarificationRecorder — appends Q&A to spec.md atomically."""

from __future__ import annotations

import contextlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import (
    CLARIFICATION_SECTION_HEADING,
    SESSION_HEADING_PREFIX,
)
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.clarification_models import (
        AmbiguityCategory,
        ClarificationAnswer,
        ClarificationQuestion,
    )


class ClarificationRecorder:
    """Records clarification answers into spec.md."""

    def record(
        self,
        spec_path: Path,
        answers: tuple[ClarificationAnswer, ...],
        questions: tuple[ClarificationQuestion, ...],
    ) -> Result:
        """Append answered Q&A to the Clarifications section of spec.md."""
        if not spec_path.exists():
            return Err(f"Spec file not found: {spec_path}")
        if not answers:
            return Ok(spec_path)
        content = spec_path.read_text(encoding="utf-8")
        q_map = {q.id: q for q in questions}
        session_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        lines = _build_qa_lines(answers, q_map)
        updated = _insert_clarifications(content, session_date, lines)
        return _atomic_write_text(spec_path, updated)

    def mark_revalidation(
        self,
        spec_path: Path,
        categories: tuple[AmbiguityCategory, ...],
    ) -> Result:
        """Tag architecture-related entries with [NEEDS RE-VALIDATION]."""
        if not spec_path.exists():
            return Err(f"Spec file not found: {spec_path}")
        content = spec_path.read_text(encoding="utf-8")
        if CLARIFICATION_SECTION_HEADING not in content:
            return Ok(spec_path)
        updated = _tag_revalidation(content, categories)
        if updated == content:
            return Ok(spec_path)
        return _atomic_write_text(spec_path, updated)


def _build_qa_lines(
    answers: tuple[ClarificationAnswer, ...],
    q_map: dict[str, ClarificationQuestion],
) -> list[str]:
    """Format Q&A bullets with category tags."""
    lines: list[str] = []
    for ans in answers:
        q = q_map.get(ans.question_id)
        if q is None:
            continue
        lines.append(
            f"- Q: [{q.category}] {q.question_text} "
            f"→ A: {ans.answer_text}"
        )
    return lines


def _insert_clarifications(
    content: str,
    session_date: str,
    qa_lines: list[str],
) -> str:
    """Insert Q&A lines into the Clarifications section."""
    section_heading = CLARIFICATION_SECTION_HEADING
    session_heading = f"{SESSION_HEADING_PREFIX} {session_date}"
    qa_block = "\n".join(qa_lines)

    if section_heading in content:
        return _append_to_existing(
            content, section_heading, session_heading, qa_block,
        )
    return _create_new_section(
        content, section_heading, session_heading, qa_block,
    )


def _append_to_existing(
    content: str,
    section_heading: str,
    session_heading: str,
    qa_block: str,
) -> str:
    """Append a new session or extend existing session."""
    if session_heading in content:
        idx = content.index(session_heading)
        insert_at = content.index("\n", idx) + 1
        next_heading = content.find("\n#", insert_at)
        if next_heading == -1:
            next_heading = len(content)
        # Find last non-empty line before next heading
        return (
            content[:next_heading].rstrip()
            + "\n"
            + qa_block
            + "\n"
            + content[next_heading:]
        )
    # Append new session after the section heading
    idx = content.index(section_heading)
    next_h2 = content.find("\n## ", idx + len(section_heading))
    if next_h2 == -1:
        next_h2 = len(content)
    return (
        content[:next_h2].rstrip()
        + "\n\n"
        + session_heading
        + "\n\n"
        + qa_block
        + "\n"
        + content[next_h2:]
    )


def _create_new_section(
    content: str,
    section_heading: str,
    session_heading: str,
    qa_block: str,
) -> str:
    """Create the Clarifications section before ## Assumptions."""
    insert_marker = "## Assumptions"
    if insert_marker in content:
        idx = content.index(insert_marker)
        return (
            content[:idx].rstrip()
            + "\n\n"
            + section_heading
            + "\n\n"
            + session_heading
            + "\n\n"
            + qa_block
            + "\n\n"
            + content[idx:]
        )
    # Fallback: append at end
    return (
        content.rstrip()
        + "\n\n"
        + section_heading
        + "\n\n"
        + session_heading
        + "\n\n"
        + qa_block
        + "\n"
    )


def _tag_revalidation(
    content: str,
    categories: tuple[AmbiguityCategory, ...],
) -> str:
    """Add [NEEDS RE-VALIDATION] to matching Q&A entries."""
    lines = content.splitlines()
    result: list[str] = []
    tag = "[NEEDS RE-VALIDATION]"
    for line in lines:
        if line.startswith("- Q: [") and tag not in line:
            for cat in categories:
                if f"[{cat}]" in line:
                    line = line + f" {tag}"
                    break
        result.append(line)
    return "\n".join(result)


def _atomic_write_text(path: Path, content: str) -> Result:
    """Write text atomically via temp file + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8")
    fd: int | None = None
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)
        os.write(fd, encoded)
        os.fsync(fd)
        os.close(fd)
        fd = None
        tmp_path.replace(path)
        tmp_path = None
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write '{path}': {exc}")
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
