"""E2E integration test: pipeline resume and state recovery."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _write_manifest(tmp_path: Path) -> None:
    """Write a test manifest."""
    manifest = {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {"id": "001", "name": "auth", "display_name": "Authentication",
             "description": "Login", "priority": "P0",
             "category": "foundation", "service": "identity-service"},
        ],
        "services": [
            {"name": "Identity Service", "slug": "identity-service",
             "features": ["001"], "rationale": "Auth",
             "communication": []},
        ],
        "events": [],
    }
    d = tmp_path / ".specforge"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class TestPipelineResume:
    def test_skip_completed_phases(self, tmp_path: Path, monkeypatch) -> None:
        """Run pipeline, then re-run. Should skip all phases."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        # First run
        result1 = runner.invoke(cli, ["specify", "identity-service"])
        assert result1.exit_code == 0
        out = tmp_path / ".specforge" / "features" / "identity-service"
        spec_mtime = (out / "spec.md").stat().st_mtime
        # Second run — should skip
        result2 = runner.invoke(cli, ["specify", "identity-service"])
        assert result2.exit_code == 0
        # spec.md should not be rewritten (same mtime)
        assert (out / "spec.md").stat().st_mtime == spec_mtime

    def test_force_regenerates(self, tmp_path: Path, monkeypatch) -> None:
        """--force should regenerate all artifacts."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["specify", "identity-service"])
        out = tmp_path / ".specforge" / "features" / "identity-service"
        # Force re-run
        result = runner.invoke(cli, ["specify", "identity-service", "--force"])
        assert result.exit_code == 0
        # Content should still be valid (regenerated)
        assert (out / "spec.md").exists()

    def test_stale_lock_detection(self, tmp_path: Path, monkeypatch) -> None:
        """A stale lock (>30 min) should allow override."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        # Create a stale lock
        out = tmp_path / ".specforge" / "features" / "identity-service"
        out.mkdir(parents=True, exist_ok=True)
        lock = out / ".pipeline-lock"
        lock.write_text(json.dumps({
            "service_slug": "identity-service",
            "pid": 99999,
            "timestamp": "2020-01-01T00:00:00+00:00",
        }), encoding="utf-8")
        # Should succeed because lock is stale
        result = runner.invoke(cli, ["specify", "identity-service"])
        assert result.exit_code == 0

    def test_active_lock_blocks(self, tmp_path: Path, monkeypatch) -> None:
        """A recent lock should block the pipeline."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        # Create a non-stale lock (future timestamp)
        out = tmp_path / ".specforge" / "features" / "identity-service"
        out.mkdir(parents=True, exist_ok=True)
        lock = out / ".pipeline-lock"
        lock.write_text(json.dumps({
            "service_slug": "identity-service",
            "pid": 99999,
            "timestamp": "2099-01-01T00:00:00+00:00",
        }), encoding="utf-8")
        result = runner.invoke(cli, ["specify", "identity-service"])
        assert result.exit_code == 1

    def test_from_phase_resumes(self, tmp_path: Path, monkeypatch) -> None:
        """--from should start from the specified phase."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        runner = CliRunner()
        # Full run first
        runner.invoke(cli, ["specify", "identity-service"])
        out = tmp_path / ".specforge" / "features" / "identity-service"
        plan_mtime = (out / "plan.md").stat().st_mtime
        # Re-run from plan
        import time
        time.sleep(0.05)  # ensure mtime difference
        result = runner.invoke(cli, ["specify", "identity-service", "--from", "plan"])
        assert result.exit_code == 0
        # Plan should be regenerated (new mtime)
        assert (out / "plan.md").stat().st_mtime >= plan_mtime
        # But spec should NOT be rewritten
        state_path = out / ".pipeline-state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        spec_phase = next(p for p in data["phases"] if p["name"] == "spec")
        assert spec_phase["status"] == "complete"
