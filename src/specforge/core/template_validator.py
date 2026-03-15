"""Post-render template validation — stateless utility functions."""

from __future__ import annotations

import re
from typing import Any

from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import (
    TemplateVarSchema,
    ValidationIssue,
    ValidationReport,
)

_PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}")
_DOUBLE_BRACE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_CODE_FENCE_RE = re.compile(r"^```")
_HEADING_RE = re.compile(r"^(#{1,6})\s")


def validate_context(
    context: dict[str, Any],
    schema: TemplateVarSchema,
) -> Result:
    """Pre-render: validate context against a variable schema.

    Returns Ok(enriched_context) with defaults injected, or
    Err(list[str]) with validation error messages.
    """
    errors = schema.validate(context)
    if errors:
        return Err(errors)
    enriched = dict(context)
    for name, (_type, default) in schema.optional.items():
        if name not in enriched:
            enriched[name] = default
    return Ok(enriched)


def validate(content: str, template_name: str = "") -> ValidationReport:
    """Post-render: check rendered content for structural issues."""
    issues: list[ValidationIssue] = []
    lines = content.split("\n")

    _check_placeholders(lines, issues)
    _check_code_blocks(lines, issues)
    _check_heading_hierarchy(lines, issues)

    return ValidationReport(template_name=template_name, issues=issues)


def _check_placeholders(
    lines: list[str],
    issues: list[ValidationIssue],
) -> None:
    """Detect unresolved Jinja2 placeholders outside code fences."""
    in_fence = False
    for line_num, line in enumerate(lines, start=1):
        if _CODE_FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _PLACEHOLDER_RE.finditer(line):
            name_match = _DOUBLE_BRACE_RE.match(match.group())
            placeholder_name = (
                name_match.group(1) if name_match else None
            )
            issues.append(
                ValidationIssue(
                    line=line_num,
                    issue_type="unresolved_placeholder",
                    message=f"Unresolved placeholder: {match.group()}",
                    placeholder_name=placeholder_name,
                )
            )


def _check_code_blocks(
    lines: list[str],
    issues: list[ValidationIssue],
) -> None:
    """Detect unclosed code fences (odd count of ```)."""
    fence_count = 0
    last_fence_line = 0
    for line_num, line in enumerate(lines, start=1):
        if _CODE_FENCE_RE.match(line.strip()):
            fence_count += 1
            last_fence_line = line_num
    if fence_count % 2 != 0:
        issues.append(
            ValidationIssue(
                line=last_fence_line,
                issue_type="unclosed_code_block",
                message="Unclosed code fence (odd number of ``` markers)",
            )
        )


def _check_heading_hierarchy(
    lines: list[str],
    issues: list[ValidationIssue],
) -> None:
    """Detect heading level skips (e.g., H1 → H4)."""
    last_level = 0
    for line_num, line in enumerate(lines, start=1):
        heading = _HEADING_RE.match(line)
        if not heading:
            continue
        level = len(heading.group(1))
        if last_level > 0 and level > last_level + 1:
            issues.append(
                ValidationIssue(
                    line=line_num,
                    issue_type="heading_skip",
                    message=(
                        f"Heading skip: H{last_level} → H{level} "
                        f"(expected H{last_level + 1} or lower)"
                    ),
                )
            )
        last_level = level
