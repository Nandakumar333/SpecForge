"""Unit tests for PipelineOrchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.result import Ok
from specforge.core.spec_pipeline import PipelineOrchestrator


def _write_manifest(tmp_path: Path, arch: str = "microservice") -> None:
    """Write a test manifest to tmp_path."""
    manifest = {
        "schema_version": "1.0",
        "architecture": arch,
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {
                "id": "001", "name": "auth", "display_name": "Authentication",
                "description": "User login", "priority": "P0",
                "category": "foundation", "service": "identity-service",
            },
            {
                "id": "002", "name": "accounts", "display_name": "Accounts",
                "description": "Account tracking", "priority": "P1",
                "category": "core", "service": "ledger-service",
            },
        ],
        "services": [
            {
                "name": "Identity Service", "slug": "identity-service",
                "features": ["001"], "rationale": "Auth",
                "communication": [],
            },
            {
                "name": "Ledger Service", "slug": "ledger-service",
                "features": ["002"], "rationale": "Finance",
                "communication": [
                    {"target": "identity-service", "pattern": "sync-rest",
                     "required": True, "description": "Auth"},
                ],
            },
        ],
        "events": [],
    }
    manifest_dir = tmp_path / ".specforge"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def _make_orchestrator() -> PipelineOrchestrator:
    """Create orchestrator with mock renderer/registry."""
    renderer = MagicMock()
    renderer.render.return_value = Ok("# Generated content")
    registry = MagicMock()
    return PipelineOrchestrator(
        renderer=renderer,
        registry=registry,
    )


class TestPipelineOrchestrator:
    def test_run_generates_all_artifacts(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        result = orch.run("identity-service", tmp_path)
        assert result.ok
        out_dir = tmp_path / ".specforge" / "features" / "identity-service"
        assert (out_dir / "spec.md").exists()
        assert (out_dir / "research.md").exists()
        assert (out_dir / "data-model.md").exists()
        assert (out_dir / "edge-cases.md").exists()
        assert (out_dir / "plan.md").exists()
        assert (out_dir / "checklist.md").exists()
        assert (out_dir / "tasks.md").exists()

    def test_run_skips_completed_phases(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        # First run
        orch.run("identity-service", tmp_path)
        # Second run — should skip all
        orch2 = _make_orchestrator()
        result = orch2.run("identity-service", tmp_path)
        assert result.ok
        # Renderer should not be called on second run (all skipped)
        assert orch2._renderer.render.call_count == 0

    def test_run_force_regenerates(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        orch.run("identity-service", tmp_path)
        orch2 = _make_orchestrator()
        result = orch2.run("identity-service", tmp_path, force=True)
        assert result.ok
        assert orch2._renderer.render.call_count == 7

    def test_run_with_feature_number(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        result = orch.run("001", tmp_path)
        assert result.ok
        out_dir = tmp_path / ".specforge" / "features" / "identity-service"
        assert (out_dir / "spec.md").exists()

    def test_run_unknown_target_errors(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        result = orch.run("nonexistent", tmp_path)
        assert not result.ok

    def test_run_missing_manifest_errors(self, tmp_path: Path) -> None:
        orch = _make_orchestrator()
        result = orch.run("test", tmp_path)
        assert not result.ok

    def test_lock_prevents_concurrent(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        # Create a lock manually
        out_dir = tmp_path / ".specforge" / "features" / "identity-service"
        out_dir.mkdir(parents=True, exist_ok=True)
        lock_path = out_dir / ".pipeline-lock"
        lock_path.write_text(
            json.dumps({
                "service_slug": "identity-service",
                "pid": 99999,
                "timestamp": "2099-01-01T00:00:00+00:00",
            }),
            encoding="utf-8",
        )
        result = orch.run("identity-service", tmp_path)
        assert not result.ok
        assert "lock" in result.error.lower()

    def test_state_saved_after_each_phase(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        orch.run("identity-service", tmp_path)
        state_path = (
            tmp_path / ".specforge" / "features"
            / "identity-service" / ".pipeline-state.json"
        )
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        for phase in data["phases"]:
            assert phase["status"] == "complete"

    def test_from_phase_skips_earlier(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        orch.run("identity-service", tmp_path)
        orch2 = _make_orchestrator()
        result = orch2.run(
            "identity-service", tmp_path, from_phase="plan"
        )
        assert result.ok
        # Should render only plan, checklist, tasks (3 phases)
        assert orch2._renderer.render.call_count == 3


class TestStubContractGeneration:
    """T038: Tests for stub contract generation."""

    def test_stub_generated_for_unspecified_dependency(
        self, tmp_path: Path
    ) -> None:
        """Stub generated when dependent service has no contracts/."""
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        result = orch.run("ledger-service", tmp_path)
        assert result.ok
        stub_path = (
            tmp_path / ".specforge" / "features"
            / "identity-service" / "contracts" / "api-spec.stub.json"
        )
        assert stub_path.exists()
        data = json.loads(stub_path.read_text(encoding="utf-8"))
        assert data["stub"] is True
        assert data["service"] == "identity-service"
        assert data["generated_by"] == "ledger-service"
        assert len(data["endpoints"]) > 0

    def test_stub_not_generated_when_real_contract_exists(
        self, tmp_path: Path
    ) -> None:
        """Stub not generated when real contract already exists."""
        _write_manifest(tmp_path)
        # Create a real contract for identity-service
        contracts_dir = (
            tmp_path / ".specforge" / "features"
            / "identity-service" / "contracts"
        )
        contracts_dir.mkdir(parents=True, exist_ok=True)
        real_contract = {
            "service": "identity-service",
            "stub": False,
            "endpoints": [{"method": "GET", "path": "/users/{id}"}],
        }
        (contracts_dir / "api-spec.json").write_text(
            json.dumps(real_contract), encoding="utf-8"
        )
        orch = _make_orchestrator()
        result = orch.run("ledger-service", tmp_path)
        assert result.ok
        # Stub should NOT be generated
        assert not (contracts_dir / "api-spec.stub.json").exists()

    def test_api_spec_generated_for_microservice(
        self, tmp_path: Path
    ) -> None:
        """api-spec.json generated for the service itself."""
        _write_manifest(tmp_path)
        orch = _make_orchestrator()
        result = orch.run("ledger-service", tmp_path)
        assert result.ok
        spec_path = (
            tmp_path / ".specforge" / "features"
            / "ledger-service" / "contracts" / "api-spec.json"
        )
        assert spec_path.exists()
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        assert data["service"] == "ledger-service"
        assert data["stub"] is False

    def test_no_contracts_for_monolith(self, tmp_path: Path) -> None:
        """Monolith architecture should not generate contracts/."""
        _write_manifest(tmp_path, arch="monolithic")
        orch = _make_orchestrator()
        result = orch.run("ledger-service", tmp_path)
        assert result.ok
        contracts_dir = (
            tmp_path / ".specforge" / "features"
            / "ledger-service" / "contracts"
        )
        assert not contracts_dir.exists()
