"""Kimi agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class KimiPlugin(SingleFileAgentPlugin):
    """Generates KIMI.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "kimi"
        self._file_path = "KIMI.md"
        self._template_name = "generic.md.j2"
