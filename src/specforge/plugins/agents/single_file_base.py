"""Base class for agents that produce a single config file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specforge.plugins.agents.base import AgentPlugin


class SingleFileAgentPlugin(AgentPlugin):
    """Base for agents that produce a single config file."""

    def __init__(self) -> None:
        self._file_path: str = ""
        self._template_name: str = ""
        self._agent_id: str = ""

    def agent_name(self) -> str:
        return self._agent_id

    def config_files(self) -> list[str]:
        return [self._file_path]

    def generate_config(
        self, target_dir: Path, context: dict[str, Any]
    ) -> list[Path]:
        output_path = target_dir / self._file_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._render_template(context)
        output_path.write_text(content, encoding="utf-8")
        return [output_path]

    def _render_template(self, context: dict[str, Any]) -> str:
        from jinja2 import Environment, PackageLoader

        env = Environment(
            loader=PackageLoader("specforge", "templates/base/agents"),
            keep_trailing_newline=True,
        )
        template = env.get_template(self._template_name)
        return template.render(**context)
