"""Tabnine agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class TabninePlugin(SingleFileAgentPlugin):
    """Generates TABNINE.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "tabnine"
        self._file_path = "TABNINE.md"
        self._template_name = "generic.md.j2"
