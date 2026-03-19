# Contract: CommandRegistrar

**Feature**: 014-interactive-model-selection
**Type**: Internal Python service (core domain logic)

## Interface

```python
@dataclass(frozen=True)
class CommandFile:
    """A single command file to be written."""
    stage: str            # e.g., "decompose"
    filename: str         # e.g., "specforge.decompose.md"
    relative_path: Path   # e.g., Path(".claude/commands/specforge.decompose.md")
    content: str          # rendered template content


class CommandRegistrar:
    """Renders and writes pipeline-stage command files for a selected agent."""

    def __init__(self) -> None: ...

    def register_commands(
        self,
        agent: AgentPlugin,
        target_dir: Path,
        context: dict[str, Any],
        force: bool = False,
    ) -> Result[list[Path], str]:
        """Render and write all pipeline-stage command files.

        Args:
            agent: The selected agent plugin (provides commands_dir, format, etc.)
            target_dir: Project root directory
            context: Template context (project_name, stack, architecture, etc.)
            force: If True, skip existing files instead of overwriting

        Returns:
            Ok(list[Path]) — paths of written files
            Err(str) — error message on failure
        """

    def build_command_files(
        self,
        agent: AgentPlugin,
        context: dict[str, Any],
    ) -> list[CommandFile]:
        """Build the list of command files without writing.

        Used by dry-run to preview what would be created.
        """

    def _render_markdown(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a command template as Markdown."""

    def _render_toml(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a command template, then wrap in TOML format."""
```

*Note: `_write_copilot_stub()` removed per plan §D-07 — Copilot’s `.prompt.md` files ARE the command files, written directly to `.github/prompts/` via the standard `register_commands()` flow with `command_extension=".prompt.md"`.*

## Behavior

1. Iterates `PIPELINE_STAGES` (8 stages)
2. For each stage, renders the Jinja2 template `base/commands/specforge.{stage}.md.j2`
3. Applies the agent's `args_placeholder` to the rendered content
4. If `command_format == "toml"`, wraps the content in TOML structure
5. Writes to `{target_dir}/{agent.commands_dir}/specforge.{stage}{agent.command_extension}`
6. For Copilot, the `.prompt.md` extension on the command file IS the discovery mechanism — no separate stub needed (per plan §D-07)
7. If `force=True` and file exists, skips the file (preserves customizations)
8. Returns list of successfully written paths

## Error Handling

- `PermissionError` during file write → `Err("Permission denied writing to ...")`
- Missing template file → `Err("Command template not found: ...")`
- All recoverable errors use `Result[T, E]` — no exceptions raised
