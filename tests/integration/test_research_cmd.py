"""Integration tests for specforge research command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.research_cmd import research
from specforge.core.config import PIPELINE_STATE_FILENAME


def _write_manifest(tmp_path: Path, manifest: dict | None = None) -> None:
    """Write a test manifest.json to .specforge/."""
    if manifest is None:
        manifest = {
            "schema_version": "1.0",
            "architecture": "microservice",
            "project_description": "Personal Finance Tracker",
            "domain": "finance",
            "features": [
                {
                    "id": "002",
                    "name": "accounts",
                    "display_name": "Account Management",
                    "description": "Track bank accounts with balances and categories",
                    "priority": "P1",
                    "category": "core",
                    "service": "ledger-service",
                },
                {
                    "id": "003",
                    "name": "transactions",
                    "display_name": "Transaction Tracking",
                    "description": "Record expenses with categories and tags",
                    "priority": "P1",
                    "category": "core",
                    "service": "ledger-service",
                },
                {
                    "id": "004",
                    "name": "budgets",
                    "display_name": "Budget Planning",
                    "description": "Create budgets by categories and track spending",
                    "priority": "P1",
                    "category": "core",
                    "service": "planning-service",
                },
            ],
            "services": [
                {
                    "name": "Ledger Service",
                    "slug": "ledger-service",
                    "features": ["002", "003"],
                    "rationale": "Core financial tracking",
                    "communication": [
                        {
                            "target": "planning-service",
                            "pattern": "async-events",
                            "required": False,
                            "description": "Events",
                        },
                    ],
                },
                {
                    "name": "Planning Service",
                    "slug": "planning-service",
                    "features": ["004"],
                    "rationale": "Financial planning",
                    "communication": [
                        {
                            "target": "ledger-service",
                            "pattern": "sync-rest",
                            "required": True,
                            "description": "Read data",
                        },
                    ],
                },
            ],
            "events": [],
        }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_spec(tmp_path: Path, slug: str, content: str) -> Path:
    """Write a spec.md file for the given service slug."""
    out_dir = tmp_path / ".specforge" / "features" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_path = out_dir / "spec.md"
    spec_path.write_text(content, encoding="utf-8")
    return spec_path


SPEC_WITH_TECH_REFS = """\
# Ledger Service Spec

## Technical Details

The service uses gRPC for auth validation with the identity service.
Data is stored in PostgreSQL with Redis caching.

[NEEDS CLARIFICATION: database choice for transaction history]

## Assumptions

- Standard assumptions apply.
"""


class TestResearchHappyPath:
    """Tests for successful research invocations."""

    def test_research_exits_zero(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_TECH_REFS)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 0, result.output

    def test_research_creates_research_md(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_TECH_REFS)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        research_path = (
            tmp_path
            / ".specforge"
            / "features"
            / "ledger-service"
            / "research.md"
        )
        assert research_path.exists(), "research.md should be created"

    def test_research_md_has_structured_content(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_TECH_REFS)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        research_path = (
            tmp_path
            / ".specforge"
            / "features"
            / "ledger-service"
            / "research.md"
        )
        content = research_path.read_text(encoding="utf-8")
        # Research output should contain markdown headings and findings
        assert "#" in content, "research.md should contain markdown headings"
        assert len(content) > 50, "research.md should have substantial content"

    def test_pipeline_state_updated(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_TECH_REFS)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        state_path = (
            tmp_path
            / ".specforge"
            / "features"
            / "ledger-service"
            / PIPELINE_STATE_FILENAME
        )
        assert state_path.exists(), "Pipeline state file should exist"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        research_phase = next(
            (p for p in state["phases"] if p["name"] == "research"), None,
        )
        assert research_phase is not None, "research phase should exist in state"
        assert research_phase["status"] == "complete"

    def test_lock_released_after_success(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_TECH_REFS)
        runner = CliRunner()
        runner.invoke(research, [ "ledger-service"])
        lock_path = tmp_path / ".specforge" / ".pipeline-lock"
        assert not lock_path.exists(), "Pipeline lock should be released"


class TestResearchErrorPaths:
    """Tests for research error handling."""

    def test_missing_manifest_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 1
        assert "manifest" in result.output.lower()

    def test_missing_spec_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(research, [ "ledger-service"])
        assert result.exit_code == 1
        assert "spec.md" in result.output.lower()

    def test_unknown_service_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(research, [ "nonexistent-service"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
