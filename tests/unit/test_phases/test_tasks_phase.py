"""Unit tests for TasksPhase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    MonolithAdapter,
)
from specforge.core.phases.tasks_phase import TasksPhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="test", service_name="Test", architecture=arch,
        project_description="Test", domain="test",
        features=(FeatureInfo("001", "a", "A", "Desc", "P0", "core"),),
        dependencies=(), events=(), output_dir=tmp_path,
    )


class TestTasksPhase:
    def test_microservice_has_container_tasks(self, tmp_path: Path) -> None:
        phase = TasksPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        names = [t["name"] for t in ctx["adapter_tasks"]]
        assert any("container" in n.lower() for n in names)

    def test_monolith_no_container_tasks(self, tmp_path: Path) -> None:
        phase = TasksPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        names = [t["name"] for t in ctx["adapter_tasks"]]
        assert not any("container" in n.lower() for n in names)

    def test_run_writes_artifact(self, tmp_path: Path) -> None:
        phase = TasksPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Tasks")
        result = phase.run(
            _ctx(tmp_path), MicroserviceAdapter(), renderer, MagicMock(), {}
        )
        assert result.ok
        assert (tmp_path / "tasks.md").exists()
