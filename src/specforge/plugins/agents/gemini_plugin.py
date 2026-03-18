"""Google Gemini agent plugin."""

from __future__ import annotations

from specforge.plugins.agents.directory_base import DirectoryAgentPlugin


class GeminiPlugin(DirectoryAgentPlugin):
    """Generates .gemini/style-guide.md governance file."""

    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "gemini"
        self._dir_path = ".gemini"
        self._file_specs = [
            ("style-guide.md", "gemini-style-guide.md.j2"),
        ]
