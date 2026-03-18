"""Claude agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class ClaudePlugin(SingleFileAgentPlugin):
    """Generates CLAUDE.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "claude"
        self._file_path = "CLAUDE.md"
        self._template_name = "claude.md.j2"
