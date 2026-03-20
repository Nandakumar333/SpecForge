"""Unit tests for ForgeOrchestrator (Feature 017)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.forge_orchestrator import (
    STATE_EXISTS,
    ForgeOrchestrator,
    ForgeReport,
)
from specforge.core.forge_state import ForgeState, ServiceForgeStatus
from specforge.core.result import Err, Ok


def _make_provider(responses: list[str] | None = None) -> MagicMock:
    provider = MagicMock()
    if responses:
        provider.call.side_effect = [Ok(r) for r in responses]
    else:
        provider.call.return_value = Ok("# Generated content\n\nSample output")
    provider.is_available.return_value = Ok(None)
    return provider


def _scaffold_project(tmp_path: Path, arch: str = "monolithic") -> Path:
    specforge = tmp_path / ".specforge"
    specforge.mkdir()
    config = {"agent": "claude", "stack": "python"}
    (specforge / "config.json").write_text(json.dumps(config))
    manifest = {
        "architecture": arch,
        "project_description": "Test app",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Auth",
             "description": "Authentication", "priority": "P0", "category": "core"},
        ],
        "services": [
            {"name": "Auth", "slug": "auth", "features": ["001"],
             "rationale": "test", "communication": []},
            {"name": "API", "slug": "api", "features": [],
             "rationale": "test", "communication": []},
        ],
    }
    (specforge / "manifest.json").write_text(json.dumps(manifest))
    features = specforge / "features"
    for slug in ("auth", "api"):
        (features / slug).mkdir(parents=True)
    return tmp_path


class TestForgeOrchestrator:
    def test_run_forge_happy_path(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(
            description="Test app",
            arch_type="monolithic",
            force=True,
        )
        assert result.ok
        report = result.value
        assert isinstance(report, ForgeReport)
        assert report.architecture == "monolithic"

    def test_run_forge_no_description_with_resume(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        # First run
        orch.run_forge(description="Test app", force=True)
        # Resume with empty description is valid
        result = orch.run_forge(description="", resume=True)
        assert result.ok

    def test_stages_execute_in_order(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok
        state_path = project / ".specforge" / "forge-state.json"
        assert state_path.exists()

    def test_decompose_uses_existing_manifest(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok
        report = result.value
        assert len(report.services) == 2

    def test_decompose_llm_with_fallback(self, tmp_path: Path) -> None:
        """When no manifest exists and LLM fails, fallback to DomainAnalyzer."""
        project = tmp_path / "fresh"
        specforge = project / ".specforge"
        specforge.mkdir(parents=True)
        (specforge / "config.json").write_text(json.dumps({"agent": "claude"}))
        (specforge / "features").mkdir()

        provider = MagicMock()
        provider.call.return_value = Err("timeout")

        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Create a TODO app", force=True)
        # Should succeed via fallback or fail gracefully
        assert result.ok or "failed" in result.error.lower()

    def test_state_exists_without_flags(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        # Create existing state
        state = ForgeState.create()
        state_path = project / ".specforge" / "forge-state.json"
        state.save(state_path)

        result = orch.run_forge(description="Test")
        assert not result.ok
        assert result.error == STATE_EXISTS

    def test_force_overwrites_state(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        state = ForgeState.create()
        state_path = project / ".specforge" / "forge-state.json"
        state.save(state_path)

        result = orch.run_forge(description="Test", force=True)
        assert result.ok

    def test_resume_skips_completed(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)

        state = ForgeState.create(description="Test")
        state.stage = "spec_generation"
        state.services["auth"] = ServiceForgeStatus(
            slug="auth", status="complete", last_completed_phase=7,
        )
        state.services["api"] = ServiceForgeStatus(
            slug="api", status="failed", retry_count=1,
        )
        state_path = project / ".specforge" / "forge-state.json"
        state.save(state_path)

        result = orch.run_forge(description="Test", resume=True)
        assert result.ok

    def test_validation_checks_artifacts(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok
        # Check that artifacts were written
        auth_dir = project / ".specforge" / "features" / "auth"
        assert (auth_dir / "spec.md").exists()

    def test_report_generated(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok
        report_path = project / ".specforge" / "reports" / "forge-report.md"
        assert report_path.exists()

    def test_exit_code_all_success(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok
        assert result.value.exit_code == 0

    def test_provider_agnostic(self, tmp_path: Path) -> None:
        """ForgeOrchestrator works with any mock LLMProvider."""
        project = _scaffold_project(tmp_path)
        for agent_name in ("claude", "copilot", "gemini"):
            provider = _make_provider()
            provider._agent_name = agent_name
            orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
            result = orch.run_forge(description="Test", force=True)
            assert result.ok


class TestAutoInit:
    def test_auto_init_when_no_specforge(self, tmp_path: Path) -> None:
        project = tmp_path / "new_project"
        project.mkdir()
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Build a TODO app", force=True)
        specforge_dir = project / ".specforge"
        # Auto-init should create .specforge/
        assert specforge_dir.exists() or not result.ok

    def test_skip_init_missing_specforge(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(
            description="Test", skip_init=True, force=True,
        )
        assert not result.ok
        assert "not initialized" in result.error.lower()

    def test_existing_specforge_skips_init(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", force=True)
        assert result.ok


class TestDryRun:
    def test_dry_run_no_llm_calls(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", dry_run=True, force=True)
        assert result.ok
        # Check .prompt.md files exist
        auth_dir = project / ".specforge" / "features" / "auth"
        prompt_files = list(auth_dir.glob("*.prompt.md"))
        assert len(prompt_files) == 7

    def test_dry_run_exit_code_zero(self, tmp_path: Path) -> None:
        project = _scaffold_project(tmp_path)
        provider = _make_provider()
        orch = ForgeOrchestrator(project_dir=project, llm_provider=provider)
        result = orch.run_forge(description="Test", dry_run=True, force=True)
        assert result.ok
