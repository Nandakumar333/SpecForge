"""CLI command: specforge edge-cases <target>."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console

from specforge.core.config import (
    MANIFEST_PATH,
    PIPELINE_LOCK_FILENAME,
    PIPELINE_STATE_FILENAME,
)
from specforge.core.edge_case_analyzer import EdgeCaseAnalyzer
from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_models import EdgeCaseReport
from specforge.core.edge_case_patterns import PatternLoader
from specforge.core.pipeline_lock import acquire_lock, release_lock
from specforge.core.pipeline_state import (
    create_initial_state,
    load_state,
    mark_complete,
    save_state,
)
from specforge.core.service_context import (
    ServiceContext,
    load_service_context,
    resolve_target,
)
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer


@click.command("edge-cases")
@click.argument("target")
def edge_cases(target: str) -> None:
    """Generate edge case analysis for a service."""
    console = Console()
    project_root = Path.cwd()

    # Resolve target
    slug_result = resolve_target(target, project_root)
    if not slug_result.ok:
        console.print(f"[red]Error:[/red] {slug_result.error}")
        raise SystemExit(1)

    ctx_result = load_service_context(slug_result.value, project_root)
    if not ctx_result.ok:
        console.print(f"[red]Error:[/red] {ctx_result.error}")
        raise SystemExit(1)

    service_ctx = ctx_result.value
    spec_path = service_ctx.output_dir / "spec.md"
    if not spec_path.exists():
        console.print(f"[red]Error:[/red] spec.md not found at {spec_path}")
        raise SystemExit(1)

    # Acquire lock
    lock_path = project_root / MANIFEST_PATH.rsplit("/", 1)[0] / PIPELINE_LOCK_FILENAME
    lock_result = acquire_lock(lock_path, service_ctx.service_slug)
    if not lock_result.ok:
        console.print(f"[red]Error:[/red] {lock_result.error}")
        raise SystemExit(1)

    try:
        _run_edge_cases(project_root, service_ctx, console)
    finally:
        release_lock(lock_path)


def _run_edge_cases(
    project_root: Path,
    service_ctx: ServiceContext,
    console: Console,
) -> None:
    """Core edge case analysis logic after lock acquisition."""
    console.print(
        f"[bold]Analyzing edge cases for "
        f"{service_ctx.service_slug}...[/bold]"
    )

    report = _analyze(service_ctx, project_root, console)
    _render_edge_cases(project_root, service_ctx, report, console)

    out_path = service_ctx.output_dir / "edge-cases.md"
    _update_pipeline_state(service_ctx, out_path)
    _print_summary(report, out_path, console)


def _analyze(
    service_ctx: ServiceContext,
    project_root: Path,
    console: Console,
) -> EdgeCaseReport:
    """Load patterns, build analyzer, and run analysis."""
    loader = PatternLoader()
    patterns_result = loader.load_patterns()
    if not patterns_result.ok:
        console.print(f"[red]Error:[/red] {patterns_result.error}")
        raise SystemExit(1)

    arch_filter = ArchitectureEdgeCaseFilter(service_ctx.architecture)
    budget = EdgeCaseBudget()
    analyzer = EdgeCaseAnalyzer(patterns_result.value, arch_filter, budget)

    manifest = _load_manifest_data(project_root)
    result = analyzer.analyze(service_ctx, manifest)
    if not result.ok:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    return result.value


def _load_manifest_data(project_root: Path) -> dict | None:
    """Load manifest.json as raw dict for boundary analysis."""
    manifest_path = project_root / MANIFEST_PATH
    if not manifest_path.exists():
        return None
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None


def _render_edge_cases(
    project_root: Path,
    service_ctx: ServiceContext,
    report: EdgeCaseReport,
    console: Console,
) -> None:
    """Render edge-cases.md via the template engine."""
    registry = TemplateRegistry(project_root)
    registry.discover()
    renderer = TemplateRenderer(registry)

    prompt_context = _load_prompt_context(project_root)

    context = {
        "project_name": service_ctx.project_description,
        "date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "feature_name": service_ctx.service_slug,
        "service": {
            "slug": service_ctx.service_slug,
            "name": service_ctx.service_name,
        },
        "architecture": service_ctx.architecture,
        "features": [
            {
                "display_name": f.display_name,
                "description": f.description,
            }
            for f in service_ctx.features
        ],
        "edge_cases": [
            {
                "id": ec.id,
                "category": ec.category,
                "severity": ec.severity,
                "scenario": ec.scenario,
                "trigger": ec.trigger,
                "affected_services": list(ec.affected_services),
                "handling_strategy": ec.handling_strategy,
                "test_suggestion": ec.test_suggestion,
            }
            for ec in report.edge_cases
        ],
        "prompt_context": prompt_context,
    }

    result = renderer.render("edge-cases", TemplateType.feature, context)
    if not result.ok:
        console.print(f"[red]Template error:[/red] {result.error}")
        raise SystemExit(1)

    out_path = service_ctx.output_dir / "edge-cases.md"
    out_path.write_text(result.value, encoding="utf-8")


def _update_pipeline_state(
    service_ctx: ServiceContext, edge_cases_path: Path,
) -> None:
    """Mark the edgecase phase as complete in pipeline state."""
    state_path = service_ctx.output_dir / PIPELINE_STATE_FILENAME
    state_result = load_state(state_path)
    if state_result.ok and state_result.value is not None:
        state = mark_complete(
            state_result.value, "edgecase",
            artifact_paths=(str(edge_cases_path),),
        )
        save_state(state_path, state)
    elif state_result.ok and state_result.value is None:
        state = create_initial_state(service_ctx.service_slug)
        state = mark_complete(
            state, "edgecase",
            artifact_paths=(str(edge_cases_path),),
        )
        save_state(state_path, state)


def _print_summary(
    report: EdgeCaseReport,
    out_path: Path,
    console: Console,
) -> None:
    """Print analysis summary with count and severity breakdown."""
    severity_counts: dict[str, int] = {}
    for ec in report.edge_cases:
        severity_counts[ec.severity] = severity_counts.get(ec.severity, 0) + 1

    console.print(
        f"\n[green]Edge case analysis complete:[/green] "
        f"{report.total_count} cases"
    )
    for severity, count in sorted(severity_counts.items()):
        console.print(f"  {severity}: {count}")
    console.print(f"\nWritten to: {out_path}")


def _load_prompt_context(project_root: Path) -> str:
    """Load governance prompt context if available."""
    try:
        from specforge.core.prompt_context import PromptContextBuilder
        from specforge.core.prompt_loader import PromptLoader

        loader = PromptLoader(project_root)
        load_result = loader.load()
        if load_result.ok and load_result.value is not None:
            return PromptContextBuilder.build(load_result.value)
    except (ImportError, Exception):
        pass
    return ""
