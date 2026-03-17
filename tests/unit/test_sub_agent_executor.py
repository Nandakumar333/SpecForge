"""Unit tests for sub_agent_executor.py — main orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _scaffold_project(
    tmp_path: Path,
    slug: str = "identity-service",
    arch: str = "microservice",
    deps: list[dict] | None = None,
) -> Path:
    """Create a minimal project structure for executor tests."""
    specforge_dir = tmp_path / ".specforge"
    specforge_dir.mkdir(parents=True)

    # Manifest
    manifest = {
        "schema_version": "1.0",
        "project_name": "test-project",
        "project_description": "Test",
        "domain": "finance",
        "architecture": arch,
        "services": [
            {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "features": ["001"],
                "communication": deps or [],
            },
        ],
        "features": [{"id": "001", "name": "Core", "priority": "P1", "category": "core"}],
        "events": [],
    }
    (specforge_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )

    # Service spec artifacts
    feature_dir = specforge_dir / "features" / slug
    feature_dir.mkdir(parents=True)
    for fname in ("spec.md", "plan.md", "data-model.md", "edge-cases.md"):
        (feature_dir / fname).write_text(f"# {fname} for {slug}")
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Create model in src/models/user.py\n"
        "- [ ] T002 Create service in src/services/user_service.py\n"
        "- [ ] T003 Create controller in src/controllers/user_controller.py\n"
    )

    # Init git repo
    import os
    os.system(f'cd /d "{tmp_path}" && git init -q && git config user.email "t@t" && git config user.name "t" && git add . && git commit -q -m "init"')

    return tmp_path


class TestSubAgentExecutorValidation:
    """SubAgentExecutor validates prerequisites."""

    def test_missing_spec_artifacts_returns_err(self, tmp_path: Path) -> None:
        from specforge.core.sub_agent_executor import SubAgentExecutor

        # Scaffold without spec artifacts
        specforge_dir = tmp_path / ".specforge"
        specforge_dir.mkdir(parents=True)
        manifest = {"schema_version": "1.0", "architecture": "microservice", "services": [{"slug": "svc", "name": "Svc", "features": [], "communication": []}], "features": [], "events": [], "project_name": "t", "project_description": "t", "domain": "t"}
        (specforge_dir / "manifest.json").write_text(json.dumps(manifest))

        executor = SubAgentExecutor(
            context_builder=MagicMock(),
            task_runner=MagicMock(),
            quality_checker_factory=MagicMock(),
            auto_fix_loop=None,
            docker_manager=None,
            project_root=tmp_path,
        )
        result = executor.execute("svc", "prompt-display")
        assert not result.ok

    def test_locked_service_returns_err(self, tmp_path: Path) -> None:
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)
        # Create a lock file
        lock_dir = project / ".specforge" / "features" / "identity-service"
        (lock_dir / ".execution-lock").write_text('{"pid": 99999, "timestamp": "2026-01-01"}')

        executor = SubAgentExecutor(
            context_builder=MagicMock(),
            task_runner=MagicMock(),
            quality_checker_factory=MagicMock(),
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        result = executor.execute("identity-service", "prompt-display")
        assert not result.ok


class TestSubAgentExecutorExecution:
    """SubAgentExecutor processes tasks in order."""

    def test_processes_tasks_in_order(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)

        mock_ctx_builder = MagicMock()
        mock_ctx_builder.build.return_value = MagicMock(ok=True, value=MagicMock())

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(ok=True, value=[])

        mock_qc = MagicMock()
        mock_qc.check.return_value = MagicMock(
            ok=True,
            value=QualityCheckResult(
                passed=True, build_output="", lint_output="", test_output="",
            ),
        )
        mock_qc_factory = MagicMock(return_value=mock_qc)

        executor = SubAgentExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        result = executor.execute("identity-service", "prompt-display")
        assert result.ok
        # Runner should be called for each task
        assert mock_runner.run.call_count == 3

    def test_commits_on_quality_pass(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)

        mock_ctx_builder = MagicMock()
        mock_ctx_builder.build.return_value = MagicMock(ok=True, value=MagicMock())

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(ok=True, value=[project / "src" / "test.py"])

        mock_qc = MagicMock()
        mock_qc.check.return_value = MagicMock(
            ok=True,
            value=QualityCheckResult(
                passed=True, build_output="", lint_output="", test_output="",
            ),
        )
        mock_qc_factory = MagicMock(return_value=mock_qc)

        executor = SubAgentExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        result = executor.execute("identity-service", "prompt-display")
        assert result.ok
        # Verify state shows tasks completed
        state = result.value
        completed = [t for t in state.tasks if t.status == "completed"]
        assert len(completed) == 3

    def test_saves_state_after_each_task(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)

        mock_ctx_builder = MagicMock()
        mock_ctx_builder.build.return_value = MagicMock(ok=True, value=MagicMock())

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(ok=True, value=[])

        mock_qc = MagicMock()
        mock_qc.check.return_value = MagicMock(
            ok=True,
            value=QualityCheckResult(
                passed=True, build_output="", lint_output="", test_output="",
            ),
        )
        mock_qc_factory = MagicMock(return_value=mock_qc)

        executor = SubAgentExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        executor.execute("identity-service", "prompt-display")

        # State file should exist
        state_path = project / ".specforge" / "features" / "identity-service" / ".execution-state.json"
        assert state_path.exists()


class TestSubAgentExecutorResume:
    """Resume capability tests."""

    def test_resume_loads_existing_state(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_completed,
            save_state,
        )
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)
        feature_dir = project / ".specforge" / "features" / "identity-service"
        state_path = feature_dir / ".execution-state.json"

        # Pre-create state with T001 completed
        state = create_initial_state(
            "identity-service", "microservice", "prompt-display",
            ("T001", "T002", "T003"),
        )
        state = mark_task_completed(state, "T001", "abc123")
        save_state(state_path, state)

        mock_ctx_builder = MagicMock()
        mock_ctx_builder.build.return_value = MagicMock(ok=True, value=MagicMock())
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(ok=True, value=[])

        executor = SubAgentExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=MagicMock(return_value=MagicMock(check=MagicMock())),
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        result = executor.execute("identity-service", "prompt-display", resume=True)
        assert result.ok
        # Should only process T002, T003 (T001 already completed)
        assert mock_runner.run.call_count == 2

    def test_resume_resets_in_progress_to_pending(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_in_progress,
            save_state,
        )
        from specforge.core.sub_agent_executor import SubAgentExecutor

        project = _scaffold_project(tmp_path)
        feature_dir = project / ".specforge" / "features" / "identity-service"
        state_path = feature_dir / ".execution-state.json"

        # Pre-create state with T001 in_progress (simulating crash)
        state = create_initial_state(
            "identity-service", "microservice", "prompt-display",
            ("T001", "T002", "T003"),
        )
        state = mark_task_in_progress(state, "T001")
        save_state(state_path, state)

        mock_ctx_builder = MagicMock()
        mock_ctx_builder.build.return_value = MagicMock(ok=True, value=MagicMock())
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(ok=True, value=[])

        executor = SubAgentExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=MagicMock(return_value=MagicMock(check=MagicMock())),
            auto_fix_loop=None,
            docker_manager=None,
            project_root=project,
        )
        result = executor.execute("identity-service", "prompt-display", resume=True)
        assert result.ok
        # All 3 tasks should run (T001 was reset from in_progress to pending)
        assert mock_runner.run.call_count == 3
