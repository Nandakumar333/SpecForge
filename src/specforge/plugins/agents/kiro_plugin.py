"""Kiro agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.directory_base import DirectoryAgentPlugin


class KiroPlugin(DirectoryAgentPlugin):
    """Generates .kiro/rules.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "kiro"
        self._dir_path = ".kiro"
        self._file_specs = [
            ("rules.md", "kiro-rules.md.j2"),
        ]
