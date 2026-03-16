"""E2E integration test: single-feature service pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write a microservice manifest with 1 service, 1 feature."""
    manifest = {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Simple auth service",
        "domain": "auth",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login and sessions", "priority": "P0",
             "category": "foundation", "service": "auth-service"},
        ],
        "services": [
            {"name": "Auth Service", "slug": "auth-service",
             "features": ["001"], "rationale": "Auth",
             "communication": []},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class TestSingleFeatureE2E:
    def test_all_artifacts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "auth-service"])
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "auth-service"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"

    def test_spec_no_subsections(self, tmp_path: Path, monkeypatch) -> None:
        """Single feature should NOT have domain capability sub-sections."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-service"])
        spec = tmp_path / ".specforge" / "features" / "auth-service" / "spec.md"
        content = spec.read_text(encoding="utf-8")
        # With < 4 features, each feature is its own capability (no grouping)
        assert "Authentication" in content

    def test_minimal_data_model(self, tmp_path: Path, monkeypatch) -> None:
        """Single feature should have minimal data model."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-service"])
        dm = tmp_path / ".specforge" / "features" / "auth-service" / "data-model.md"
        content = dm.read_text(encoding="utf-8")
        assert "Authentication" in content

    def test_contracts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-service"])
        contracts = tmp_path / ".specforge" / "features" / "auth-service" / "contracts"
        assert contracts.is_dir()
        assert (contracts / "api-spec.json").exists()
