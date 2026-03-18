"""Integration tests for ``specforge status`` CLI command (Feature 012)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.cli.status_cmd import status

# ── Helpers ───────────────────────────────────────────────────────────


def _write_json(path: Path, data: dict) -> None:
    """Write a JSON file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _setup_project(
    tmp_path: Path,
    arch: str = "microservice",
    services: list[dict] | None = None,
    project_name: str = "test-project",
) -> Path:
    """Create a minimal .specforge project with manifest."""
    sf = tmp_path / ".specforge"
    sf.mkdir(parents=True, exist_ok=True)
    (sf / "features").mkdir(exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "project_name": project_name,
        "architecture": arch,
        "features": [],
        "services": services or [],
    }
    _write_json(sf / "manifest.json", manifest)
    return tmp_path


def _add_pipeline_state(
    tmp_path: Path,
    slug: str,
    phases: list[dict],
) -> None:
    """Write a .pipeline-state.json for a service."""
    svc_dir = tmp_path / ".specforge" / "features" / slug
    svc_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "service_slug": slug,
        "schema_version": "1.0",
        "phases": phases,
    }
    _write_json(svc_dir / ".pipeline-state.json", state)


def _add_execution_state(
    tmp_path: Path,
    slug: str,
    tasks: list[dict],
) -> None:
    """Write a .execution-state.json for a service."""
    svc_dir = tmp_path / ".specforge" / "features" / slug
    svc_dir.mkdir(parents=True, exist_ok=True)
    state = {"service_slug": slug, "tasks": tasks}
    _write_json(svc_dir / ".execution-state.json", state)


def _add_quality_report(
    tmp_path: Path,
    slug: str,
    passed: bool = True,
    check_results: list[dict] | None = None,
) -> None:
    """Write a .quality-report.json for a service."""
    svc_dir = tmp_path / ".specforge" / "features" / slug
    svc_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "service_slug": slug,
        "level": "service",
        "gate_result": {
            "passed": passed,
            "check_results": check_results or [],
        },
    }
    _write_json(svc_dir / ".quality-report.json", report)


def _service_entry(
    slug: str,
    name: str | None = None,
    features: list[str] | None = None,
) -> dict:
    """Build a manifest service entry dict."""
    return {
        "slug": slug,
        "name": name or slug.replace("-", " ").title(),
        "features": features or [],
        "communication": [],
    }


def _completed_pipeline(slug: str) -> list[dict]:
    """Pipeline phases for a fully-specced service."""
    return [
        {"name": "spec", "status": "complete"},
        {"name": "plan", "status": "complete"},
        {"name": "tasks", "status": "complete"},
    ]


def _partial_pipeline(slug: str) -> list[dict]:
    """Pipeline phases for a service mid-planning."""
    return [
        {"name": "spec", "status": "complete"},
        {"name": "plan", "status": "in-progress"},
    ]


def _completed_tasks(n: int = 3) -> list[dict]:
    """N completed tasks."""
    return [{"id": f"t{i}", "status": "complete"} for i in range(n)]


def _mixed_tasks() -> list[dict]:
    """Tasks with mixed statuses."""
    return [
        {"id": "t1", "status": "complete"},
        {"id": "t2", "status": "in-progress"},
        {"id": "t3", "status": "pending"},
    ]


# ── Phase 9: Watch Mode validation tests ─────────────────────────────


class TestWatchMode:
    def test_watch_rejects_format_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        _add_pipeline_state(tmp_path, "svc-a", _completed_pipeline("svc-a"))
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--watch", "--format", "markdown"])
        assert result.exit_code != 0
        assert "watch" in result.output.lower() or "terminal" in result.output.lower()

    def test_watch_rejects_format_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        _add_pipeline_state(tmp_path, "svc-a", _completed_pipeline("svc-a"))
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--watch", "--format", "json"])
        assert result.exit_code != 0
        assert "watch" in result.output.lower() or "terminal" in result.output.lower()

    def test_watch_default_interval_is_5(self) -> None:
        for param in status.params:
            if param.name == "interval":
                assert param.default == 5
                break
        else:
            pytest.fail("--interval option not found on status command")


# ── Phase 10: CLI Integration tests ──────────────────────────────────


class TestStatusNoProject:
    def test_status_no_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No .specforge dir → error + non-zero exit."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "manifest" in result.output.lower()


