"""Unit tests for shared_infra_executor.py — cross-service infrastructure executor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _scaffold_infra_project(
    tmp_path: Path,
    arch: str = "microservice",
    *,
    include_tasks: bool = True,
    task_content: str | None = None,
) -> Path:
    """Create a minimal project structure for shared-infra executor tests."""
    specforge_dir = tmp_path / ".specforge"
    specforge_dir.mkdir(parents=True)

    manifest = {
        "schema_version": "1.0",
        "project_name": "test-project",
        "project_description": "Test project",
        "domain": "finance",
        "architecture": arch,
        "services": [],
        "features": [],
        "events": [],
    }
    (specforge_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )

    if include_tasks:
        infra_dir = specforge_dir / "features" / "cross-service-infra"
        infra_dir.mkdir(parents=True)
        content = task_content or (
            "- [ ] T001 Set up shared message broker config\n"
            "- [ ] T002 Create cross-service auth middleware\n"
        )
        (infra_dir / "tasks.md").write_text(content, encoding="utf-8")

    import os
    os.system(
        f'cd /d "{tmp_path}" && git init -q '
        f'&& git config user.email "t@t" && git config user.name "t" '
        f'&& git add . && git commit -q -m "init"'
    )

    return tmp_path


class TestSharedInfraExecutorValidation:
    """SharedInfraExecutor validates architecture before execution."""

    def test_execute_validates_architecture_rejects_monolithic(
        self, tmp_path: Path,
    ) -> None:
        from specforge.core.shared_infra_executor import SharedInfraExecutor

        project = _scaffold_infra_project(tmp_path, arch="monolithic")

        executor = SharedInfraExecutor(
            context_builder=MagicMock(),
            task_runner=MagicMock(),
            quality_checker_factory=MagicMock(),
            auto_fix_loop=None,
            project_root=project,
        )
        result = executor.execute("prompt-display")
        assert not result.ok
        assert "monolithic" in result.error.lower()

    def test_execute_accepts_microservice_architecture(
        self, tmp_path: Path,
    ) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.shared_infra_executor import SharedInfraExecutor

        project = _scaffold_infra_project(tmp_path, arch="microservice")

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

        executor = SharedInfraExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            project_root=project,
        )
        result = executor.execute("prompt-display")
        assert result.ok

    def test_execute_locates_infra_tasks(self, tmp_path: Path) -> None:
        from specforge.core.shared_infra_executor import SharedInfraExecutor

        project = _scaffold_infra_project(
            tmp_path, arch="microservice", include_tasks=False,
        )

        executor = SharedInfraExecutor(
            context_builder=MagicMock(),
            task_runner=MagicMock(),
            quality_checker_factory=MagicMock(),
            auto_fix_loop=None,
            project_root=project,
        )
        result = executor.execute("prompt-display")
        assert not result.ok
        assert "cross-service-infra" in result.error.lower() or "tasks.md" in result.error.lower()


class TestSharedInfraExecutorExecution:
    """SharedInfraExecutor processes infra tasks in order."""

    def test_execute_processes_infra_tasks(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.shared_infra_executor import SharedInfraExecutor

        project = _scaffold_infra_project(tmp_path, arch="microservice")

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

        executor = SharedInfraExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            project_root=project,
        )
        result = executor.execute("prompt-display")
        assert result.ok
        # Runner should be called once per task (2 tasks)
        assert mock_runner.run.call_count == 2

    def test_execute_marks_shared_infra_complete(
        self, tmp_path: Path,
    ) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.shared_infra_executor import SharedInfraExecutor

        project = _scaffold_infra_project(tmp_path, arch="microservice")

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

        executor = SharedInfraExecutor(
            context_builder=mock_ctx_builder,
            task_runner=mock_runner,
            quality_checker_factory=mock_qc_factory,
            auto_fix_loop=None,
            project_root=project,
        )
        result = executor.execute("prompt-display")
        assert result.ok
        assert result.value.shared_infra_complete is True
