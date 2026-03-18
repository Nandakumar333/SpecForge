"""Shai agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class ShaiPlugin(SingleFileAgentPlugin):
    """Generates SHAI.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "shai"
        self._file_path = "SHAI.md"
        self._template_name = "generic.md.j2"
