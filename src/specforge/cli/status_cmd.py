"""CLI command: specforge status."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from specforge.core.config import WATCH_DEFAULT_INTERVAL


@click.command("status")
@click.option(
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(["terminal", "markdown", "json"]),
    default=["terminal"],
    help="Output format(s).",
)
@click.option("--graph", is_flag=True, hidden=True, help="Show dependency graph.")
@click.option("--watch", is_flag=True, hidden=True, help="Auto-refresh terminal dashboard.")
@click.option(
    "--interval",
    type=int,
    default=WATCH_DEFAULT_INTERVAL,
    hidden=True,
    help="Watch refresh interval in seconds.",
)
@click.pass_context
def status(
    ctx: click.Context,
    formats: tuple[str, ...],
    graph: bool,
    watch: bool,
    interval: int,
) -> None:
    """Show project-wide status dashboard."""
    console = Console(width=max(Console().width, 120))
    project_root = Path.cwd()

    if watch and set(formats) - {"terminal"}:
        console.print("[red]Error: --watch only works with terminal format[/red]")
        sys.exit(1)

    from specforge.core.status_collector import collect_project_status

    result = collect_project_status(project_root)
    if not result.ok:
        console.print(f"[red]Error: {result.error}[/red]")
        sys.exit(1)

    snapshot = result.value

    if watch:
        _run_watch(console, project_root, snapshot, graph, interval)
        return

    _emit_formats(console, project_root, snapshot, formats, graph)

    if snapshot.has_failures:
        sys.exit(1)


def _emit_formats(
    console: Console,
    project_root: Path,
    snapshot,
    formats: tuple[str, ...],
    graph: bool,
) -> None:
    """Render all requested output formats."""
    if "terminal" in formats:
        from specforge.cli.dashboard_renderer import render_dashboard

        render_dashboard(console, snapshot, show_graph=graph)

    if "json" in formats:
        from specforge.core.report_generator import generate_json_report

        reports_dir = project_root / ".specforge" / "reports"
        json_result = generate_json_report(snapshot, reports_dir)
        if json_result.ok:
            console.print(f"[green]JSON report: {json_result.value}[/green]")

    if "markdown" in formats:
        from specforge.core.report_generator import generate_markdown_report

        reports_dir = project_root / ".specforge" / "reports"
        md_result = generate_markdown_report(snapshot, reports_dir)
        if md_result.ok:
            console.print(f"[green]Markdown report: {md_result.value}[/green]")


def _run_watch(console, project_root, snapshot, graph, interval):
    """Watch mode loop: collect → render → sleep → repeat."""
    import time

    from specforge.cli.dashboard_renderer import render_dashboard
    from specforge.core.status_collector import collect_project_status

    try:
        while True:
            console.clear()
            render_dashboard(console, snapshot, show_graph=graph)
            time.sleep(interval)
            result = collect_project_status(project_root)
            if result.ok:
                snapshot = result.value
            terminal = all(
                s.overall_status in ("COMPLETE", "FAILED")
                for s in snapshot.services
            )
            if terminal:
                render_dashboard(console, snapshot, show_graph=graph)
                break
    except KeyboardInterrupt:
        console.print("\n[dim]Watch stopped.[/dim]")
