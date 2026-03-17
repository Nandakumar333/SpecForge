"""Task generation data models — frozen dataclasses for Feature 008."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EffortSize = Literal["S", "M", "L", "XL"]


@dataclass(frozen=True)
class BuildStep:
    """A single step in an architecture-specific build sequence."""

    order: int
    category: str
    description_template: str
    default_effort: EffortSize
    file_path_pattern: str
    depends_on: tuple[int, ...]
    parallelizable_with: tuple[int, ...]


@dataclass(frozen=True)
class TaskItem:
    """A single actionable work item in a generated task file."""

    id: str
    description: str
    phase: int
    layer: str
    dependencies: tuple[str, ...]
    parallel: bool
    effort: EffortSize
    user_story: str
    file_paths: tuple[str, ...]
    service_scope: str
    governance_rules: tuple[str, ...]
    commit_message: str


@dataclass(frozen=True)
class TaskFile:
    """A collection of ordered tasks for a single target."""

    target_name: str
    architecture: str
    tasks: tuple[TaskItem, ...]
    phases: tuple[tuple[int, tuple[TaskItem, ...]], ...]
    total_count: int


@dataclass
class DependencyGraph:
    """Internal DAG representation — mutable during construction."""

    adjacency: dict[str, tuple[str, ...]] = field(default_factory=dict)
    in_degree: dict[str, int] = field(default_factory=dict)
    tasks_by_id: dict[str, TaskItem] = field(default_factory=dict)
    depth_levels: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationSummary:
    """Result of full-project task generation."""

    generated_files: tuple[str, ...]
    task_counts: dict[str, int]
    cross_dependencies: tuple[str, ...]
    warnings: tuple[str, ...]
