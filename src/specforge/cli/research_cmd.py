"""CLI command: specforge research <target>."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console

from specforge.core.architecture_adapter import create_adapter
from specforge.core.clarification_models import ResearchFinding
from specforge.core.config import (
    MANIFEST_PATH,
    PIPELINE_LOCK_FILENAME,
    PIPELINE_STATE_FILENAME,
)
from specforge.core.pipeline_lock import acquire_lock, release_lock
from specforge.core.pipeline_state import (
    create_initial_state,
    load_state,
    mark_complete,
    save_state,
)
from specforge.core.research_resolver import ResearchResolver
from specforge.core.service_context import load_service_context, resolve_target
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer


@click.command("research")
@click.argument("target")
def research(target: str) -> None:
    """Generate research findings for a service's technical unknowns."""
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
        _run_research(project_root, service_ctx, spec_path, console)
    finally:
        release_lock(lock_path)


def _run_research(
    project_root: Path,
    service_ctx: object,
    spec_path: Path,
    console: Console,
) -> None:
    """Core research logic after lock acquisition."""
    console.print(
        f"[bold]Researching technical unknowns for "
        f"{service_ctx.service_slug}...[/bold]"
    )

    spec_text = spec_path.read_text(encoding="utf-8")
    plan_path = service_ctx.output_dir / "plan.md"
    plan_text = None
    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        console.print("Scanning plan.md... found unknowns")

    # Create adapter and resolver
    adapter = create_adapter(service_ctx.architecture)
    resolver = ResearchResolver(adapter)
    findings = resolver.resolve(spec_text, plan_text, service_ctx)

    # Merge with existing research.md if present
    research_path = service_ctx.output_dir / "research.md"
    if research_path.exists():
        existing = _parse_existing_findings(research_path)
        if existing:
            findings = resolver.merge_findings(existing, findings)
            console.print(
                f"Merging with existing research.md "
                f"({sum(1 for f in existing if f.status == 'RESOLVED')} "
                f"RESOLVED preserved)"
            )

    # Render template
    _render_research(project_root, service_ctx, findings, console)

    # Update pipeline state
    _update_pipeline_state(service_ctx, research_path)

    # Summary
    status_counts = _count_statuses(findings)
    console.print(f"\n[green]Research complete:[/green] {len(findings)} findings")
    for status, count in sorted(status_counts.items()):
        console.print(f"  {status}: {count}")
    console.print(f"\nWritten to: {research_path}")


def _render_research(
    project_root: Path,
    service_ctx: object,
    findings: tuple[ResearchFinding, ...],
    console: Console,
) -> None:
    """Render research.md via the template engine."""
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
        "adapter_research_extras": [
            {"topic": f.topic, "description": f.summary}
            for f in findings
        ],
        "findings": [
            {
                "topic": f.topic,
                "summary": f.summary,
                "source": f.source,
                "status": f.status,
                "originating_marker": f.originating_marker,
                "alternatives": list(f.alternatives),
            }
            for f in findings
        ],
        "prompt_context": prompt_context,
    }

    result = renderer.render("research", TemplateType.feature, context)
    if not result.ok:
        console.print(f"[red]Template error:[/red] {result.error}")
        raise SystemExit(1)

    out_path = service_ctx.output_dir / "research.md"
    out_path.write_text(result.value, encoding="utf-8")


def _update_pipeline_state(
    service_ctx: object, research_path: Path,
) -> None:
    """Mark the research phase as complete in pipeline state."""
    state_path = service_ctx.output_dir / PIPELINE_STATE_FILENAME
    state_result = load_state(state_path)
    if state_result.ok and state_result.value is not None:
        state = mark_complete(
            state_result.value, "research",
            artifact_paths=(str(research_path),),
        )
        save_state(state_path, state)
    elif state_result.ok and state_result.value is None:
        state = create_initial_state(service_ctx.service_slug)
        state = mark_complete(
            state, "research",
            artifact_paths=(str(research_path),),
        )
        save_state(state_path, state)


def _parse_existing_findings(
    path: Path,
) -> tuple[ResearchFinding, ...]:
    """Parse existing research.md for findings (best-effort)."""
    # Simple heuristic parser for the R-NNN format
    findings: list[ResearchFinding] = []
    with contextlib.suppress(OSError):
        content = path.read_text(encoding="utf-8")
        import re

        blocks = re.split(r"^###\s+R-\d+:\s*", content, flags=re.MULTILINE)
        for block in blocks[1:]:
            lines = block.strip().splitlines()
            topic = lines[0].strip() if lines else ""
            status = "UNVERIFIED"
            source = "spec-reference"
            for line in lines:
                if line.startswith("**Status**:"):
                    status = line.split(":", 1)[1].strip()
                if line.startswith("**Source**:"):
                    source = line.split(":", 1)[1].strip()
            findings.append(ResearchFinding(
                topic=topic,
                summary=" ".join(lines[1:5]),
                source=source,
                status=status,
                originating_marker="existing research.md",
            ))
    return tuple(findings)


def _count_statuses(
    findings: tuple[ResearchFinding, ...],
) -> dict[str, int]:
    """Count findings by status."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    return counts


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
