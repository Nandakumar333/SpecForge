"""Domain entities for governance prompt files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptThreshold:
    key: str
    value: str


@dataclass(frozen=True)
class PromptRule:
    rule_id: str
    title: str
    severity: str  # "ERROR" | "WARNING"
    scope: str
    description: str
    thresholds: tuple[PromptThreshold, ...]
    example_correct: str
    example_incorrect: str


@dataclass(frozen=True)
class PromptFileMeta:
    domain: str
    stack: str
    version: str
    precedence: int
    checksum: str


@dataclass(frozen=True)
class PromptFile:
    path: Path
    meta: PromptFileMeta
    rules: tuple[PromptRule, ...]
    raw_content: str


@dataclass(frozen=True)
class PromptSet:
    files: dict[str, PromptFile]
    precedence: list[str]
    feature_id: str


@dataclass(frozen=True)
class ConflictEntry:
    threshold_key: str
    rule_id_a: str
    domain_a: str
    value_a: str
    rule_id_b: str
    domain_b: str
    value_b: str
    winning_domain: str
    winning_value: str
    is_ambiguous: bool
    suggested_resolution: str


@dataclass(frozen=True)
class ConflictReport:
    conflicts: tuple[ConflictEntry, ...]
    has_conflicts: bool


@dataclass(frozen=True)
class ProjectMeta:
    project_name: str
    stack: str
    version: str
    created_at: str
