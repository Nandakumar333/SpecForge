"""Unit tests for StatusCollector (Feature 012 — Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path

from specforge.core.result import Err, Ok
from specforge.core.status_collector import (
    ManifestData,
    collect_project_status,
    load_manifest,
    read_orchestration_state,
    read_service_states,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _write_json(path: Path, data: dict) -> None:
    """Write a JSON file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _minimal_manifest(
    *,
    services: list[dict] | None = None,
    architecture: str = "microservice",
    features: list[dict] | None = None,
    project_name: str = "test-project",
) -> dict:
    """Build a valid manifest dict with sane defaults."""
    return {
        "schema_version": "1.0",
        "project_name": project_name,
        "architecture": architecture,
        "features": features or [],
        "services": services or [],
    }


def _setup_manifest(tmp_path: Path, manifest: dict) -> None:
    """Write manifest.json in the standard location."""
    _write_json(tmp_path / ".specforge" / "manifest.json", manifest)


def _pipeline_state(
    slug: str,
    phases: list[dict],
) -> dict:
    return {
        "service_slug": slug,
        "schema_version": "1.0",
        "phases": phases,
    }


def _execution_state(slug: str, tasks: list[dict]) -> dict:
    return {"service_slug": slug, "tasks": tasks}


def _quality_report(
    slug: str,
    passed: bool = True,
    check_results: list[dict] | None = None,
) -> dict:
    return {
        "service_slug": slug,
        "level": "service",
        "gate_result": {
            "passed": passed,
            "check_results": check_results or [],
        },
    }


# ── T005: Manifest reading tests ─────────────────────────────────────


class TestLoadManifest:
    def test_load_manifest_returns_service_list(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {
                    "slug": "auth-service",
                    "name": "Auth Service",
                    "features": ["F001"],
                    "communication": [],
                },
                {
                    "slug": "pay-service",
                    "name": "Payment Service",
                    "features": ["F002", "F003"],
                    "communication": [{"target": "auth-service"}],
                },
            ],
            features=[
                {"id": "F001", "name": "Authentication", "service": "auth-service"},
                {"id": "F002", "name": "Payment", "service": "pay-service"},
            ],
        )
        _setup_manifest(tmp_path, manifest)

        result = load_manifest(tmp_path)
        assert result.ok
        data: ManifestData = result.value
        assert data.architecture == "microservice"
        assert len(data.services) == 2
        assert data.services[0].slug == "auth-service"
        assert data.services[0].display_name == "Auth Service"
        assert data.services[0].features == ("F001",)
        assert data.services[1].features == ("F002", "F003")
        assert len(data.communication) == 1
        assert data.communication[0].source == "pay-service"
        assert data.communication[0].target == "auth-service"

    def test_load_manifest_missing_file(self, tmp_path: Path) -> None:
        result = load_manifest(tmp_path)
        assert not result.ok
        assert "Manifest not found" in result.error

    def test_load_manifest_corrupt_json(self, tmp_path: Path) -> None:
        specforge_dir = tmp_path / ".specforge"
        specforge_dir.mkdir()
        (specforge_dir / "manifest.json").write_text("{invalid json!!}", encoding="utf-8")

        result = load_manifest(tmp_path)
        assert not result.ok
        assert "Failed to parse manifest" in result.error

    def test_load_manifest_empty_services(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(services=[])
        _setup_manifest(tmp_path, manifest)

        result = load_manifest(tmp_path)
        assert result.ok
        assert len(result.value.services) == 0

    def test_service_to_feature_mapping(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {
                    "slug": "planning-service",
                    "name": "Planning Service",
                    "features": ["004", "006", "007"],
                    "communication": [],
                },
            ],
        )
        _setup_manifest(tmp_path, manifest)

        result = load_manifest(tmp_path)
        assert result.ok
        svc = result.value.services[0]
        assert svc.slug == "planning-service"
        assert svc.features == ("004", "006", "007")


# ── T006: Per-service state file reading tests ───────────────────────


