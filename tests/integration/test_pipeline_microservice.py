"""E2E integration test: microservice pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write a microservice manifest with 2 services (3+2 features)."""
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


class TestMicroserviceE2E:
    def test_all_artifacts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "ledger-service"])
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "ledger-service"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"

    def test_contracts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        contracts = tmp_path / ".specforge" / "features" / "ledger-service" / "contracts"
        assert contracts.is_dir()
        assert (contracts / "api-spec.json").exists()
        data = json.loads((contracts / "api-spec.json").read_text(encoding="utf-8"))
        assert data["service"] == "ledger-service"
        assert data["stub"] is False

    def test_stub_contracts_for_dependencies(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        stub = (tmp_path / ".specforge" / "features"
                / "identity-service" / "contracts" / "api-spec.stub.json")
        assert stub.exists()
        data = json.loads(stub.read_text(encoding="utf-8"))
        assert data["stub"] is True
        assert data["service"] == "identity-service"

    def test_spec_has_service_dependencies(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        spec = (tmp_path / ".specforge" / "features"
                / "ledger-service" / "spec.md")
        content = spec.read_text(encoding="utf-8")
        assert "Service Dependencies" in content
        assert "identity-service" in content.lower() or "Identity Service" in content

    def test_plan_has_deployment_sections(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        plan = (tmp_path / ".specforge" / "features"
                / "ledger-service" / "plan.md")
        content = plan.read_text(encoding="utf-8")
        assert "Containerization" in content
        assert "Health Checks" in content
        assert "Circuit Breakers" in content

    def test_datamodel_no_cross_service_entities(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        dm = (tmp_path / ".specforge" / "features"
              / "ledger-service" / "data-model.md")
        content = dm.read_text(encoding="utf-8")
        assert "API Contract References" in content
        assert "Shared Entities" not in content

    def test_edge_cases_distributed(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        ec = (tmp_path / ".specforge" / "features"
              / "ledger-service" / "edge-cases.md")
        content = ec.read_text(encoding="utf-8")
        # Enriched format uses category titles; fallback uses adapter names
        has_enriched = "Service Unavailability" in content
        has_fallback = "Service Down" in content
        assert has_enriched or has_fallback

    def test_no_shared_entities_for_microservice(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "ledger-service"])
        assert not (tmp_path / ".specforge" / "shared_entities.md").exists()
