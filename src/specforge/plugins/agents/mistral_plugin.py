"""Mistral agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class MistralPlugin(SingleFileAgentPlugin):
    """Generates MISTRAL.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "mistral"
        self._file_path = "MISTRAL.md"
        self._template_name = "generic.md.j2"
