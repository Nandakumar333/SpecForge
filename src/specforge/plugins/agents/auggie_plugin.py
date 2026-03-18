"""Auggie agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class AuggiePlugin(SingleFileAgentPlugin):
    """Generates AUGGIE.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "auggie"
        self._file_path = "AUGGIE.md"
        self._template_name = "generic.md.j2"
