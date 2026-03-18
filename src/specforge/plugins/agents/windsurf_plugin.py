"""Windsurf agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class WindsurfPlugin(SingleFileAgentPlugin):
    """Generates .windsurfrules governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "windsurf"
        self._file_path = ".windsurfrules"
        self._template_name = "windsurf.rules.j2"
