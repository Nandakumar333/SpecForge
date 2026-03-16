"""Integration tests for specforge clarify command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


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


SPEC_WITH_AMBIGUITIES = """\
# Ledger Service Spec

## Features

Transactions should be processed appropriately based on account type.
The system should handle various edge cases as needed.
Categories TBD.

## Assumptions

- Standard assumptions apply.
"""

SPEC_CLEAN = """\
# spec

## features

all items are processed in order with a 5-second timeout.
each record has exactly one owner.

## assumptions

- none.
"""


class TestClarifyHappyPath:
    """Tests for successful clarify invocations."""

    def test_clarify_by_slug_exits_zero(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["clarify", "ledger-service"],
            input="skip\nskip\nskip\nskip\nskip\n",
        )
        assert result.exit_code == 0, result.output

    def test_clarify_outputs_scanning_message(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["clarify", "ledger-service"],
            input="skip\nskip\nskip\nskip\nskip\n",
        )
        assert result.exit_code == 0, result.output
        assert "ledger-service" in result.output.lower()

    def test_feature_number_resolves_to_service(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["clarify", "002"],
            input="skip\nskip\nskip\nskip\nskip\n",
        )
        assert result.exit_code == 0, result.output

    def test_no_ambiguities_detected(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        # Use a single-service manifest so BoundaryAnalyzer finds no shared concepts
        single_svc = {
            "schema_version": "1.0",
            "architecture": "monolith",
            "project_description": "Simple App",
            "domain": "general",
            "features": [
                {
                    "id": "001",
                    "name": "core",
                    "display_name": "Core",
                    "description": "Main functionality",
                    "priority": "P1",
                    "category": "core",
                    "service": "main-service",
                },
            ],
            "services": [
                {
                    "name": "Main Service",
                    "slug": "main-service",
                    "features": ["001"],
                    "rationale": "Monolith",
                    "communication": [],
                },
            ],
            "events": [],
        }
        _write_manifest(tmp_path, single_svc)
        _write_spec(tmp_path, "main-service", SPEC_CLEAN)
        runner = CliRunner()
        result = runner.invoke(cli, ["clarify", "main-service"])
        assert result.exit_code == 0, result.output
        assert "no ambiguities" in result.output.lower()

    def test_lock_released_after_success(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        runner.invoke(
            cli,
            ["clarify", "ledger-service"],
            input="skip\nskip\nskip\nskip\nskip\n",
        )
        lock_path = tmp_path / ".specforge" / ".pipeline-lock"
        assert not lock_path.exists(), "Pipeline lock should be released"


class TestClarifyErrorPaths:
    """Tests for clarify error handling."""

    def test_missing_manifest_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["clarify", "ledger-service"])
        assert result.exit_code == 1
        assert "manifest" in result.output.lower()

    def test_missing_spec_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        # No spec.md written — output_dir exists but spec.md does not
        runner = CliRunner()
        result = runner.invoke(cli, ["clarify", "ledger-service"])
        assert result.exit_code == 1
        assert "spec.md" in result.output.lower()

    def test_unknown_service_exits_one(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["clarify", "nonexistent-service"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestClarifyReportMode:
    """Tests for --report flag behaviour."""

    def test_report_creates_clarifications_report(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["clarify", "ledger-service", "--report"],
        )
        assert result.exit_code == 0, result.output
        report_path = (
            tmp_path
            / ".specforge"
            / "features"
            / "ledger-service"
            / "clarifications-report.md"
        )
        assert report_path.exists(), "clarifications-report.md should be created"

    def test_report_does_not_modify_spec(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        spec_path = _write_spec(
            tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES,
        )
        original_content = spec_path.read_text(encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["clarify", "ledger-service", "--report"],
        )
        assert result.exit_code == 0, result.output
        assert spec_path.read_text(encoding="utf-8") == original_content

    def test_report_lock_released(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service", SPEC_WITH_AMBIGUITIES)
        runner = CliRunner()
        runner.invoke(cli, ["clarify", "ledger-service", "--report"])
        lock_path = tmp_path / ".specforge" / ".pipeline-lock"
        assert not lock_path.exists(), "Pipeline lock should be released"
