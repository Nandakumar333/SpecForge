"""End-to-end integration tests for specforge forge CLI command (Feature 017)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from specforge.core.result import Err, Ok


def _scaffold_project(tmp_path: Path) -> Path:
    specforge = tmp_path / ".specforge"
    specforge.mkdir()
    config = {"agent": "claude", "stack": "python"}
    (specforge / "config.json").write_text(json.dumps(config))
    manifest = {
        "architecture": "monolithic",
        "project_description": "Test app",
        "features": [
            {"id": "001", "name": "core", "display_name": "Core",
             "description": "Core logic", "priority": "P0", "category": "core"},
        ],
        "services": [
            {"name": "Core", "slug": "core-service", "features": ["001"],
             "rationale": "test", "communication": []},
        ],
    }
    (specforge / "manifest.json").write_text(json.dumps(manifest))
    (specforge / "features" / "core-service").mkdir(parents=True)
    return tmp_path


def _mock_provider():
    provider = MagicMock()
    provider.call.return_value = Ok("# Generated\n\nContent here.")
    provider.is_available.return_value = Ok(None)
    return provider


class TestForgeEndToEnd:
    def test_forge_help(self) -> None:
        from specforge.cli.forge_cmd import forge
        runner = CliRunner()
        result = runner.invoke(forge, ["--help"])
        assert result.exit_code == 0
        assert "forge" in result.output.lower()

    def test_empty_description_error(self) -> None:
        from specforge.cli.forge_cmd import forge
        runner = CliRunner()
        result = runner.invoke(forge, [])
        assert result.exit_code == 2

    def test_resume_force_mutually_exclusive(self) -> None:
        from specforge.cli.forge_cmd import forge
        runner = CliRunner()
        result = runner.invoke(forge, ["test", "--resume", "--force"])
        assert result.exit_code != 0

    def test_dry_run_produces_prompt_files(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _mock_provider()

        with patch("specforge.cli.forge_cmd._build_forge") as mock_build:
            from specforge.core.forge_orchestrator import ForgeOrchestrator
            from specforge.core.forge_progress import ForgeProgress
            from rich.console import Console

            orch = ForgeOrchestrator(
                project_dir=project, llm_provider=provider,
            )
            mock_build.return_value = (orch, None)

            from specforge.cli.forge_cmd import forge
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                import os
                os.chdir(str(project))
                result = runner.invoke(
                    forge, ["Test App", "--dry-run", "--force"],
                    catch_exceptions=False,
                )

        svc_dir = project / ".specforge" / "features" / "core-service"
        prompt_files = list(svc_dir.glob("*.prompt.md"))
        assert len(prompt_files) == 7

    def test_skip_init_on_missing_project(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        provider = _mock_provider()

        with patch("specforge.cli.forge_cmd._build_forge") as mock_build:
            from specforge.core.forge_orchestrator import ForgeOrchestrator
            orch = ForgeOrchestrator(
                project_dir=project, llm_provider=provider,
            )
            mock_build.return_value = (orch, None)

            from specforge.cli.forge_cmd import forge
            runner = CliRunner()
            with runner.isolated_filesystem(temp_dir=tmp_path):
                import os
                os.chdir(str(project))
                result = runner.invoke(
                    forge, ["Test App", "--skip-init", "--force"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 2
