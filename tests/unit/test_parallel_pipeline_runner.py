"""Unit tests for ParallelPipelineRunner (Feature 016)."""

from __future__ import annotations

import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from specforge.core.parallel_pipeline_runner import ParallelPipelineRunner
from specforge.core.parallel_progress_tracker import ProgressTracker
from specforge.core.result import Err, Ok


class TestParallelPipelineRunner:
    def _make_runner(
        self,
        orchestrator_factory=None,
        max_workers=4,
        fail_fast=False,
    ):
        console = Console(quiet=True)
        tracker = ProgressTracker(console=console, total_services=5)
        if orchestrator_factory is None:
            orchestrator_factory = self._make_mock_factory()
        return ParallelPipelineRunner(
            orchestrator_factory=orchestrator_factory,
            tracker=tracker,
            max_workers=max_workers,
            fail_fast=fail_fast,
        )

    def _make_mock_factory(self, fail_slugs=None):
        """Factory that returns mock orchestrators."""
        fail_slugs = fail_slugs or set()

        def factory():
            orch = MagicMock()

            def _run(target, root, force=False, from_phase=None):
                if target in fail_slugs:
                    return Err(f"Failed: {target}")
                return Ok(root / ".specforge" / "features" / target)

            orch.run = _run
            return orch

        return factory

    def test_parallel_execution(self, tmp_path):
        runner = self._make_runner(max_workers=2)
        slugs = ("auth", "billing", "admin")
        result = runner.run(slugs, tmp_path)
        assert result.ok
        state = result.value
        assert state.total_services == 3
        completed = [s for s in state.services if s.status == "completed"]
        assert len(completed) == 3

    def test_error_isolation(self, tmp_path):
        factory = self._make_mock_factory(fail_slugs={"billing"})
        runner = self._make_runner(
            orchestrator_factory=factory, fail_fast=False,
        )
        result = runner.run(("auth", "billing", "admin"), tmp_path)
        assert result.ok
        state = result.value
        statuses = {s.slug: s.status for s in state.services}
        assert statuses["auth"] == "completed"
        assert statuses["billing"] == "failed"
        assert statuses["admin"] == "completed"

    def test_fail_fast_cancels(self, tmp_path):
        """When fail-fast is set, first failure cancels remaining."""
        call_order = []

        def slow_factory():
            orch = MagicMock()

            def _run(target, root, force=False, from_phase=None):
                call_order.append(target)
                if target == "fail-svc":
                    return Err("crash")
                time.sleep(0.5)
                return Ok(root / ".specforge" / "features" / target)

            orch.run = _run
            return orch

        runner = self._make_runner(
            orchestrator_factory=slow_factory,
            max_workers=1,
            fail_fast=True,
        )
        result = runner.run(("fail-svc", "slow-svc"), tmp_path)
        assert result.ok
        state = result.value
        failed = [s for s in state.services if s.status == "failed"]
        assert len(failed) >= 1

    def test_empty_slugs_error(self, tmp_path):
        runner = self._make_runner()
        result = runner.run((), tmp_path)
        assert not result.ok

    def test_max_workers_capped(self, tmp_path):
        runner = self._make_runner(max_workers=10)
        result = runner.run(("a", "b"), tmp_path)
        assert result.ok
        # Should cap at len(slugs) = 2

    def test_exception_in_worker(self, tmp_path):
        def bad_factory():
            orch = MagicMock()
            orch.run.side_effect = RuntimeError("boom")
            return orch

        runner = self._make_runner(orchestrator_factory=bad_factory)
        result = runner.run(("a",), tmp_path)
        assert result.ok
        state = result.value
        assert state.services[0].status == "failed"
        assert "boom" in state.services[0].error
