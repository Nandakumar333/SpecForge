"""Integration tests for specforge specify command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.cli.pipeline_status_cmd import pipeline_status


def _write_manifest(tmp_path: Path, arch: str = "microservice") -> None:
    manifest = {
        "schema_version": "1.0",
        "architecture": arch,
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login", "priority": "P0", "category": "foundation",
             "service": "identity-service"},
            {"id": "002", "name": "accounts", "display_name": "Accounts",
             "description": "Account tracking", "priority": "P1", "category": "core",
             "service": "ledger-service"},
            {"id": "003", "name": "transactions", "display_name": "Transactions",
             "description": "Txn tracking", "priority": "P1", "category": "core",
             "service": "ledger-service"},
        ],
        "services": [
            {"name": "Identity Service", "slug": "identity-service",
             "features": ["001"], "rationale": "Auth",
             "communication": []},
            {"name": "Ledger Service", "slug": "ledger-service",
             "features": ["002", "003"], "rationale": "Finance",
             "communication": [
                 {"target": "identity-service", "pattern": "sync-rest",
                  "required": True, "description": "Auth"}]},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class TestSpecifyCommand:
    def test_specify_by_slug(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "identity-service"])
        assert result.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "identity-service"
        assert (out / "spec.md").exists()
        assert (out / "tasks.md").exists()

    def test_specify_by_feature_number(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "002"])
        assert result.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "ledger-service"
        assert (out / "spec.md").exists()

    def test_specify_unknown_service(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "nonexistent"])
        assert result.exit_code == 1

    def test_specify_force(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "identity-service"])
        result = runner.invoke(cli, ["specify", "identity-service", "--force"])
        assert result.exit_code == 0

    def test_specify_missing_manifest(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "test"])
        assert result.exit_code == 1

    def test_multi_feature_service(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "ledger-service"])
        assert result.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "ledger-service"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"


class TestSpecifyArchitectures:
    def test_monolith(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, "monolithic")
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "identity-service"])
        assert result.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "identity-service"
        assert (out / "spec.md").exists()
        # Monolith should create shared_entities.md
        assert (tmp_path / ".specforge" / "shared_entities.md").exists()

    def test_modular_monolith(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, "modular-monolith")
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "ledger-service"])
        assert result.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "ledger-service"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"
        assert (tmp_path / ".specforge" / "shared_entities.md").exists()


class TestPipelineStatusCommand:
    def test_no_state(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(pipeline_status, [])
        assert result.exit_code == 0
        assert "No pipeline state" in result.output

    def test_after_pipeline_run(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "identity-service"])
        result = runner.invoke(pipeline_status, [])
        assert result.exit_code == 0
        assert "identity-service" in result.output

    def test_specific_service(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "identity-service"])
        result = runner.invoke(pipeline_status, ["identity-service"])
        assert result.exit_code == 0
        assert "complete" in result.output
