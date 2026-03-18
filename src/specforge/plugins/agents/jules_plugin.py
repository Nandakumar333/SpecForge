"""Jules agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class JulesPlugin(SingleFileAgentPlugin):
    """Generates JULES.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "jules"
        self._file_path = "JULES.md"
        self._template_name = "generic.md.j2"
