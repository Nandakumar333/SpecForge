"""Fallback generic agent plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specforge.plugins.agents.base import AgentPlugin


class GenericPlugin(AgentPlugin):
    """Fallback agent plugin for unsupported agents."""

    def __init__(self, commands_dir: str = "commands") -> None:
        self._commands_dir = commands_dir

    def agent_name(self) -> str:
        return "generic"

    @property
    def commands_dir(self) -> str:
        return self._commands_dir

    def config_files(self) -> list[str]:
        return [f"{self._commands_dir}/rules.md"]

    def generate_config(
        self, target_dir: Path, context: dict[str, Any]
    ) -> list[Path]:
        output_path = target_dir / self._commands_dir / "rules.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        from jinja2 import Environment, PackageLoader

        env = Environment(
            loader=PackageLoader("specforge", "templates/base/agents"),
            keep_trailing_newline=True,
        )
        template = env.get_template("generic.md.j2")
        merged = {**context, "agent_name": "generic"}
        content = template.render(**merged)
        output_path.write_text(content, encoding="utf-8")
        return [output_path]
