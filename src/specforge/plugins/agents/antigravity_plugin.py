"""Antigravity agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class AntigravityPlugin(SingleFileAgentPlugin):
    """Generates .agy/rules.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "antigravity"
        self._file_path = ".agy/rules.md"
        self._template_name = "generic.md.j2"
