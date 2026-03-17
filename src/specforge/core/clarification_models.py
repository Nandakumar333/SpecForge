"""Frozen dataclasses for the Research & Clarification Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AmbiguityCategory = Literal[
    "domain", "technical", "service_boundary", "communication"
]

FindingStatus = Literal["RESOLVED", "UNVERIFIED", "BLOCKED", "CONFLICTING"]


@dataclass(frozen=True)
class AmbiguityPattern:
    """A regex-based rule for detecting ambiguities in spec text."""

    pattern_type: str
    regex: str
    category: AmbiguityCategory
    description: str
    case_sensitive: bool = False


@dataclass(frozen=True)
class AmbiguityMatch:
    """A single ambiguity detected in spec text."""

    text: str
    line_number: int
    category: AmbiguityCategory
    pattern_type: str
    confidence: float


@dataclass(frozen=True)
class SuggestedAnswer:
    """One suggested answer option for a clarification question."""

    label: str
    text: str
    implications: str


@dataclass(frozen=True)
class ClarificationQuestion:
    """A structured question generated from a detected ambiguity."""

    id: str
    category: AmbiguityCategory
    context_excerpt: str
    question_text: str
    suggested_answers: tuple[SuggestedAnswer, ...]
    source_match: AmbiguityMatch
    impact_rank: int


@dataclass(frozen=True)
class ClarificationAnswer:
    """A user's answer to a clarification question."""

    question_id: str
    answer_text: str
    is_custom: bool
    answered_at: str


@dataclass(frozen=True)
class ClarificationSession:
    """Aggregate root for one clarify run."""

    service_slug: str
    questions: tuple[ClarificationQuestion, ...]
    answers: tuple[ClarificationAnswer, ...]
    skipped_ids: tuple[str, ...]
    is_report_mode: bool
    session_date: str


@dataclass(frozen=True)
class ResearchFinding:
    """A single research result with status."""

    topic: str
    summary: str
    source: str
    status: FindingStatus
    originating_marker: str
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchContext:
    """Aggregated context for research generation."""

    architecture: str
    communication_patterns: tuple[str, ...]
    tech_references: tuple[str, ...]
    clarification_markers: tuple[str, ...]
    adapter_extras: tuple[dict[str, str], ...]
