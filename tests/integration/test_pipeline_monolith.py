"""E2E integration test: monolith pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write a monolithic manifest with 3 modules."""
    manifest = {
        "schema_version": "1.0",
        "architecture": "monolithic",
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login and sessions", "priority": "P0",
             "category": "foundation", "service": "auth-module"},
            {"id": "002", "name": "accounts", "display_name": "Accounts",
             "description": "Account tracking", "priority": "P1",
             "category": "core", "service": "accounts-module"},
            {"id": "003", "name": "transactions", "display_name": "Transactions",
             "description": "Transaction processing", "priority": "P1",
             "category": "core", "service": "transactions-module"},
        ],
        "services": [
            {"name": "Auth Module", "slug": "auth-module",
             "features": ["001"], "rationale": "Auth",
             "communication": []},
            {"name": "Accounts Module", "slug": "accounts-module",
             "features": ["002"], "rationale": "Finance",
             "communication": []},
            {"name": "Transactions Module", "slug": "transactions-module",
             "features": ["003"], "rationale": "Finance",
             "communication": []},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class TestMonolithE2E:
    def test_all_artifacts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "auth-module"])
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "auth-module"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"

    def test_no_contracts_dir(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        contracts = tmp_path / ".specforge" / "features" / "auth-module" / "contracts"
        assert not contracts.exists()

    def test_plan_references_shared_infrastructure(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        plan = tmp_path / ".specforge" / "features" / "auth-module" / "plan.md"
        content = plan.read_text(encoding="utf-8")
        assert "Shared Database" in content
        assert "Shared Auth Middleware" in content

    def test_datamodel_references_shared_entities(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        dm = tmp_path / ".specforge" / "features" / "auth-module" / "data-model.md"
        content = dm.read_text(encoding="utf-8")
        assert "shared_entities.md" in content

    def test_shared_entities_created(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        assert (tmp_path / ".specforge" / "shared_entities.md").exists()

    def test_spec_no_service_dependencies(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        spec = tmp_path / ".specforge" / "features" / "auth-module" / "spec.md"
        content = spec.read_text(encoding="utf-8")
        assert "Service Dependencies" not in content

    def test_edge_cases_module_boundary(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        ec = tmp_path / ".specforge" / "features" / "auth-module" / "edge-cases.md"
        content = ec.read_text(encoding="utf-8")
        # Enriched format uses category titles; fallback uses adapter names
        has_enriched = "Data Boundary" in content or "Concurrency" in content
        has_fallback = "Module Boundary Violation" in content
        assert has_enriched or has_fallback

    def test_plan_no_docker(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "auth-module"])
        plan = tmp_path / ".specforge" / "features" / "auth-module" / "plan.md"
        content = plan.read_text(encoding="utf-8")
        assert "Containerization" not in content
        assert "Circuit Breakers" not in content
