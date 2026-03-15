"""Scaffold file writer — renders templates and writes files to disk."""

from __future__ import annotations

from pathlib import Path

from specforge.core.project import ScaffoldPlan, ScaffoldResult
from specforge.core.result import Err, Ok, Result
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer


def write_scaffold(plan: ScaffoldPlan) -> Result:
    """Write all scaffold files to disk per the plan."""
    target = plan.config.target_dir
    result = ScaffoldResult(plan=plan)

    if plan.config.dry_run:
        return Ok(result)

    try:
        renderer = _create_renderer()
        _create_directories(target, plan)
        _write_files(target, plan, result, renderer)
    except PermissionError as exc:
        path = _extract_path(exc, target)
        return Err(
            f"Permission denied writing to '{path}'. Check directory permissions."
        )
    return Ok(result)


def _create_renderer() -> TemplateRenderer:
    """Create a TemplateRenderer with discovered built-in templates."""
    registry = TemplateRegistry()
    registry.discover()
    return TemplateRenderer(registry)


def _create_directories(target: Path, plan: ScaffoldPlan) -> None:
    """Create all scaffold directories."""
    for directory in plan.directories:
        (target / directory).mkdir(parents=True, exist_ok=True)


def _write_files(
    target: Path,
    plan: ScaffoldPlan,
    result: ScaffoldResult,
    renderer: TemplateRenderer,
) -> None:
    """Render and write each scaffold file."""
    for scaffold_file in plan.files:
        abs_path = target / scaffold_file.relative_path
        if abs_path.exists() and plan.config.force:
            result.skipped.append(abs_path)
            continue
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        render_result = renderer.render_raw(
            scaffold_file.template_name,
            scaffold_file.context,
        )
        if render_result.ok:
            abs_path.write_text(render_result.value, encoding="utf-8")
            result.written.append(abs_path)


def _extract_path(exc: PermissionError, fallback: Path) -> str:
    """Extract the path from a PermissionError or use fallback."""
    if exc.filename:
        return str(exc.filename)
    return str(fallback)
