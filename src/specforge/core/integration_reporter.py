"""Integration reporter — generates Markdown report (Feature 011)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from specforge.core.config import INTEGRATION_REPORT_FILENAME
from specforge.core.orchestrator_models import (
    IntegrationReport,
    OrchestrationPlan,
    OrchestrationState,
    VerificationResult,
)
from specforge.core.result import Err, Ok, Result


class IntegrationReporter:
    """Generates integration report as Markdown file."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def generate(
        self,
        report: IntegrationReport,
        state: OrchestrationState,
        plan: OrchestrationPlan,
    ) -> Result[Path, str]:
        """Generate integration report and write to disk."""
        try:
            elapsed = self._compute_elapsed(state, report)
            content = self._build_content(report, elapsed)
            path = self._root / ".specforge" / INTEGRATION_REPORT_FILENAME
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return Ok(path)
        except OSError as exc:
            return Err(f"Failed to write report: {exc}")

    # ------------------------------------------------------------------
    # Private helpers (each ≤ 30 lines)
    # ------------------------------------------------------------------

    def _compute_elapsed(
        self, state: OrchestrationState, report: IntegrationReport,
    ) -> str | None:
        """Return human-readable elapsed time, or None."""
        if not state.started_at:
            return None
        try:
            start = datetime.fromisoformat(state.started_at)
            end = datetime.fromisoformat(report.created_at)
            delta = end - start
            total_secs = int(delta.total_seconds())
            if total_secs < 0:
                return None
            mins, secs = divmod(total_secs, 60)
            hrs, mins = divmod(mins, 60)
            if hrs:
                return f"{hrs}h {mins}m {secs}s"
            if mins:
                return f"{mins}m {secs}s"
            return f"{secs}s"
        except (ValueError, TypeError):
            return None

    def _build_content(
        self, report: IntegrationReport, elapsed: str | None,
    ) -> str:
        """Build full markdown content from report data."""
        lines: list[str] = [
            "# Integration Report",
            "",
            f"**Architecture**: {report.architecture}",
            f"**Generated**: {report.created_at}",
            "",
        ]
        lines.extend(self._build_summary(report, elapsed))
        lines.extend(self._build_phases(report))
        lines.extend(self._build_verification(report))
        lines.extend(self._build_integration(report))
        return "\n".join(lines)

    def _build_summary(
        self, report: IntegrationReport, elapsed: str | None,
    ) -> list[str]:
        """Build summary table."""
        lines = [
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Phases | {report.total_phases} |",
            f"| Total Services | {report.total_services} |",
            f"| Succeeded | {report.succeeded_services} |",
            f"| Failed | {report.failed_services} |",
            f"| Skipped | {report.skipped_services} |",
            f"| **Verdict** | **{report.verdict.upper()}** |",
        ]
        if elapsed:
            lines.append(f"| Elapsed Time | {elapsed} |")
        lines.append("")
        return lines

    def _build_phases(self, report: IntegrationReport) -> list[str]:
        """Build per-phase service tables."""
        lines = ["## Phase Results", ""]
        for phase in report.phase_results:
            lines.append(f"### Phase {phase.index}")
            lines.append("")
            lines.append("| Service | Status | Tasks |")
            lines.append("|---------|--------|-------|")
            for svc in phase.services:
                lines.append(
                    f"| {svc.slug} | {svc.status} "
                    f"| {svc.tasks_completed}/{svc.tasks_total} |",
                )
            lines.append("")
        return lines

    def _build_verification(self, report: IntegrationReport) -> list[str]:
        """Build verification results section."""
        if not report.verification_results:
            return []
        lines = ["## Verification Results", ""]
        for vr in report.verification_results:
            lines.extend(self._build_single_verification(vr))
        return lines

    def _build_single_verification(self, vr: VerificationResult) -> list[str]:
        """Build one verification result block."""
        tag = "✅ PASS" if vr.passed else "❌ FAIL"
        lines = [f"### After Phase {vr.after_phase}", "", f"**Result**: {tag}", ""]
        for cr in vr.contract_results:
            icon = "✅" if cr.passed else "❌"
            lines.append(f"- **{cr.consumer}** ↔ **{cr.provider}**: {icon}")
            if not cr.passed:
                for m in cr.mismatches:
                    lines.append(
                        f"  - Field: `{m.field}` — "
                        f"Expected: `{m.expected}`, Actual: `{m.actual}`",
                    )
        for br in vr.boundary_results:
            lines.append(
                f"- **{br.entity}**: {br.violation_type} — {br.details}",
            )
        lines.append("")
        return lines

    def _build_integration(self, report: IntegrationReport) -> list[str]:
        """Build integration validation section."""
        ir = report.integration_result
        if ir is None:
            return []
        tag = "✅ PASS" if ir.passed else "❌ FAIL"
        lines = [
            "## Integration Validation",
            "",
            f"**Result**: {tag}",
            "",
        ]
        if ir.health_checks:
            lines.extend(self._build_health_checks(ir.health_checks))
        return lines

    def _build_health_checks(
        self, checks: tuple,  # tuple[HealthCheckResult, ...]
    ) -> list[str]:
        """Build health checks table."""
        lines = [
            "### Health Checks",
            "",
            "| Service | Status | Response Time |",
            "|---------|--------|--------------|",
        ]
        for hc in checks:
            icon = "✅" if hc.passed else "❌"
            rt = f"{hc.response_time_ms}" if hc.response_time_ms else "N/A"
            lines.append(f"| {hc.service} | {icon} | {rt}ms |")
        lines.append("")
        return lines
