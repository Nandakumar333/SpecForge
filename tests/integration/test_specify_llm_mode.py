"""Integration tests for full LLM pipeline via specify --dry-run-prompt."""

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
    """Write config.json and constitution for LLM pipeline tests."""
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    config = {"agent": agent, "stack": "python"}
    (d / "config.json").write_text(json.dumps(config), encoding="utf-8")
    mem = d / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "constitution.md").write_text(
        "# Constitution\n\nMinimal constitution for testing.\n",
        encoding="utf-8",
    )


PROMPT_FILES = [
    "spec.prompt.md",
    "research.prompt.md",
    "data-model.prompt.md",
    "edge-cases.prompt.md",
    "plan.prompt.md",
    "checklist.prompt.md",
    "tasks.prompt.md",
]

ALL_PHASES = ["spec", "research", "datamodel", "edgecase", "plan", "checklist", "tasks"]


class TestSpecifyLLMMode:
    """Tests for specify pipeline with mock LLM provider via --dry-run-prompt."""

    def test_dry_run_generates_all_prompt_files(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Run specify --dry-run-prompt and verify all 7 .prompt.md files created."""
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
            assert (out / pf).exists(), f"Missing {pf}. Output: {result.output}"

    def test_prompt_files_contain_spec_kit_skeleton(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Check that spec.prompt.md contains Spec-Kit format markers."""
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
        spec_prompt = (
            tmp_path / ".specforge" / "features" / "identity-service"
            / "spec.prompt.md"
        )
        content = spec_prompt.read_text(encoding="utf-8")
        assert "Feature Specification" in content
        assert "Requirements" in content
        assert "Success Criteria" in content

    def test_prompt_files_contain_architecture_context(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """For microservice manifest, verify prompts contain architecture context."""
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
        spec_prompt = (
            tmp_path / ".specforge" / "features" / "identity-service"
            / "spec.prompt.md"
        )
        content = spec_prompt.read_text(encoding="utf-8")
        has_microservice = "icroservice" in content
        has_docker = "Docker" in content
        assert has_microservice or has_docker, (
            "Prompt should contain microservice/Docker architecture context"
        )

    def test_prompt_files_contain_prior_artifacts_in_later_phases(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Check that tasks.prompt.md references content from earlier phases."""
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
        tasks_prompt = (
            tmp_path / ".specforge" / "features" / "identity-service"
            / "tasks.prompt.md"
        )
        content = tasks_prompt.read_text(encoding="utf-8")
        assert "Prior Artifacts" in content, (
            "tasks.prompt.md should include prior artifacts section"
        )
        assert "### spec" in content, (
            "tasks.prompt.md should reference spec phase output"
        )

    def test_pipeline_state_records_all_phases(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Check .pipeline-state.json has all 7 phases as 'complete'."""
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
        state_path = (
            tmp_path / ".specforge" / "features" / "identity-service"
            / ".pipeline-state.json"
        )
        assert state_path.exists(), "Pipeline state file should exist"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        phases = {p["name"]: p["status"] for p in state["phases"]}
        for phase_name in ALL_PHASES:
            assert phases.get(phase_name) == "complete", (
                f"Phase '{phase_name}' should be 'complete', "
                f"got '{phases.get(phase_name)}'"
            )
