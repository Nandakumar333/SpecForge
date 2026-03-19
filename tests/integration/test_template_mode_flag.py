"""Integration tests for --template-mode flag on the specify command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write microservice manifest with 2 services (3 features)."""
    manifest = {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login and sessions", "priority": "P0",
             "category": "foundation", "service": "identity-service"},
            {"id": "002", "name": "accounts", "display_name": "Accounts",
             "description": "Account tracking", "priority": "P1",
             "category": "core", "service": "ledger-service"},
            {"id": "003", "name": "transactions", "display_name": "Transactions",
             "description": "Transaction processing", "priority": "P1",
             "category": "core", "service": "ledger-service"},
        ],
        "services": [
            {"name": "Identity Service", "slug": "identity-service",
             "features": ["001"], "rationale": "Auth",
             "communication": []},
            {"name": "Ledger Service", "slug": "ledger-service",
             "features": ["002", "003"], "rationale": "Finance",
             "communication": [
                 {"target": "identity-service", "pattern": "sync-rest",
                  "required": True, "description": "Auth checks"}]},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_config(tmp_path: Path, agent: str = "generic") -> None:
    """Write config.json with the specified agent."""
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    config = {"agent": agent, "stack": "python"}
    (d / "config.json").write_text(json.dumps(config), encoding="utf-8")


ARTIFACT_FILES = [
    "spec.md", "research.md", "data-model.md",
    "edge-cases.md", "plan.md", "checklist.md", "tasks.md",
]

PROMPT_FILES = [
    "spec.prompt.md", "research.prompt.md", "data-model.prompt.md",
    "edge-cases.prompt.md", "plan.prompt.md", "checklist.prompt.md",
    "tasks.prompt.md",
]


class TestTemplateModeFlag:
    """Tests for --template-mode flag behavior."""

    def test_template_mode_produces_artifacts(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """specify --template-mode produces all 7 .md artifacts."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["specify", "identity-service", "--template-mode"]
        )
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "identity-service"
        for af in ARTIFACT_FILES:
            assert (out / af).exists(), f"Missing {af}. Output: {result.output}"

    def test_template_mode_no_prompt_files(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """With --template-mode, no .prompt.md files should exist."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "identity-service", "--template-mode"])
        out = tmp_path / ".specforge" / "features" / "identity-service"
        for pf in PROMPT_FILES:
            assert not (out / pf).exists(), (
                f"Unexpected prompt file {pf} in template mode"
            )

    def test_template_mode_identical_to_default_without_provider(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When agent is 'generic', default mode auto-falls back to template mode."""
        dir_explicit = tmp_path / "explicit"
        dir_explicit.mkdir()
        _write_manifest(dir_explicit)

        dir_fallback = tmp_path / "fallback"
        dir_fallback.mkdir()
        _write_manifest(dir_fallback)
        _write_config(dir_fallback, agent="generic")

        runner = CliRunner()

        monkeypatch.chdir(dir_explicit)
        res_explicit = runner.invoke(
            cli, ["specify", "identity-service", "--template-mode"]
        )
        assert res_explicit.exit_code == 0, res_explicit.output

        monkeypatch.chdir(dir_fallback)
        res_fallback = runner.invoke(cli, ["specify", "identity-service"])
        assert res_fallback.exit_code == 0, res_fallback.output

        out_explicit = (
            dir_explicit / ".specforge" / "features" / "identity-service"
        )
        out_fallback = (
            dir_fallback / ".specforge" / "features" / "identity-service"
        )

        for af in ARTIFACT_FILES:
            assert (out_explicit / af).exists(), f"Missing {af} in explicit run"
            assert (out_fallback / af).exists(), f"Missing {af} in fallback run"
            content_a = (out_explicit / af).read_text(encoding="utf-8")
            content_b = (out_fallback / af).read_text(encoding="utf-8")
            assert content_a == content_b, (
                f"{af} differs between --template-mode and auto-fallback"
            )

    def test_auto_fallback_emits_warning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When agent is 'generic', a warning about falling back appears."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_config(tmp_path, agent="generic")
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "identity-service"])
        assert result.exit_code == 0, result.output
        assert "Falling back" in result.output or "falling back" in result.output, (
            f"Expected fallback warning in output: {result.output}"
        )
