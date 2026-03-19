"""Bob agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class BobPlugin(SingleFileAgentPlugin):
    """Generates .bob/rules.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "bob"
        self._file_path = ".bob/rules.md"
        self._template_name = "generic.md.j2"

    @property
    def commands_dir(self) -> str:
        return ".bob/commands"
