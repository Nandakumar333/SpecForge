"""Integration tests for specforge edge-cases CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.edge_cases_cmd import edge_cases
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
                    "id": "001",
                    "name": "transactions",
                    "display_name": "Transaction Recording",
                    "description": "Record income/expense",
                    "priority": "P0",
                    "category": "core",
                    "service": "ledger-service",
                },
                {
                    "id": "002",
                    "name": "auth",
                    "display_name": "Authentication",
                    "description": "User auth",
                    "priority": "P0",
                    "category": "core",
                    "service": "identity-service",
                },
            ],
            "services": [
                {
                    "name": "Ledger Service",
                    "slug": "ledger-service",
                    "features": ["001"],
                    "rationale": "Core financial tracking",
                    "communication": [
                        {
                            "target": "identity-service",
                            "pattern": "sync-rest",
                            "required": True,
                            "description": "Token validation",
                        },
                    ],
                },
                {
                    "name": "Identity Service",
                    "slug": "identity-service",
                    "features": ["002"],
                    "rationale": "Auth management",
                    "communication": [],
                },
            ],
            "events": [
                {
                    "name": "transaction.created",
                    "producer": "ledger-service",
                    "consumers": ["identity-service"],
                },
            ],
        }
    specforge_dir = tmp_path / ".specforge"
    specforge_dir.mkdir(parents=True, exist_ok=True)
    (specforge_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )


def _write_spec(tmp_path: Path, slug: str) -> None:
    """Write a minimal spec.md for a service."""
    features_dir = tmp_path / ".specforge" / "features" / slug
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "spec.md").write_text(
        "# Spec\nBasic spec content.", encoding="utf-8",
    )


class TestEdgeCasesHappyPath:
    """Tests for successful edge-cases invocations."""

    def test_edge_cases_creates_md(
        self, tmp_path: Path, monkeypatch: object,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service")
        runner = CliRunner()
        result = runner.invoke(edge_cases, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        out_path = (
            tmp_path / ".specforge" / "features"
            / "ledger-service" / "edge-cases.md"
        )
        assert out_path.exists(), "edge-cases.md should be created"

    def test_edge_cases_has_yaml_blocks(
        self, tmp_path: Path, monkeypatch: object,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service")
        runner = CliRunner()
        result = runner.invoke(edge_cases, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        out_path = (
            tmp_path / ".specforge" / "features"
            / "ledger-service" / "edge-cases.md"
        )
        content = out_path.read_text(encoding="utf-8")
        assert "```yaml" in content, "edge-cases.md should contain yaml blocks"

    def test_pipeline_state_updated(
        self, tmp_path: Path, monkeypatch: object,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_spec(tmp_path, "ledger-service")
        runner = CliRunner()
        result = runner.invoke(edge_cases, [ "ledger-service"])
        assert result.exit_code == 0, result.output
        state_path = (
            tmp_path / ".specforge" / "features"
            / "ledger-service" / PIPELINE_STATE_FILENAME
        )
        assert state_path.exists(), "Pipeline state file should exist"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        edgecase_phase = next(
            (p for p in state["phases"] if p["name"] == "edgecase"), None,
        )
        assert edgecase_phase is not None, "edgecase phase should exist"
        assert edgecase_phase["status"] == "complete"


class TestEdgeCasesErrorPaths:
    """Tests for edge-cases error handling."""

    def test_missing_manifest_exits_one(
        self, tmp_path: Path, monkeypatch: object,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(edge_cases, [ "ledger-service"])
        assert result.exit_code == 1
        assert "manifest" in result.output.lower()

    def test_unknown_service_exits_one(
        self, tmp_path: Path, monkeypatch: object,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(edge_cases, [ "nonexistent-service"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
