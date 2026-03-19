"""Cursor agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class CursorPlugin(SingleFileAgentPlugin):
    """Generates .cursorrules governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "cursor"
        self._file_path = ".cursorrules"
        self._template_name = "cursor.rules.j2"

    @property
    def commands_dir(self) -> str:
        return ".cursor/commands"
