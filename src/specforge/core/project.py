"""Core domain dataclasses for SpecForge scaffold operations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from specforge.core.config import PROJECT_NAME_PATTERN
from specforge.core.result import Err, Ok, Result


@dataclass(frozen=True)
class ProjectConfig:
    """Validated project configuration for scaffold operations."""

    name: str
    target_dir: Path
    agent: str = "agnostic"
    stack: str = "agnostic"
    architecture: str = "monolithic"
    no_git: bool = False
    force: bool = False
    dry_run: bool = False
    here: bool = False

    @staticmethod
    def create(
        name: str,
        target_dir: Path,
        agent: str = "agnostic",
        stack: str = "agnostic",
        architecture: str = "monolithic",
        no_git: bool = False,
        force: bool = False,
        dry_run: bool = False,
        here: bool = False,
    ) -> Result:
        """Validate and create a ProjectConfig."""
        if here and name:
            return Err(
                "Cannot specify both NAME and --here. "
                "Use --here to scaffold into the current directory."
            )
        if here:
            derived_name = target_dir.name
            return Ok(
                ProjectConfig(
                    name=derived_name,
                    target_dir=target_dir,
                    agent=agent,
                    stack=stack,
                    architecture=architecture,
                    no_git=no_git,
                    force=force,
                    dry_run=dry_run,
                    here=True,
                )
            )
        if not name:
            return Err("Project name is required.")
        if not re.match(PROJECT_NAME_PATTERN, name):
            return Err(
                f"Invalid project name '{name}'. "
                "Only alphanumeric characters, hyphens, "
                "and underscores are allowed."
            )
        return Ok(
            ProjectConfig(
                name=name,
                target_dir=target_dir,
                agent=agent,
                stack=stack,
                architecture=architecture,
                no_git=no_git,
                force=force,
                dry_run=dry_run,
                here=here,
            )
        )


@dataclass(frozen=True)
class ScaffoldFile:
    """A single file to be rendered and written during scaffold."""

    relative_path: Path
    template_name: str
    context: dict[str, Any]


@dataclass(frozen=True)
class ScaffoldPlan:
    """Complete plan for scaffolding a project directory."""

    config: ProjectConfig
    files: list[ScaffoldFile]
    directories: list[Path]


@dataclass
class ScaffoldResult:
    """Outcome of a scaffold write operation."""

    plan: ScaffoldPlan
    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    git_committed: bool = False
    agent_source: Literal["explicit", "auto-detected", "agnostic"] = "agnostic"


@dataclass(frozen=True)
class DetectionResult:
    """Result of agent auto-detection from PATH."""

    agent: str
    source: Literal["explicit", "auto-detected", "agnostic"]
    executable: str | None = None


@dataclass(frozen=True)
class CheckResult:
    """Result of a single prerequisite check."""

    tool: str
    found: bool
    version: str | None = None
    install_hint: str = ""
