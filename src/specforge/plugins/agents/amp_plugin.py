"""Amp agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class AmpPlugin(SingleFileAgentPlugin):
    """Generates AMP.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "amp"
        self._file_path = "AMP.md"
        self._template_name = "generic.md.j2"
