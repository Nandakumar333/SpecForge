"""Frozen dataclasses for edge case analysis (Feature 007)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EdgeCaseCategory = Literal[
    "concurrency",
    "data_boundary",
    "state_machine",
    "ui_ux",
    "security",
    "data_migration",
    "service_unavailability",
    "network_partition",
    "eventual_consistency",
    "distributed_transaction",
    "version_skew",
    "data_ownership",
    "interface_contract_violation",
]

Severity = Literal["critical", "high", "medium", "low"]


@dataclass(frozen=True)
class EdgeCase:
    """A single generated edge case with full metadata."""

    id: str
    category: str
    severity: str
    scenario: str
    trigger: str
    affected_services: tuple[str, ...]
    handling_strategy: str
    test_suggestion: str


@dataclass(frozen=True)
class EdgeCasePattern:
    """A scenario template loaded from a YAML pattern file."""

    category: str
    scenario_template: str
    trigger_template: str
    handling_strategies: tuple[str, ...]
    severity_microservice: str | None
    severity_monolith: str | None
    test_template: str
    applicable_patterns: tuple[str, ...]


@dataclass(frozen=True)
class EdgeCaseReport:
    """Aggregate of all edge cases generated for a service."""

    service_slug: str
    architecture: str
    edge_cases: tuple[EdgeCase, ...]
    total_count: int


def make_edge_case_id(n: int) -> str:
    """Return EC-NNN formatted id for sequential numbering."""
    return f"EC-{n:03d}"
