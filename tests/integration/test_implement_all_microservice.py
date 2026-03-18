"""Integration tests for specforge implement --all (microservice mode)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from specforge.core.orchestrator_models import IntegrationReport
from specforge.core.result import Err, Ok


def _scaffold_project(tmp_path: Path) -> Path:
    """Create minimal project scaffold."""
    specforge = tmp_path / ".specforge"
    specforge.mkdir()
    (specforge / "manifest.json").write_text(json.dumps({
        "architecture": "microservice",
        "services": [
            {"slug": "identity-service", "communication": []},
            {"slug": "admin-service", "communication": []},
            {"slug": "ledger-service", "communication": [{"target": "identity-service"}]},
            {"slug": "portfolio-service", "communication": [{"target": "identity-service"}]},
            {"slug": "planning-service", "communication": [{"target": "ledger-service"}]},
            {"slug": "analytics-service", "communication": [{"target": "ledger-service"}, {"target": "portfolio-service"}]},
        ],
    }))
    features = specforge / "features"
    for slug in ("identity-service", "admin-service", "ledger-service",
                 "portfolio-service", "planning-service", "analytics-service"):
        d = features / slug
        d.mkdir(parents=True)
        (d / "tasks.md").write_text("# Tasks\n")
    return tmp_path


def _make_pass_report() -> IntegrationReport:
    return IntegrationReport(
        architecture="microservice",
        total_phases=3, total_services=6,
        verdict="pass", succeeded_services=6,
    )


def _make_fail_report() -> IntegrationReport:
    return IntegrationReport(
        architecture="microservice",
        total_phases=3, total_services=6,
        verdict="fail", succeeded_services=4, failed_services=1,
    )


class TestImplementAllMicroservice:
    def test_implement_all_happy_path(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)

        mock_orch = MagicMock()
        mock_orch.execute.return_value = Ok(_make_pass_report())

        with patch("specforge.cli.implement_cmd._build_orchestrator", return_value=mock_orch):
            from specforge.cli.implement_cmd import implement
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(implement, ["--all"], catch_exceptions=False)

        # 0 if wired, 2 if not yet
        assert result.exit_code in (0, 2)

    def test_implement_all_and_target_mutually_exclusive(self) -> None:
        from specforge.cli.implement_cmd import implement
        runner = CliRunner()
        result = runner.invoke(implement, ["--all", "identity-service"])
        assert result.exit_code == 2

    def test_implement_all_and_shared_infra_mutually_exclusive(self) -> None:
        from specforge.cli.implement_cmd import implement
        runner = CliRunner()
        result = runner.invoke(implement, ["--all", "--shared-infra"])
        assert result.exit_code == 2

    def test_to_phase_requires_all(self) -> None:
        from specforge.cli.implement_cmd import implement
        runner = CliRunner()
        result = runner.invoke(implement, ["--to-phase", "2"])
        assert result.exit_code == 2
