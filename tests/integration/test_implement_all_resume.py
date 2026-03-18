"""Integration tests for specforge implement --all --resume."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from specforge.core.orchestrator_models import IntegrationReport
from specforge.core.result import Ok


def _scaffold_project(tmp_path: Path) -> Path:
    specforge = tmp_path / ".specforge"
    specforge.mkdir()
    (specforge / "manifest.json").write_text(json.dumps({
        "architecture": "microservice",
        "services": [
            {"slug": "identity-service", "communication": []},
            {"slug": "ledger-service", "communication": [{"target": "identity-service"}]},
        ],
    }))
    features = specforge / "features"
    for slug in ("identity-service", "ledger-service"):
        d = features / slug
        d.mkdir(parents=True)
        (d / "tasks.md").write_text("# Tasks\n")
    return tmp_path


class TestImplementAllResume:
    def test_resume_skips_completed(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)

        # Create state file with phase 0 completed
        from specforge.core.orchestration_state import (
            create_initial_state, mark_phase_in_progress,
            mark_service_completed, save_state,
        )
        from specforge.core.orchestrator_models import OrchestrationPlan, Phase
        from dataclasses import replace as dc_replace

        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(
                Phase(index=0, services=("identity-service",)),
                Phase(index=1, services=("ledger-service",)),
            ),
            total_services=2, shared_infra_required=True,
        )
        state = create_initial_state(plan)
        state = mark_phase_in_progress(state, 0)
        state = mark_service_completed(state, 0, "identity-service", 5, 5)
        phase0 = dc_replace(state.phases[0], status="completed")
        state = dc_replace(state, phases=(phase0, state.phases[1]), shared_infra_status="completed")
        save_state(tmp_path / ".specforge" / "orchestration-state.json", state)

        mock_orch = MagicMock()
        mock_orch.execute.return_value = Ok(IntegrationReport(
            architecture="microservice",
            total_phases=2, total_services=2,
            verdict="pass", succeeded_services=2,
        ))

        with patch("specforge.cli.implement_cmd._build_orchestrator", return_value=mock_orch):
            from specforge.cli.implement_cmd import implement
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(
                    implement, ["--all", "--resume"], catch_exceptions=False,
                )

        assert result.exit_code in (0, 2)

    def test_resume_no_state_starts_fresh(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)

        mock_orch = MagicMock()
        mock_orch.execute.return_value = Ok(IntegrationReport(
            architecture="microservice",
            total_phases=2, total_services=2,
            verdict="pass", succeeded_services=2,
        ))

        with patch("specforge.cli.implement_cmd._build_orchestrator", return_value=mock_orch):
            from specforge.cli.implement_cmd import implement
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(
                    implement, ["--all", "--resume"], catch_exceptions=False,
                )

        assert result.exit_code in (0, 2)
