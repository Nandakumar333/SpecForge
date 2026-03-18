"""OpenAI Codex agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class CodexPlugin(SingleFileAgentPlugin):
    """Generates AGENTS.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "codex"
        self._file_path = "AGENTS.md"
        self._template_name = "codex.md.j2"