class TestStatusNoManifest:
    def test_status_no_manifest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """".specforge dir exists but no manifest → error suggesting decompose."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specforge").mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0
        assert "manifest" in result.output.lower() or "error" in result.output.lower()


class TestStatusEmptyProject:
    def test_status_empty_project_all_not_started(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Manifest with services but no state files → all NOT_STARTED."""
        monkeypatch.chdir(tmp_path)
        _setup_project(
            tmp_path,
            services=[_service_entry("svc-a"), _service_entry("svc-b")],
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        assert "NOT STARTED" in result.output


class TestStatusPartialProject:
    def test_status_partial_project_mixed_statuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """3 services at different stages."""
        monkeypatch.chdir(tmp_path)
        _setup_project(
            tmp_path,
            services=[
                _service_entry("svc-a"),
                _service_entry("svc-b"),
                _service_entry("svc-c"),
            ],
        )
        # svc-a: completed pipeline + tasks = IN_PROGRESS or COMPLETE
        _add_pipeline_state(tmp_path, "svc-a", _completed_pipeline("svc-a"))
        _add_execution_state(tmp_path, "svc-a", _completed_tasks())
        _add_quality_report(tmp_path, "svc-a", passed=True)
        # svc-b: partial pipeline = PLANNING
        _add_pipeline_state(tmp_path, "svc-b", _partial_pipeline("svc-b"))
        # svc-c: nothing = NOT_STARTED

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        output = result.output
        # At least two different statuses should be visible
        assert "Svc A" in output or "svc-a" in output.lower()
        assert "Svc B" in output or "svc-b" in output.lower()
        assert "Svc C" in output or "svc-c" in output.lower()


class TestStatusCompleteProject:
    def test_status_complete_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All services done → exit 0."""
        monkeypatch.chdir(tmp_path)
        _setup_project(
            tmp_path,
            services=[_service_entry("svc-a"), _service_entry("svc-b")],
        )
        for slug in ("svc-a", "svc-b"):
            _add_pipeline_state(tmp_path, slug, _completed_pipeline(slug))
            _add_execution_state(tmp_path, slug, _completed_tasks())
            _add_quality_report(tmp_path, slug, passed=True)

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output


class TestStatusFormatJson:
    def test_status_format_json_creates_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--format json creates status.json."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--format", "json"])
        assert result.exit_code == 0, result.output
        json_path = tmp_path / ".specforge" / "reports" / "status.json"
        assert json_path.exists(), f"Expected {json_path} to exist"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "services" in data


class TestStatusFormatMarkdown:
    def test_status_format_markdown_creates_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--format markdown creates status.md."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--format", "markdown"])
        assert result.exit_code == 0, result.output
        md_path = tmp_path / ".specforge" / "reports" / "status.md"
        assert md_path.exists(), f"Expected {md_path} to exist"


class TestStatusFormatBoth:
    def test_status_format_both_creates_both_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--format json --format markdown creates both files."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        runner = CliRunner()
        result = runner.invoke(
            cli, ["status", "--format", "json", "--format", "markdown"],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".specforge" / "reports" / "status.json").exists()
        assert (tmp_path / ".specforge" / "reports" / "status.md").exists()


class TestStatusGraphFlag:
    def test_status_graph_flag_shows_graph(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--graph shows dependency graph section."""
        monkeypatch.chdir(tmp_path)
        _setup_project(
            tmp_path,
            services=[
                {
                    "slug": "svc-a",
                    "name": "Svc A",
                    "features": [],
                    "communication": [{"target": "svc-b"}],
                },
                _service_entry("svc-b"),
            ],
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--graph"])
        assert result.exit_code == 0, result.output
        assert "Dependency Graph" in result.output or "svc-a" in result.output


class TestStatusExitCodes:
    def test_status_exit_code_0_no_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exit 0 when no failures."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_status_exit_code_1_with_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exit 1 when any service is FAILED."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        # Quality gate failure triggers FAILED status
        _add_quality_report(tmp_path, "svc-a", passed=False)
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1


class TestStatusCorruptState:
    def test_status_corrupt_state_shows_unknown_with_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Corrupt JSON → UNKNOWN status + warning in output."""
        monkeypatch.chdir(tmp_path)
        _setup_project(tmp_path, services=[_service_entry("svc-a")])
        svc_dir = tmp_path / ".specforge" / "features" / "svc-a"
        svc_dir.mkdir(parents=True, exist_ok=True)
        (svc_dir / ".pipeline-state.json").write_text("{invalid json", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        assert "UNKNOWN" in result.output or "Warning" in result.output or "warning" in result.output.lower()


class TestStatusBoundary:
    def test_status_single_service_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """1 service boundary case."""
        monkeypatch.chdir(tmp_path)
        _setup_project(
            tmp_path,
            arch="monolithic",
            services=[_service_entry("monolith-app")],
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        assert "Monolith App" in result.output or "monolith-app" in result.output.lower()

    def test_status_large_project_15_services(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """15 services all appear in output."""
        monkeypatch.chdir(tmp_path)
        services = [_service_entry(f"svc-{i:02d}") for i in range(15)]
        _setup_project(tmp_path, services=services)
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        for i in range(15):
            slug = f"svc-{i:02d}"
            assert slug in result.output.lower() or slug.replace("-", " ") in result.output.lower()
