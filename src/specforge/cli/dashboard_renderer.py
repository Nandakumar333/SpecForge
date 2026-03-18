"""Rich terminal rendering for the project status dashboard."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specforge.core.config import STATUS_DISPLAY_LABELS
from specforge.core.status_models import (
    PhaseProgressRecord,
    ProjectStatusSnapshot,
    QualitySummaryRecord,
)


def render_dashboard(
    console: Console,
    snapshot: ProjectStatusSnapshot,
    *,
    show_graph: bool = False,
) -> None:
    """Render the full status dashboard to the console."""
    render_badge(console, snapshot.architecture)
    render_service_table(console, snapshot)
    if snapshot.phases:
        render_phase_progress(console, snapshot.phases)
    render_quality_summary(console, snapshot.quality, snapshot.architecture)
    if show_graph and snapshot.graph.nodes:
        render_graph(console, snapshot)
    if snapshot.warnings:
        _render_warnings(console, snapshot.warnings)


def render_badge(console: Console, architecture: str) -> None:
    """Render architecture badge."""
    badge_map = {
        "microservice": "MICROSERVICE",
        "monolithic": "MONOLITH",
        "modular-monolith": "MODULAR",
    }
    label = badge_map.get(architecture, architecture.upper())
    console.print(Panel(f"[bold]{label}[/bold]", title="Architecture", expand=False))


def render_service_table(
    console: Console,
    snapshot: ProjectStatusSnapshot,
) -> None:
    """Render the service status table with architecture-adaptive columns."""
    table = Table(title="Service Status")
    table.add_column("Service", style="cyan")
    table.add_column("Features")
    table.add_column("Spec")
    table.add_column("Plan")
    table.add_column("Tasks")
    table.add_column("Impl %")
    table.add_column("Tests")
    if snapshot.architecture == "microservice":
        table.add_column("Docker")
    if snapshot.architecture == "modular-monolith":
        table.add_column("Boundary")
    table.add_column("Status")

    for svc in snapshot.services:
        row = _build_service_row(svc, snapshot.architecture)
        table.add_row(*row)

    console.print(table)


def _build_service_row(svc, architecture: str) -> list[str]:
    """Build a single table row for a service."""
    lc = svc.lifecycle
    row = [
        svc.display_name,
        ", ".join(svc.features) if svc.features else "-",
        lc.spec or "-",
        lc.plan or "-",
        lc.tasks or "-",
        f"{lc.impl_percent}%" if lc.impl_percent is not None else "-",
        f"{lc.tests_passed}/{lc.tests_total}" if lc.tests_total is not None else "-",
    ]
    if architecture == "microservice":
        row.append(lc.docker or "-")
    if architecture == "modular-monolith":
        row.append(lc.boundary_compliance or "-")
    status_display = STATUS_DISPLAY_LABELS.get(svc.overall_status, svc.overall_status)
    style = _status_style(svc.overall_status)
    row.append(f"[{style}]{status_display}[/{style}]")
    return row


def render_phase_progress(
    console: Console,
    phases: tuple[PhaseProgressRecord, ...],
) -> None:
    """Render phase progress bars."""
    console.print("\n[bold]Phase Progress[/bold]")
    for phase in phases:
        pct = phase.completion_percent
        filled = int(pct / 100 * 20)
        bar = "█" * filled + "░" * (20 - filled)
        if phase.status == "blocked":
            note = (
                f" (blocked by Phase {phase.blocked_by})"
                if phase.blocked_by is not None
                else " (blocked)"
            )
            console.print(f"  {phase.label}: [{bar}] {pct:.0f}%[dim]{note}[/dim]")
        else:
            console.print(f"  {phase.label}: [{bar}] {pct:.0f}%")


def render_quality_summary(
    console: Console,
    quality: QualitySummaryRecord,
    architecture: str,
) -> None:
    """Render quality summary panel."""
    lines = _quality_lines(quality, architecture)
    console.print(Panel("\n".join(lines), title="Quality Summary"))


def _quality_lines(quality: QualitySummaryRecord, architecture: str) -> list[str]:
    """Build quality summary text lines."""
    lines = [
        f"Services: {quality.services_total} total, "
        f"{quality.services_complete} complete, "
        f"{quality.services_in_progress} in progress, "
        f"{quality.services_not_started} not started",
        f"Tasks: {quality.tasks_total} total, "
        f"{quality.tasks_complete} complete, "
        f"{quality.tasks_failed} failed",
    ]
    if quality.coverage_avg is not None:
        lines.append(f"Coverage: {quality.coverage_avg:.0f}% average")
    if architecture == "microservice":
        _append_docker_lines(lines, quality)
    if quality.autofix_success_rate is not None:
        lines.append(f"Auto-fix: {quality.autofix_success_rate:.0f}% success rate")
    return lines


def _append_docker_lines(lines: list[str], quality: QualitySummaryRecord) -> None:
    """Append Docker/contract lines for microservice architecture."""
    if quality.docker_built is not None:
        lines.append(
            f"Docker: {quality.docker_built}/{quality.docker_total} built, "
            f"{quality.docker_failing} failing",
        )
    if quality.contract_passed is not None:
        lines.append(
            f"Contracts: {quality.contract_passed}/{quality.contract_total} passing",
        )


def render_graph(console: Console, snapshot: ProjectStatusSnapshot) -> None:
    """Render dependency graph."""
    from specforge.core.graph_builder import render_ascii

    text = render_ascii(snapshot.graph)
    console.print(Panel(text, title="Dependency Graph"))


def _render_warnings(console: Console, warnings: tuple[str, ...]) -> None:
    """Render warnings panel."""
    console.print(Panel(
        "\n".join(f"⚠ {w}" for w in warnings),
        title="Warnings",
        style="yellow",
    ))


def _status_style(status: str) -> str:
    """Map status to Rich style."""
    styles = {
        "COMPLETE": "green",
        "IN_PROGRESS": "yellow",
        "PLANNING": "blue",
        "NOT_STARTED": "dim",
        "BLOCKED": "magenta",
        "FAILED": "red",
        "UNKNOWN": "dim red",
    }
    return styles.get(status, "white")
