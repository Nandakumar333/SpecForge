"""Roocode agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class RoocodePlugin(SingleFileAgentPlugin):
    """Generates .roo/rules.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "roocode"
        self._file_path = ".roo/rules.md"
        self._template_name = "generic.md.j2"

    @property
    def commands_dir(self) -> str:
        return ".roo/commands"
