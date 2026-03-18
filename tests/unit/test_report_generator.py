"""Unit tests for report_generator (Feature 012 — Phase 6)."""

from __future__ import annotations

import json
from pathlib import Path

from specforge.core.report_generator import (
    generate_json_report,
    generate_markdown_report,
)
from specforge.core.status_models import (
    DependencyGraph,
    LifecyclePhases,
    PhaseProgressRecord,
    ProjectStatusSnapshot,
    QualitySummaryRecord,
    ServiceStatusRecord,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _make_quality(**overrides: object) -> QualitySummaryRecord:
    """Build a QualitySummaryRecord with sane defaults."""
    defaults: dict = {
        "services_total": 0,
        "services_complete": 0,
        "services_in_progress": 0,
        "services_planning": 0,
        "services_not_started": 0,
        "services_blocked": 0,
        "services_failed": 0,
        "services_unknown": 0,
        "tasks_total": 0,
        "tasks_complete": 0,
        "tasks_failed": 0,
    }
    defaults.update(overrides)
    return QualitySummaryRecord(**defaults)


def _make_snapshot(**overrides: object) -> ProjectStatusSnapshot:
    """Build a ProjectStatusSnapshot with minimal defaults."""
    defaults: dict = {
        "project_name": "TestProject",
        "architecture": "microservice",
        "services": (),
        "phases": (),
        "quality": _make_quality(),
        "graph": DependencyGraph(nodes=()),
        "warnings": (),
        "timestamp": "2026-03-18T00:00:00Z",
        "has_failures": False,
    }
    defaults.update(overrides)
    return ProjectStatusSnapshot(**defaults)


def _make_service(**overrides: object) -> ServiceStatusRecord:
    """Build a ServiceStatusRecord with defaults."""
    defaults: dict = {
        "slug": "auth-service",
        "display_name": "Auth Service",
        "features": ("user-auth",),
        "lifecycle": LifecyclePhases(),
        "overall_status": "NOT_STARTED",
    }
    defaults.update(overrides)
    return ServiceStatusRecord(**defaults)


def _load_json(path: Path) -> dict:
    """Read a JSON file and return the parsed dict."""
    return json.loads(path.read_text(encoding="utf-8"))


# ── TestGenerateJsonReport ────────────────────────────────────────────


class TestGenerateJsonReport:
    """Tests for generate_json_report."""

    def test_generate_json_valid_output(self, tmp_path: Path) -> None:
        """Valid JSON with correct top-level keys."""
        snap = _make_snapshot()
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        for key in (
            "schema_version",
            "project_name",
            "architecture",
            "timestamp",
            "has_failures",
            "services",
            "phases",
            "quality",
            "warnings",
        ):
            assert key in data

    def test_generate_json_not_started_service_null_fields(
        self,
        tmp_path: Path,
    ) -> None:
        """NOT_STARTED service has all lifecycle fields as null."""
        svc = _make_service(overall_status="NOT_STARTED")
        snap = _make_snapshot(services=(svc,))
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        lc = data["services"][0]["lifecycle"]
        for field in (
            "spec",
            "plan",
            "tasks",
            "impl_percent",
            "tests_passed",
            "tests_total",
            "docker",
            "boundary_compliance",
        ):
            assert lc[field] is None

    def test_generate_json_complete_service_all_fields_populated(
        self,
        tmp_path: Path,
    ) -> None:
        """COMPLETE service has all lifecycle fields populated."""
        lifecycle = LifecyclePhases(
            spec="DONE",
            plan="DONE",
            tasks="DONE",
            impl_percent=100,
            tests_passed=42,
            tests_total=42,
            docker="OK",
            boundary_compliance="OK",
        )
        svc = _make_service(
            overall_status="COMPLETE",
            lifecycle=lifecycle,
            phase_index=0,
        )
        snap = _make_snapshot(services=(svc,))
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        lc = data["services"][0]["lifecycle"]
        assert lc["spec"] == "DONE"
        assert lc["impl_percent"] == 100
        assert lc["tests_passed"] == 42
        assert lc["docker"] == "OK"

    def test_generate_json_creates_reports_dir(self, tmp_path: Path) -> None:
        """Output dir is created if it doesn't exist."""
        out = tmp_path / "nested" / "reports"
        result = generate_json_report(_make_snapshot(), out)
        assert result.ok
        assert result.value.exists()

    def test_generate_json_overwrites_existing(self, tmp_path: Path) -> None:
        """Existing file is replaced on second call."""
        snap1 = _make_snapshot(project_name="First")
        snap2 = _make_snapshot(project_name="Second")
        generate_json_report(snap1, tmp_path)
        result = generate_json_report(snap2, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        assert data["project_name"] == "Second"

    def test_generate_json_includes_timestamp(self, tmp_path: Path) -> None:
        """Timestamp from snapshot is preserved."""
        ts = "2026-06-15T12:30:00Z"
        snap = _make_snapshot(timestamp=ts)
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        assert data["timestamp"] == ts

    def test_generate_json_includes_warnings_array(
        self,
        tmp_path: Path,
    ) -> None:
        """Warnings tuple is serialized as a JSON array."""
        snap = _make_snapshot(warnings=("Missing state file", "Stale data"))
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        assert data["warnings"] == ["Missing state file", "Stale data"]

    def test_generate_json_phases_ordered_by_index(
        self,
        tmp_path: Path,
    ) -> None:
        """Phases are ordered by index in output."""
        p1 = PhaseProgressRecord(
            index=1,
            label="Phase 2",
            services=("b",),
            completion_percent=50.0,
            status="in-progress",
        )
        p0 = PhaseProgressRecord(
            index=0,
            label="Phase 1",
            services=("a",),
            completion_percent=100.0,
            status="complete",
        )
        snap = _make_snapshot(phases=(p1, p0))
        result = generate_json_report(snap, tmp_path)
        assert result.ok
        data = _load_json(result.value)
        indices = [p["index"] for p in data["phases"]]
        assert indices == [0, 1]


# ── TestGenerateMarkdownReport ────────────────────────────────────────


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report."""

    def _gen(self, snap: ProjectStatusSnapshot, out: Path) -> str:
        """Generate markdown and return content string."""
        result = generate_markdown_report(snap, out)
        assert result.ok
        return result.value.read_text(encoding="utf-8")

    def test_generate_markdown_contains_architecture_badge(
        self,
        tmp_path: Path,
    ) -> None:
        """Markdown includes the architecture badge in uppercase."""
        snap = _make_snapshot(architecture="microservice")
        md = self._gen(snap, tmp_path)
        assert "**Architecture**: MICROSERVICE" in md

    def test_generate_markdown_contains_service_table(
        self,
        tmp_path: Path,
    ) -> None:
        """Markdown includes a pipe-delimited service table."""
        svc = _make_service(
            slug="api-gw",
            display_name="API Gateway",
            overall_status="IN_PROGRESS",
            lifecycle=LifecyclePhases(spec="DONE", plan="WIP"),
        )
        snap = _make_snapshot(services=(svc,))
        md = self._gen(snap, tmp_path)
        assert "| API Gateway" in md
        assert "IN_PROGRESS" in md

    def test_generate_markdown_contains_phase_progress(
        self,
        tmp_path: Path,
    ) -> None:
        """Markdown includes text-based progress bars."""
        phase = PhaseProgressRecord(
            index=0,
            label="Foundation",
            services=("svc-a",),
            completion_percent=80.0,
            status="in-progress",
        )
        snap = _make_snapshot(phases=(phase,))
        md = self._gen(snap, tmp_path)
        assert "Foundation" in md
        assert "80" in md

    def test_generate_markdown_contains_quality_summary(
        self,
        tmp_path: Path,
    ) -> None:
        """Markdown includes quality metrics."""
        q = _make_quality(
            services_total=5,
            services_complete=3,
            tasks_total=20,
            tasks_complete=15,
        )
        snap = _make_snapshot(quality=q)
        md = self._gen(snap, tmp_path)
        assert "5" in md
        assert "3" in md

    def test_generate_markdown_creates_reports_dir(
        self,
        tmp_path: Path,
    ) -> None:
        """Output dir is created if it doesn't exist."""
        out = tmp_path / "deep" / "dir"
        result = generate_markdown_report(_make_snapshot(), out)
        assert result.ok
        assert result.value.exists()

    def test_generate_markdown_includes_timestamp(
        self,
        tmp_path: Path,
    ) -> None:
        """Timestamp appears in the markdown footer."""
        ts = "2026-06-15T12:30:00Z"
        snap = _make_snapshot(timestamp=ts)
        md = self._gen(snap, tmp_path)
        assert ts in md
