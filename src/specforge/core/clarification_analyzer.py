"""AmbiguityScanner — pattern-based ambiguity detection for spec text."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specforge.core.clarification_models import AmbiguityMatch, AmbiguityPattern
from specforge.core.config import VAGUE_TERM_PATTERNS

if TYPE_CHECKING:
    from specforge.core.clarification_models import AmbiguityCategory

# Lines starting with these prefixes are structural and should be skipped.
_SKIP_PREFIXES = ("#", "```", "<!--", "| ", "---")


def default_patterns() -> tuple[AmbiguityPattern, ...]:
    """Factory producing the default ambiguity-detection patterns."""
    vague = AmbiguityPattern(
        pattern_type="vague_term",
        regex="|".join(VAGUE_TERM_PATTERNS),
        category="domain",
        description="Detects vague or imprecise terms",
    )
    undefined = AmbiguityPattern(
        pattern_type="undefined_concept",
        regex=r'(?<=\s)[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}(?=\s|[,;.\)]|$)'
        r'|"[^"]{3,}"',
        category="domain",
        description="Detects capitalized multi-word terms "
        "or quoted terms that may lack definition",
        case_sensitive=True,
    )
    missing_boundary = AmbiguityPattern(
        pattern_type="missing_boundary",
        regex=r"\beither\s+\w+\s+or\s+\w+"
        r"|\bor\b(?=\s+\w+\s+(?:should|could|might|can|may))"
        r"|[^#]\?$",
        category="technical",
        description="Detects unresolved choices and "
        "open questions in non-heading lines",
    )
    unspecified = AmbiguityPattern(
        pattern_type="unspecified_choice",
        regex=r"\bTBD\b"
        r"|\bto be determined\b"
        r"|\bnot yet decided\b"
        r"|\bTBC\b"
        r"|\bto be confirmed\b",
        category="technical",
        description="Detects explicit markers of unresolved decisions",
    )
    return (vague, undefined, missing_boundary, unspecified)


def _should_skip_line(line: str) -> bool:
    """Return True for headings, code fences, tables, and comments."""
    stripped = line.lstrip()
    return any(stripped.startswith(p) for p in _SKIP_PREFIXES)


class AmbiguityScanner:
    """Scans spec text for ambiguity patterns."""

    def __init__(self, patterns: tuple[AmbiguityPattern, ...]) -> None:
        self._patterns = patterns
        self._compiled: list[tuple[AmbiguityPattern, re.Pattern[str]]] = [
            (
                p,
                re.compile(p.regex)
                if p.case_sensitive
                else re.compile(p.regex, re.IGNORECASE),
            )
            for p in patterns
        ]

    def scan(self, spec_text: str) -> tuple[AmbiguityMatch, ...]:
        """Scan spec text and return matches sorted by line number."""
        if not spec_text.strip():
            return ()
        lines = spec_text.splitlines()
        matches: list[AmbiguityMatch] = []
        for line_num, line in enumerate(lines, start=1):
            if _should_skip_line(line):
                continue
            self._scan_line(line, line_num, matches)
        matches.sort(key=lambda m: m.line_number)
        return tuple(matches)

    def scan_for_category(
        self, spec_text: str, category: AmbiguityCategory,
    ) -> tuple[AmbiguityMatch, ...]:
        """Return only matches for the given category."""
        return tuple(
            m for m in self.scan(spec_text) if m.category == category
        )

    def _scan_line(
        self,
        line: str,
        line_num: int,
        matches: list[AmbiguityMatch],
    ) -> None:
        """Apply all compiled patterns to a single line."""
        for pattern, compiled in self._compiled:
            for m in compiled.finditer(line):
                confidence = 1.0 if pattern.pattern_type in (
                    "vague_term", "unspecified_choice",
                ) else 0.7
                matches.append(AmbiguityMatch(
                    text=m.group().strip(),
                    line_number=line_num,
                    category=pattern.category,
                    pattern_type=pattern.pattern_type,
                    confidence=confidence,
                ))
