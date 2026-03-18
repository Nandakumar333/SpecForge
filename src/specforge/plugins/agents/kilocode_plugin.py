"""Kilocode agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class KilocodePlugin(SingleFileAgentPlugin):
    """Generates .kilocode/rules.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "kilocode"
        self._file_path = ".kilocode/rules.md"
        self._template_name = "generic.md.j2"
