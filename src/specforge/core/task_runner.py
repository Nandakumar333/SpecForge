"""TaskRunner — executes a single task (Mode A display, Mode B agent call)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from specforge.core.executor_models import ExecutionMode, ImplementPrompt
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


class TaskRunner:
    """Executes a single task in the chosen mode."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def run(
        self,
        prompt: ImplementPrompt,
        mode: ExecutionMode,
    ) -> Result[list[Path], str]:
        """Execute a task. Returns list of changed files."""
        if mode == "prompt-display":
            return self._run_mode_a(prompt)
        return Err(f"Mode '{mode}' not yet implemented")

    def _run_mode_a(self, prompt: ImplementPrompt) -> Result[list[Path], str]:
        """Mode A: display prompt, wait for user confirmation."""
        _display_prompt(prompt)
        answer = _wait_for_confirmation()

        if answer == "y":
            changed = _get_changed_files(self._root)
            return Ok(changed)
        if answer == "skip":
            return Ok([])
        return Err("User indicated task not complete")


def _display_prompt(prompt: ImplementPrompt) -> None:
    """Display the implementation prompt with Rich formatting."""
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        content = (
            f"**Task**: {prompt.task_description}\n\n"
            f"**Files**: {', '.join(prompt.file_hints) or 'N/A'}\n\n"
            f"---\n\n{prompt.system_context}"
        )
        if prompt.dependency_context:
            content += f"\n\n**Dependencies**:\n{prompt.dependency_context}"
        console.print(Panel(content, title="Implementation Prompt"))
    except ImportError:
        print(f"\n=== Task: {prompt.task_description} ===")
        print(f"Files: {', '.join(prompt.file_hints) or 'N/A'}")
        print(prompt.system_context)


def _wait_for_confirmation() -> str:
    """Prompt user for task completion status."""
    try:
        from rich.prompt import Prompt

        return Prompt.ask(
            "Task complete?",
            choices=["y", "n", "skip"],
            default="y",
        )
    except ImportError:
        return input("Task complete? [y/n/skip]: ").strip().lower()


def _get_changed_files(project_root: Path) -> list[Path]:
    """Detect changed files via git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        files: list[Path] = []
        for line in result.stdout.strip().splitlines():
            if len(line) > 3:
                path = line[3:].strip()
                files.append(project_root / path)
        return files
    except (subprocess.TimeoutExpired, OSError):
        return []
