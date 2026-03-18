"""Qwen agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class QwenPlugin(SingleFileAgentPlugin):
    """Generates QWEN.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "qwen"
        self._file_path = "QWEN.md"
        self._template_name = "generic.md.j2"
