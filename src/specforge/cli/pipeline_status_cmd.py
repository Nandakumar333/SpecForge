"""CLI command: specforge pipeline-status [target]."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from specforge.core.config import FEATURES_DIR
from specforge.core.pipeline_state import load_state


@click.command("pipeline-status")
@click.argument("target", required=False)
@click.pass_context
def pipeline_status(ctx: click.Context, target: str | None) -> None:
    """Show pipeline phase status for services."""
    console = Console()
    project_root = Path.cwd()
    features_dir = project_root / FEATURES_DIR

    if not features_dir.is_dir():
        console.print("[yellow]No pipeline state found.[/yellow]")
        return

    if target:
        _show_service(console, features_dir, target)
    else:
        _show_all(console, features_dir)


def _show_service(
    console: Console, features_dir: Path, slug: str
) -> None:
    """Show status for a specific service."""
    state_path = features_dir / slug / ".pipeline-state.json"
    result = load_state(state_path)
    if not result.ok or result.value is None:
        console.print(f"[yellow]No state for '{slug}'[/yellow]")
        return
    _render_table(console, result.value)


def _show_all(console: Console, features_dir: Path) -> None:
    """Show status for all services."""
    found = False
    for svc_dir in sorted(features_dir.iterdir()):
        if not svc_dir.is_dir():
            continue
        state_path = svc_dir / ".pipeline-state.json"
        result = load_state(state_path)
        if result.ok and result.value is not None:
            found = True
            _render_table(console, result.value)
    if not found:
        console.print("[yellow]No pipeline state found.[/yellow]")


def _render_table(console: Console, state: object) -> None:
    """Render a Rich table for a pipeline state."""
    table = Table(title=f"Pipeline: {state.service_slug}")
    table.add_column("Phase", style="cyan")
    table.add_column("Status")
    table.add_column("Artifacts")
    for ps in state.phases:
        style = _status_style(ps.status)
        artifacts = ", ".join(ps.artifact_paths) if ps.artifact_paths else "-"
        table.add_row(ps.name, f"[{style}]{ps.status}[/{style}]", artifacts)
    console.print(table)


def _status_style(status: str) -> str:
    """Map status to Rich style."""
    styles = {
        "complete": "green",
        "in-progress": "yellow",
        "failed": "red",
        "pending": "dim",
    }
    return styles.get(status, "white")
