"""GitHub Copilot agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.directory_base import DirectoryAgentPlugin


class CopilotPlugin(DirectoryAgentPlugin):
    """Generates .github/copilot-instructions.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "copilot"
        self._dir_path = ".github"
        self._file_specs = [
            ("copilot-instructions.md", "copilot-instructions.md.j2"),
        ]

    @property
    def commands_dir(self) -> str:
        return ".github/prompts"

    @property
    def command_extension(self) -> str:
        return ".prompt.md"
