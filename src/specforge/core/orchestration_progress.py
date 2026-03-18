"""Rich-based progress display for orchestration (Feature 011)."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from specforge.core.orchestrator_models import (
    IntegrationReport,
    OrchestrationPlan,
    OrchestrationState,
    PhaseState,
    VerificationResult,
)

_STATUS_ICONS: dict[str, str] = {
    "completed": "✅",
    "in-progress": "⏳",
    "pending": "⏸",
    "failed": "❌",
    "partial": "⚠️",
    "skipped": "⏭",
}


def render_phase_map(
    plan: OrchestrationPlan,
    state: OrchestrationState,
) -> Tree:
    """Render orchestration plan as a Rich Tree with status indicators."""
    tree = Tree(f"🔧 Implementation ({plan.architecture})")
    state_map = {ps.index: ps for ps in state.phases}
    for phase in plan.phases:
        ps = state_map.get(phase.index)
        status = ps.status if ps else "pending"
        icon = _STATUS_ICONS.get(status, "?")
        tree.add(
            f"{icon} Phase {phase.index}: "
            f"{', '.join(phase.services)}"
        )
    return tree


def render_service_table(phase_state: PhaseState) -> Table:
    """Render per-service status table for a phase."""
    table = Table(title=f"Phase {phase_state.index}")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Tasks", justify="right")
    for svc in phase_state.services:
        icon = _STATUS_ICONS.get(svc.status, "?")
        tasks = f"{svc.tasks_completed}/{svc.tasks_total}"
        table.add_row(svc.slug, f"{icon} {svc.status}", tasks)
    return table


def render_verification_result(vr: VerificationResult) -> str:
    """Render verification result as a single-line string."""
    if vr.passed:
        return "✅ contracts OK ✅ boundaries OK"
    parts: list[str] = []
    failed_contracts = [c for c in vr.contract_results if not c.passed]
    if failed_contracts:
        parts.append(f"❌ {len(failed_contracts)} contract issue(s)")
    failed_bounds = list(vr.boundary_results)
    if failed_bounds:
        parts.append(f"❌ {len(failed_bounds)} boundary issue(s)")
    return " ".join(parts) if parts else "❌ verification failed"


def render_final_summary(report: IntegrationReport) -> Panel:
    """Render final summary as a Rich Panel."""
    verdict_icon = "✅" if report.verdict == "pass" else "❌"
    lines = [
        f"Verdict: {verdict_icon} {report.verdict.upper()}",
        f"Services: {report.succeeded_services}/{report.total_services} succeeded",
        f"Phases: {report.total_phases}",
    ]
    if report.failed_services:
        lines.append(f"Failed: {report.failed_services}")
    if report.skipped_services:
        lines.append(f"Skipped: {report.skipped_services}")
    content = Text("\n".join(lines))
    return Panel(content, title="Integration Summary")
