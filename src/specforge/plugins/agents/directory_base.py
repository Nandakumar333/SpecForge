"""Base class for agents that produce files in a directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specforge.plugins.agents.base import AgentPlugin


class DirectoryAgentPlugin(AgentPlugin):
    """Base for agents that produce files in a directory."""

    def __init__(self) -> None:
        self._agent_id: str = ""
        self._dir_path: str = ""
        self._file_specs: list[tuple[str, str]] = []

    def agent_name(self) -> str:
        return self._agent_id

    @property
    def commands_dir(self) -> str:
        """Derive commands dir from agent's config directory."""
        return f"{self._dir_path}/commands"

    def config_files(self) -> list[str]:
        return [f"{self._dir_path}/{spec[0]}" for spec in self._file_specs]

    def generate_config(
        self, target_dir: Path, context: dict[str, Any]
    ) -> list[Path]:
        written: list[Path] = []
        for rel_path, template_name in self._file_specs:
            output_path = target_dir / self._dir_path / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._render_template(template_name, context)
            output_path.write_text(content, encoding="utf-8")
            written.append(output_path)
        return written

    def _render_template(
        self, template_name: str, context: dict[str, Any]
    ) -> str:
        from jinja2 import Environment, PackageLoader

        env = Environment(
            loader=PackageLoader("specforge", "templates/base/agents"),
            keep_trailing_newline=True,
        )
        template = env.get_template(template_name)
        return template.render(**context)
