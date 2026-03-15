"""Scaffold plan builder — generates the complete file plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specforge.core.config import SCAFFOLD_DIRS, STACK_HINTS
from specforge.core.project import ProjectConfig, ScaffoldFile, ScaffoldPlan
from specforge.core.result import Ok, Result
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry

# Legacy lists kept for backward compatibility references
PROMPT_FILES = [
    "app-analyzer",
    "feature-specifier",
    "implementation-planner",
    "task-decomposer",
    "code-reviewer",
    "test-writer",
    "debugger",
]

FEATURE_TEMPLATES = [
    "spec-template",
    "plan-template",
    "tasks-template",
    "research-template",
    "data-model-template",
    "quickstart-template",
    "contracts-template",
]


def _build_context(config: ProjectConfig) -> dict[str, Any]:
    """Build the Jinja2 template context from a config."""
    from datetime import date

    return {
        "project_name": config.name,
        "agent": config.agent,
        "stack": config.stack,
        "date": date.today().isoformat(),
        "stack_hint": STACK_HINTS.get(config.stack, "Language-agnostic"),
    }


def _build_files(config: ProjectConfig) -> list[ScaffoldFile]:
    """Build the ordered list of scaffold files from registry."""
    ctx = _build_context(config)
    files: list[ScaffoldFile] = []

    registry = TemplateRegistry()
    registry.discover()

    # Constitution
    files.append(
        ScaffoldFile(
            relative_path=Path(".specforge/constitution.md"),
            template_name="base/constitution.md.j2",
            context=ctx,
        )
    )

    # Memory files
    files.append(
        ScaffoldFile(
            relative_path=Path(".specforge/memory/constitution.md"),
            template_name="base/constitution.md.j2",
            context=ctx,
        )
    )
    files.append(
        ScaffoldFile(
            relative_path=Path(".specforge/memory/decisions.md"),
            template_name="decisions.md.j2",
            context=ctx,
        )
    )

    # Prompt files from registry
    prompts = registry.list(TemplateType.prompt)
    for info in prompts:
        if info.stack is not None:
            continue  # Skip stack variants in scaffold
        files.append(
            ScaffoldFile(
                relative_path=Path(f".specforge/prompts/{info.logical_name}.md"),
                template_name=info.template_path,
                context=ctx,
            )
        )

    # Feature templates from registry
    features = registry.list(TemplateType.feature)
    for info in features:
        files.append(
            ScaffoldFile(
                relative_path=Path(
                    f".specforge/templates/features/{info.logical_name}.md"
                ),
                template_name=info.template_path,
                context=ctx,
            )
        )

    # Gitignore
    if not config.no_git:
        files.append(
            ScaffoldFile(
                relative_path=Path(".gitignore"),
                template_name="gitignore.j2",
                context=ctx,
            )
        )

    return sorted(files, key=lambda f: str(f.relative_path))


def build_scaffold_plan(config: ProjectConfig) -> Result:
    """Build a complete scaffold plan from a ProjectConfig."""
    directories = [Path(d) for d in SCAFFOLD_DIRS]
    files = _build_files(config)
    plan = ScaffoldPlan(config=config, files=files, directories=directories)
    return Ok(plan)
