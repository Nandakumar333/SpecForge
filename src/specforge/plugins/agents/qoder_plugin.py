"""Qoder agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class QoderPlugin(SingleFileAgentPlugin):
    """Generates QODER.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "qoder"
        self._file_path = "QODER.md"
        self._template_name = "generic.md.j2"
