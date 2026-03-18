"""Opencode agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class OpencodePlugin(SingleFileAgentPlugin):
    """Generates OPENCODE.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "opencode"
        self._file_path = "OPENCODE.md"
        self._template_name = "generic.md.j2"
