"""CommandRegistrar — renders and writes pipeline-stage command files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader

from specforge.core.config import COMMAND_PREFIX, PIPELINE_STAGES
from specforge.core.result import Err, Ok, Result
from specforge.plugins.agents.base import AgentPlugin


@dataclass(frozen=True)
class CommandFile:
    """A single command file to be written."""

    stage: str
    filename: str
    relative_path: Path
    content: str


class CommandRegistrar:
    """Renders and writes pipeline-stage command files for a selected agent."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("specforge", "templates/base/commands"),
            keep_trailing_newline=True,
        )

    def build_command_files(
        self,
        agent: AgentPlugin,
        context: dict[str, Any],
    ) -> list[CommandFile]:
        """Build the list of command files without writing to disk."""
        files: list[CommandFile] = []
        for stage in PIPELINE_STAGES:
            template_name = f"{COMMAND_PREFIX}.{stage}.md.j2"
            render_ctx = {**context, "arguments": agent.args_placeholder}
            if agent.command_format == "toml":
                content = self._render_toml(template_name, render_ctx)
            else:
                content = self._render_markdown(template_name, render_ctx)
            filename = f"{COMMAND_PREFIX}.{stage}{agent.command_extension}"
            rel_path = Path(agent.commands_dir) / filename
            files.append(CommandFile(
                stage=stage,
                filename=filename,
                relative_path=rel_path,
                content=content,
            ))
        return files

    def register_commands(
        self,
        agent: AgentPlugin,
        target_dir: Path,
        context: dict[str, Any],
        force: bool = False,
    ) -> Result[list[Path], str]:
        """Render and write all pipeline-stage command files."""
        try:
            command_files = self.build_command_files(agent, context)
        except Exception as exc:
            return Err(f"Command template rendering failed: {exc}")

        written: list[Path] = []
        try:
            for cf in command_files:
                out_path = target_dir / cf.relative_path
                if force and out_path.exists():
                    continue
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(cf.content, encoding="utf-8")
                written.append(out_path)
        except PermissionError as exc:
            return Err(f"Permission denied writing to {exc}")
        except OSError as exc:
            return Err(f"Failed to write command file: {exc}")

        return Ok(written)

    def _render_markdown(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a command template as Markdown."""
        template = self._env.get_template(template_name)
        return template.render(**context)

    def _render_toml(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a command template, then wrap in TOML format."""
        md_content = self._render_markdown(template_name, context)
        description = self._extract_description(md_content)
        prompt_body = self._strip_frontmatter(md_content)
        return (
            f'description = "{description}"\n'
            f"\n"
            f"# Source: specforge\n"
            f"\n"
            f'prompt = """\n'
            f"{prompt_body}"
            f'"""\n'
        )

    @staticmethod
    def _extract_description(md_content: str) -> str:
        """Extract description from YAML frontmatter."""
        match = re.search(
            r"^---\s*\n.*?description:\s*(.+?)\s*\n.*?---",
            md_content,
            re.DOTALL,
        )
        return match.group(1) if match else "SpecForge pipeline command"

    @staticmethod
    def _strip_frontmatter(md_content: str) -> str:
        """Remove YAML frontmatter from Markdown content."""
        stripped = re.sub(
            r"^---\s*\n.*?---\s*\n",
            "",
            md_content,
            count=1,
            flags=re.DOTALL,
        )
        return stripped.lstrip("\n")
