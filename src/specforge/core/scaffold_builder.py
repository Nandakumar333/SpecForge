"""Scaffold plan builder — generates the complete file plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specforge.core.config import SCAFFOLD_DIRS, STACK_HINTS
from specforge.core.project import ProjectConfig, ScaffoldFile, ScaffoldPlan
from specforge.core.prompt_manager import PromptFileManager
from specforge.core.result import Err, Ok, Result
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


def generate_governance_files(config: ProjectConfig) -> Result:
    """Generate governance prompt files for a project.

    Called AFTER write_scaffold to ensure target directory exists first.
    Handles --force by skipping customized files.
    """
    if config.dry_run:
        return Ok([])

    registry = TemplateRegistry()
    registry.discover()
    mgr = PromptFileManager(project_root=config.target_dir, registry=registry)

    if config.force:
        return _generate_governance_with_force(mgr, config)
    return mgr.generate(project_name=config.name, stack=config.stack)


def _generate_governance_with_force(
    mgr: PromptFileManager,
    config: ProjectConfig,
) -> Result:
    """Generate governance files for --force, skipping customized files."""
    from specforge.core.config import GOVERNANCE_DOMAINS

    paths: list[Path] = []
    for domain in GOVERNANCE_DOMAINS:
        file_path = mgr.resolve_path(domain, config.stack)
        if file_path.exists():
            custom_result = mgr.is_customized(file_path, config.stack)
            if custom_result.ok and custom_result.value:
                # File is customized — skip regeneration
                paths.append(file_path)
                continue
        # Not customized or doesn't exist — regenerate
        result = mgr.generate_one(domain, config.name, config.stack)
        if not result.ok:
            return Err(result.error)
        paths.append(result.value)

    # Always update config.json
    from specforge.core.prompt_manager import _write_config_json
    config_result = _write_config_json(config.target_dir, config.name, config.stack)
    if not config_result.ok:
        return Err(config_result.error)

    return Ok(paths)


def build_scaffold_plan(config: ProjectConfig) -> Result:
    """Build a complete scaffold plan from a ProjectConfig."""
    directories = [Path(d) for d in SCAFFOLD_DIRS]
    files = _build_files(config)

    plan = ScaffoldPlan(config=config, files=files, directories=directories)
    return Ok(plan)
