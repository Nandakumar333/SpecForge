"""E2E integration test: modular-monolith pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write a modular-monolith manifest with 3 modules (2+1+2 features)."""
    manifest = {
        "schema_version": "1.0",
        "architecture": "modular-monolith",
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login and sessions", "priority": "P0",
             "category": "foundation", "service": "auth-module"},
            {"id": "002", "name": "passwords", "display_name": "Password Management",
             "description": "Password reset", "priority": "P1",
             "category": "foundation", "service": "auth-module"},
            {"id": "003", "name": "payments", "display_name": "Payments",
             "description": "Payment processing", "priority": "P1",
             "category": "core", "service": "payments-module"},
            {"id": "004", "name": "reports", "display_name": "Reports",
             "description": "Financial reports", "priority": "P2",
             "category": "supporting", "service": "reporting-module"},
            {"id": "005", "name": "dashboards", "display_name": "Dashboards",
             "description": "Dashboard views", "priority": "P2",
             "category": "supporting", "service": "reporting-module"},
        ],
        "services": [
            {"name": "Auth Module", "slug": "auth-module",
             "features": ["001", "002"], "rationale": "Auth",
             "communication": []},
            {"name": "Payments Module", "slug": "payments-module",
             "features": ["003"], "rationale": "Payments",
             "communication": []},
            {"name": "Reporting Module", "slug": "reporting-module",
             "features": ["004", "005"], "rationale": "Reporting",
             "communication": []},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class TestModularMonolithE2E:
    def test_all_artifacts_generated(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["specify", "payments-module"])
        assert result.exit_code == 0, result.output
        out = tmp_path / ".specforge" / "features" / "payments-module"
        for artifact in ["spec.md", "research.md", "data-model.md",
                         "edge-cases.md", "plan.md", "checklist.md", "tasks.md"]:
            assert (out / artifact).exists(), f"Missing {artifact}"

    def test_no_contracts_dir(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        contracts = tmp_path / ".specforge" / "features" / "payments-module" / "contracts"
        assert not contracts.exists()

    def test_plan_has_boundary_enforcement(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        plan = tmp_path / ".specforge" / "features" / "payments-module" / "plan.md"
        content = plan.read_text(encoding="utf-8")
        assert "Module Boundary Enforcement" in content

    def test_checklist_no_cross_module_db(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        checklist = tmp_path / ".specforge" / "features" / "payments-module" / "checklist.md"
        content = checklist.read_text(encoding="utf-8")
        assert "cross-module" in content.lower()

    def test_edge_cases_interface_violation(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        ec = tmp_path / ".specforge" / "features" / "payments-module" / "edge-cases.md"
        content = ec.read_text(encoding="utf-8")
        assert "Interface Contract Violation" in content

    def test_datamodel_strict_boundaries(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        dm = tmp_path / ".specforge" / "features" / "payments-module" / "data-model.md"
        content = dm.read_text(encoding="utf-8")
        assert "Module Boundary Constraints" in content
        assert "cross-module" in content.lower()

    def test_shared_entities_created(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        assert (tmp_path / ".specforge" / "shared_entities.md").exists()

    def test_spec_has_module_interface(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "payments-module"])
        spec = tmp_path / ".specforge" / "features" / "payments-module" / "spec.md"
        content = spec.read_text(encoding="utf-8")
        assert "Module Interface Contract" in content