class TestReadServiceStates:
    def test_read_pipeline_state_complete(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        pipeline = _pipeline_state("auth-service", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "complete"},
            {"name": "tasks", "status": "complete"},
        ])
        _write_json(svc_dir / ".pipeline-state.json", pipeline)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.pipeline, Ok)
        phases = raw.pipeline.value["phases"]
        assert all(p["status"] == "complete" for p in phases)

    def test_read_pipeline_state_partial(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        pipeline = _pipeline_state("auth-service", [
            {"name": "spec", "status": "complete"},
            {"name": "research", "status": "in-progress"},
            {"name": "plan", "status": "pending"},
        ])
        _write_json(svc_dir / ".pipeline-state.json", pipeline)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.pipeline, Ok)
        statuses = [p["status"] for p in raw.pipeline.value["phases"]]
        assert statuses == ["complete", "in-progress", "pending"]

    def test_read_pipeline_state_missing(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        (features_dir / "auth-service").mkdir(parents=True)

        raw = read_service_states(features_dir, "auth-service")
        assert raw.pipeline is None
        assert raw.execution is None
        assert raw.quality is None

    def test_read_pipeline_state_corrupt(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)
        (svc_dir / ".pipeline-state.json").write_text(
            "NOT VALID JSON", encoding="utf-8",
        )

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.pipeline, Err)
        assert "Corrupt file" in raw.pipeline.error

    def test_read_execution_state(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        execution = _execution_state("auth-service", [
            {"task_id": "T001", "status": "completed"},
            {"task_id": "T002", "status": "completed"},
            {"task_id": "T003", "status": "in-progress"},
            {"task_id": "T004", "status": "pending"},
        ])
        _write_json(svc_dir / ".execution-state.json", execution)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.execution, Ok)
        tasks = raw.execution.value["tasks"]
        assert len(tasks) == 4

    def test_read_execution_state_no_tasks(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        execution = _execution_state("auth-service", [])
        _write_json(svc_dir / ".execution-state.json", execution)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.execution, Ok)
        assert raw.execution.value["tasks"] == []

    def test_read_execution_state_missing(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        (features_dir / "auth-service").mkdir(parents=True)

        raw = read_service_states(features_dir, "auth-service")
        assert raw.execution is None

    def test_read_quality_report_extracts_test_counts(
        self, tmp_path: Path,
    ) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        quality = _quality_report(
            "auth-service",
            passed=True,
            check_results=[
                {
                    "checker_name": "pytest",
                    "passed": True,
                    "category": "coverage",
                    "output": "Tests: 45 passed, 0 failed",
                },
            ],
        )
        _write_json(svc_dir / ".quality-report.json", quality)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.quality, Ok)
        checks = raw.quality.value["gate_result"]["check_results"]
        assert checks[0]["output"] == "Tests: 45 passed, 0 failed"

    def test_read_quality_report_missing(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        (features_dir / "auth-service").mkdir(parents=True)

        raw = read_service_states(features_dir, "auth-service")
        assert raw.quality is None

    def test_read_quality_report_docker_check(self, tmp_path: Path) -> None:
        features_dir = tmp_path / ".specforge" / "features"
        svc_dir = features_dir / "auth-service"
        svc_dir.mkdir(parents=True)

        quality = _quality_report(
            "auth-service",
            passed=True,
            check_results=[
                {
                    "checker_name": "docker_checker",
                    "passed": True,
                    "category": "docker",
                    "output": "Docker build successful",
                },
                {
                    "checker_name": "docker_checker",
                    "passed": False,
                    "category": "docker",
                    "output": "Docker build failed",
                },
            ],
        )
        _write_json(svc_dir / ".quality-report.json", quality)

        raw = read_service_states(features_dir, "auth-service")
        assert isinstance(raw.quality, Ok)
        checks = raw.quality.value["gate_result"]["check_results"]
        assert checks[0]["checker_name"] == "docker_checker"
        assert checks[0]["passed"] is True
        assert checks[1]["passed"] is False


# ── T008: Integration-level collector tests ──────────────────────────


class TestCollectProjectStatus:
    def test_collect_empty_project(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {"slug": "auth-service", "name": "Auth", "features": ["F001"], "communication": []},
                {"slug": "pay-service", "name": "Pay", "features": ["F002"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        (tmp_path / ".specforge" / "features" / "auth-service").mkdir(parents=True)
        (tmp_path / ".specforge" / "features" / "pay-service").mkdir(parents=True)

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        assert len(snap.services) == 2
        assert all(s.overall_status == "NOT_STARTED" for s in snap.services)

    def test_collect_partial_project(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {"slug": "svc-a", "name": "A", "features": ["F001"], "communication": []},
                {"slug": "svc-b", "name": "B", "features": ["F002"], "communication": []},
                {"slug": "svc-c", "name": "C", "features": ["F003"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        features_dir = tmp_path / ".specforge" / "features"

        # svc-a: planning (pipeline in-progress, no execution)
        svc_a = features_dir / "svc-a"
        svc_a.mkdir(parents=True)
        _write_json(svc_a / ".pipeline-state.json", _pipeline_state("svc-a", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "in-progress"},
        ]))

        # svc-b: in-progress (has execution tasks)
        svc_b = features_dir / "svc-b"
        svc_b.mkdir(parents=True)
        _write_json(svc_b / ".pipeline-state.json", _pipeline_state("svc-b", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "complete"},
            {"name": "tasks", "status": "complete"},
        ]))
        _write_json(svc_b / ".execution-state.json", _execution_state("svc-b", [
            {"task_id": "T001", "status": "completed"},
            {"task_id": "T002", "status": "in-progress"},
        ]))

        # svc-c: not started
        (features_dir / "svc-c").mkdir(parents=True)

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        statuses = {s.slug: s.overall_status for s in snap.services}
        assert statuses["svc-a"] == "PLANNING"
        assert statuses["svc-b"] == "IN_PROGRESS"
        assert statuses["svc-c"] == "NOT_STARTED"

    def test_collect_complete_project(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {"slug": "auth", "name": "Auth", "features": ["F001"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        svc_dir = tmp_path / ".specforge" / "features" / "auth"
        svc_dir.mkdir(parents=True)

        _write_json(svc_dir / ".pipeline-state.json", _pipeline_state("auth", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "complete"},
            {"name": "tasks", "status": "complete"},
        ]))
        _write_json(svc_dir / ".execution-state.json", _execution_state("auth", [
            {"task_id": "T001", "status": "completed"},
            {"task_id": "T002", "status": "completed"},
        ]))
        _write_json(svc_dir / ".quality-report.json", _quality_report(
            "auth",
            passed=True,
            check_results=[
                {"checker_name": "pytest", "passed": True, "category": "coverage", "output": "Tests: 10 passed, 0 failed"},
                {"checker_name": "docker_checker", "passed": True, "category": "docker", "output": "OK"},
            ],
        ))

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        assert snap.services[0].overall_status == "COMPLETE"
        assert snap.has_failures is False
        assert snap.services[0].lifecycle.spec == "DONE"
        assert snap.services[0].lifecycle.impl_percent == 100

    def test_collect_corrupt_state_file(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {"slug": "good", "name": "Good", "features": ["F001"], "communication": []},
                {"slug": "bad", "name": "Bad", "features": ["F002"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        features_dir = tmp_path / ".specforge" / "features"

        # good service: planning
        good_dir = features_dir / "good"
        good_dir.mkdir(parents=True)
        _write_json(good_dir / ".pipeline-state.json", _pipeline_state("good", [
            {"name": "spec", "status": "complete"},
        ]))

        # bad service: corrupt pipeline file
        bad_dir = features_dir / "bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / ".pipeline-state.json").write_text("CORRUPT!", encoding="utf-8")

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        statuses = {s.slug: s.overall_status for s in snap.services}
        assert statuses["good"] == "PLANNING"
        assert statuses["bad"] == "UNKNOWN"
        assert len(snap.warnings) > 0
        assert any("bad" in w for w in snap.warnings)

    def test_collect_no_manifest(self, tmp_path: Path) -> None:
        result = collect_project_status(tmp_path)
        assert not result.ok
        assert "Manifest not found" in result.error

    def test_collect_single_service_project(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            architecture="monolithic",
            services=[
                {"slug": "monolith", "name": "Monolith", "features": ["F001"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        svc_dir = tmp_path / ".specforge" / "features" / "monolith"
        svc_dir.mkdir(parents=True)
        _write_json(svc_dir / ".pipeline-state.json", _pipeline_state("monolith", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "in-progress"},
        ]))

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        assert snap.architecture == "monolithic"
        assert len(snap.services) == 1
        assert snap.services[0].overall_status == "PLANNING"

    def test_collect_large_project_15_services(self, tmp_path: Path) -> None:
        services = []
        for i in range(15):
            services.append({
                "slug": f"svc-{i:02d}",
                "name": f"Service {i}",
                "features": [f"F{i:03d}"],
                "communication": [],
            })
        manifest = _minimal_manifest(services=services)
        _setup_manifest(tmp_path, manifest)
        features_dir = tmp_path / ".specforge" / "features"

        for i in range(15):
            slug = f"svc-{i:02d}"
            svc_dir = features_dir / slug
            svc_dir.mkdir(parents=True)
            if i < 5:
                # Complete
                _write_json(svc_dir / ".pipeline-state.json", _pipeline_state(slug, [
                    {"name": "spec", "status": "complete"},
                    {"name": "plan", "status": "complete"},
                    {"name": "tasks", "status": "complete"},
                ]))
                _write_json(svc_dir / ".execution-state.json", _execution_state(slug, [
                    {"task_id": "T001", "status": "completed"},
                ]))
                _write_json(svc_dir / ".quality-report.json", _quality_report(slug, passed=True))
            elif i < 10:
                # Planning
                _write_json(svc_dir / ".pipeline-state.json", _pipeline_state(slug, [
                    {"name": "spec", "status": "complete"},
                    {"name": "plan", "status": "in-progress"},
                ]))
            # else: not started (no state files)

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        assert len(snap.services) == 15
        statuses = [s.overall_status for s in snap.services]
        assert statuses.count("COMPLETE") == 5
        assert statuses.count("PLANNING") == 5
        assert statuses.count("NOT_STARTED") == 5

    def test_collect_execution_state_zero_tasks(self, tmp_path: Path) -> None:
        manifest = _minimal_manifest(
            services=[
                {"slug": "svc", "name": "Svc", "features": ["F001"], "communication": []},
            ],
        )
        _setup_manifest(tmp_path, manifest)
        svc_dir = tmp_path / ".specforge" / "features" / "svc"
        svc_dir.mkdir(parents=True)

        _write_json(svc_dir / ".pipeline-state.json", _pipeline_state("svc", [
            {"name": "spec", "status": "complete"},
            {"name": "plan", "status": "complete"},
            {"name": "tasks", "status": "complete"},
        ]))
        # Execution state with empty tasks list — should not cause division by zero
        _write_json(svc_dir / ".execution-state.json", _execution_state("svc", []))

        result = collect_project_status(tmp_path)
        assert result.ok
        snap = result.value
        # Has execution state (even empty) → IN_PROGRESS? No — empty tasks means
        # _has_execution_activity returns False since len(tasks)==0.
        # All pipeline phases complete + execution empty tasks + no quality →
        # _is_all_complete checks pipeline (all complete ✓), execution (Ok but empty tasks → True), quality (None → no gate check → True)
        # So this should be COMPLETE.
        svc_record = snap.services[0]
        assert svc_record.lifecycle.impl_percent == 0


class TestReadOrchestrationState:
    def test_read_orchestration_state_exists(self, tmp_path: Path) -> None:
        orch = {
            "architecture": "microservice",
            "status": "in-progress",
            "phases": [
                {"index": 0, "status": "completed", "services": [{"slug": "auth", "status": "completed"}]},
            ],
        }
        _write_json(tmp_path / ".specforge" / "orchestration-state.json", orch)

        result = read_orchestration_state(tmp_path)
        assert isinstance(result, Ok)
        assert result.value["status"] == "in-progress"

    def test_read_orchestration_state_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".specforge").mkdir(parents=True)
        result = read_orchestration_state(tmp_path)
        assert result is None

    def test_read_orchestration_state_corrupt(self, tmp_path: Path) -> None:
        specforge_dir = tmp_path / ".specforge"
        specforge_dir.mkdir(parents=True)
        (specforge_dir / "orchestration-state.json").write_text("BAD", encoding="utf-8")

        result = read_orchestration_state(tmp_path)
        assert isinstance(result, Err)
