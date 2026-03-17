"""Unit tests for task_runner.py — Mode A (prompt-display)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTaskRunnerModeA:
    """TaskRunner.run() in prompt-display mode."""

    def test_renders_prompt_via_template(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(
            system_context="governance rules",
            task_description="Create User model",
            file_hints=("src/models/user.py",),
        )
        runner = TaskRunner(tmp_path)

        with patch("specforge.core.task_runner._display_prompt") as mock_display, \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="y"), \
             patch("specforge.core.task_runner._get_changed_files", return_value=[]):
            result = runner.run(prompt, "prompt-display")

        assert result.ok
        mock_display.assert_called_once()

    def test_user_yes_detects_changed_files(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(
            system_context="gov",
            task_description="Create model",
        )
        runner = TaskRunner(tmp_path)
        changed = [tmp_path / "src" / "model.py"]

        with patch("specforge.core.task_runner._display_prompt"), \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="y"), \
             patch("specforge.core.task_runner._get_changed_files", return_value=changed):
            result = runner.run(prompt, "prompt-display")

        assert result.ok
        assert result.value == changed

    def test_user_no_returns_err(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(
            system_context="gov",
            task_description="Create model",
        )
        runner = TaskRunner(tmp_path)

        with patch("specforge.core.task_runner._display_prompt"), \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="n"):
            result = runner.run(prompt, "prompt-display")

        assert not result.ok

    def test_user_skip_returns_ok_empty(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(
            system_context="gov",
            task_description="Create model",
        )
        runner = TaskRunner(tmp_path)

        with patch("specforge.core.task_runner._display_prompt"), \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="skip"):
            result = runner.run(prompt, "prompt-display")

        assert result.ok
        assert result.value == []


class TestTaskRunnerModeB:
    """TaskRunner.run() in agent-call mode."""

    def test_agent_call_sends_prompt_to_subprocess(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(
            system_context="gov rules",
            task_description="Create model",
            file_hints=("src/model.py",),
        )
        runner = TaskRunner(tmp_path)

        mock_result = MagicMock(returncode=0, stdout="done", stderr="")
        with patch("specforge.core.task_runner._detect_agent", return_value="claude"), \
             patch("specforge.core.task_runner.subprocess.run", return_value=mock_result), \
             patch("specforge.core.task_runner._get_changed_files", return_value=[tmp_path / "x.py"]):
            result = runner.run(prompt, "agent-call")

        assert result.ok
        assert len(result.value) == 1

    def test_agent_call_falls_back_to_mode_a_when_no_agent(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(system_context="gov", task_description="Create model")
        runner = TaskRunner(tmp_path)

        with patch("specforge.core.task_runner._detect_agent", return_value=None), \
             patch("specforge.core.task_runner._display_prompt"), \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="y"), \
             patch("specforge.core.task_runner._get_changed_files", return_value=[]):
            result = runner.run(prompt, "agent-call")

        assert result.ok

    def test_agent_call_retries_and_falls_back_after_failures(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import ImplementPrompt
        from specforge.core.task_runner import TaskRunner

        prompt = ImplementPrompt(system_context="gov", task_description="Create model")
        runner = TaskRunner(tmp_path)

        mock_fail = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("specforge.core.task_runner._detect_agent", return_value="claude"), \
             patch("specforge.core.task_runner.subprocess.run", return_value=mock_fail), \
             patch("specforge.core.task_runner.time.sleep"), \
             patch("specforge.core.task_runner._display_prompt"), \
             patch("specforge.core.task_runner._wait_for_confirmation", return_value="y"), \
             patch("specforge.core.task_runner._get_changed_files", return_value=[]):
            result = runner.run(prompt, "agent-call")

        assert result.ok  # fell back to Mode A
