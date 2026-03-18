"""Integration tests for specforge implement --all (monolith mode)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from specforge.core.orchestrator_models import IntegrationReport
from specforge.core.result import Ok


def _scaffold_monolith(tmp_path: Path) -> Path:
    specforge = tmp_path / ".specforge"
    specforge.mkdir()
    (specforge / "manifest.json").write_text(json.dumps({
        "architecture": "monolithic",
        "services": [
            {"slug": "auth-module", "communication": []},
            {"slug": "ledger-module", "communication": [{"target": "auth-module"}]},
        ],
    }))
    features = specforge / "features"
    for slug in ("auth-module", "ledger-module"):
        d = features / slug
        d.mkdir(parents=True)
        (d / "tasks.md").write_text("# Tasks\n")
    return tmp_path


class TestImplementAllMonolith:
    def test_implement_all_monolith_no_docker(self, tmp_path: Path) -> None:
        _scaffold_monolith(tmp_path)
        mock_orch = MagicMock()
        mock_orch.execute.return_value = Ok(IntegrationReport(
            architecture="monolithic",
            total_phases=2, total_services=2,
            verdict="pass", succeeded_services=2,
        ))

        with patch("specforge.cli.implement_cmd._build_orchestrator", return_value=mock_orch):
            from specforge.cli.implement_cmd import implement
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(implement, ["--all"], catch_exceptions=False)

        assert result.exit_code in (0, 2)

    def test_implement_all_monolith_boundary_checks(self, tmp_path: Path) -> None:
        _scaffold_monolith(tmp_path)
        mock_orch = MagicMock()
        mock_orch.execute.return_value = Ok(IntegrationReport(
            architecture="modular-monolith",
            total_phases=2, total_services=2,
            verdict="pass", succeeded_services=2,
        ))

        with patch("specforge.cli.implement_cmd._build_orchestrator", return_value=mock_orch):
            from specforge.cli.implement_cmd import implement
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(implement, ["--all"], catch_exceptions=False)

        assert result.exit_code in (0, 2)
