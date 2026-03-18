"""Pi agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class PiPlugin(SingleFileAgentPlugin):
    """Generates PI.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "pi"
        self._file_path = "PI.md"
        self._template_name = "generic.md.j2"
