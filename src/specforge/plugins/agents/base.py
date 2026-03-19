"""Abstract base class for agent plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AgentPlugin(ABC):
    """Base class for agent-specific configuration generators.

    Concrete implementations (claude.py, copilot.py, etc.) are
    deferred to Feature 003 (plan.md D-02).
    """

    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent identifier (e.g., 'claude')."""

    @abstractmethod
    def generate_config(
        self,
        target_dir: Path,
        context: dict[str, Any],
    ) -> list[Path]:
        """Generate agent-specific config files. Return written paths."""

    @abstractmethod
    def config_files(self) -> list[str]:
        """Return list of config file names this agent produces."""

    @property
    def commands_dir(self) -> str:
        """Agent-native commands directory path relative to project root."""
        return ".specforge/commands"

    @property
    def command_format(self) -> str:
        """Output format for command files: 'markdown' or 'toml'."""
        return "markdown"

    @property
    def command_extension(self) -> str:
        """File extension for command files (including dot)."""
        return ".md"

    @property
    def args_placeholder(self) -> str:
        """Agent-native argument placeholder string."""
        return "$ARGUMENTS"
