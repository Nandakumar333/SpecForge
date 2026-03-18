"""Codebuddy agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class CodebuddyPlugin(SingleFileAgentPlugin):
    """Generates CODEBUDDY.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "codebuddy"
        self._file_path = "CODEBUDDY.md"
        self._template_name = "generic.md.j2"
