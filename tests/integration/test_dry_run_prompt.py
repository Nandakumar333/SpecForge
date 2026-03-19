"""Integration tests for --dry-run-prompt flag on specify and decompose."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.core.result import Ok


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


def _write_config(tmp_path: Path, agent: str = "claude") -> None:
    """Write config.json for LLM-related tests."""
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    config = {"agent": agent, "stack": "python"}
    (d / "config.json").write_text(json.dumps(config), encoding="utf-8")


PROMPT_FILES = [
    "spec.prompt.md", "research.prompt.md", "data-model.prompt.md",
    "edge-cases.prompt.md", "plan.prompt.md", "checklist.prompt.md",
    "tasks.prompt.md",
]

ARTIFACT_FILES = [
    "spec.md", "research.md", "data-model.md",
    "edge-cases.md", "plan.md", "checklist.md", "tasks.md",
]


class TestDryRunPromptFlag:
    """Tests for --dry-run-prompt flag behavior."""

    def test_dry_run_writes_prompt_files_not_artifacts(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """With --dry-run-prompt, .prompt.md files exist but regular .md do NOT."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_config(tmp_path, agent="claude")
        runner = CliRunner()
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            result = runner.invoke(
                cli, ["specify", "identity-service", "--dry-run-prompt"]
            )
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "identity-service"
        for pf in PROMPT_FILES:
            assert (out / pf).exists(), f"Missing prompt file {pf}"
        for af in ARTIFACT_FILES:
            assert not (out / af).exists(), (
                f"Artifact {af} should NOT exist in dry-run-prompt mode"
            )

    def test_dry_run_prompt_content_structure(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Each .prompt.md starts with '# System Prompt' and contains '# User Prompt'."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_config(tmp_path, agent="claude")
        runner = CliRunner()
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            runner.invoke(
                cli, ["specify", "identity-service", "--dry-run-prompt"]
            )
        out = tmp_path / ".specforge" / "features" / "identity-service"
        for pf in PROMPT_FILES:
            content = (out / pf).read_text(encoding="utf-8")
            assert content.startswith("# System Prompt"), (
                f"{pf} should start with '# System Prompt'"
            )
            assert "# User Prompt" in content, (
                f"{pf} should contain '# User Prompt'"
            )

    def test_mutual_exclusion_rejected(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """specify --template-mode --dry-run-prompt should fail with non-zero exit."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["specify", "dummy-target", "--template-mode", "--dry-run-prompt"],
        )
        assert result.exit_code != 0, (
            "Mutual exclusion of --template-mode and --dry-run-prompt "
            f"should fail. Output: {result.output}"
        )

    def test_dry_run_prompt_for_decompose(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """decompose --dry-run-prompt writes .specforge/decompose.prompt.md."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, agent="claude")
        runner = CliRunner()
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            result = runner.invoke(
                cli,
                ["decompose", "--dry-run-prompt", "Personal Finance App"],
            )
        assert result.exit_code == 0, result.output
        prompt_file = tmp_path / ".specforge" / "decompose.prompt.md"
        assert prompt_file.exists(), (
            f"Expected decompose.prompt.md. Output: {result.output}"
        )
        content = prompt_file.read_text(encoding="utf-8")
        assert "# System Prompt" in content
        assert "# User Prompt" in content
