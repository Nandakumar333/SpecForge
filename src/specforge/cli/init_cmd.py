"""specforge init command — scaffold a new project."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from specforge.core.agent_detector import detect_agent
from specforge.core.config import SUPPORTED_STACKS, VALID_ARCHITECTURES
from specforge.core.git_ops import init_repo, is_git_available
from specforge.core.project import ProjectConfig
from specforge.core.result import Result
from specforge.core.scaffold_builder import (
    build_scaffold_plan,
    generate_governance_files,
)
from specforge.core.scaffold_writer import write_scaffold
from specforge.core.stack_detector import StackDetector


@click.command()
@click.argument("name", required=False, default=None)
@click.option(
    "--here",
    is_flag=True,
    help="Scaffold into CWD instead of creating a subdirectory.",
)
@click.option(
    "--agent",
    type=str,
    default=None,
    help="AI agent to configure.",
)
@click.option(
    "--stack",
    type=click.Choice(SUPPORTED_STACKS, case_sensitive=False),
    default=None,
    help="Technology stack.",
)
@click.option(
    "--arch",
    type=click.Choice(VALID_ARCHITECTURES, case_sensitive=False),
    default="monolithic",
    help="Architecture pattern (default: monolithic).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Allow scaffolding into an existing directory.",
)
@click.option("--no-git", is_flag=True, hidden=True, help="Skip git init.")
@click.option("--dry-run", is_flag=True, hidden=True, help="Preview without writing.")
def init(
    name: str | None,
    here: bool,
    agent: str | None,
    stack: str | None,
    arch: str,
    force: bool,
    no_git: bool,
    dry_run: bool,
) -> None:
    """Scaffold a new SpecForge project."""
    _validate_args(name, here)
    target_dir = _resolve_target(name, here)
    _check_existing(target_dir, name, here, force, dry_run)

    # Resolve agent: explicit flag > interactive prompt > auto-detect
    resolved_agent, agent_source = _resolve_agent(agent)
    commands_dir_override: str | None = None
    if resolved_agent == "generic" and agent_source == "interactive":
        commands_dir_override = _prompt_commands_dir()

    resolved_stack = stack or StackDetector.detect(target_dir)
    config_result = ProjectConfig.create(
        name=name or "",
        target_dir=target_dir,
        here=here,
        agent=resolved_agent,
        stack=resolved_stack,
        architecture=arch,
        no_git=no_git,
        force=force,
        dry_run=dry_run,
    )
    if not config_result.ok:
        _fail(config_result.error)
    config = config_result.value
    plan_result = build_scaffold_plan(config)
    if not plan_result.ok:
        _fail(plan_result.error)
    plan = plan_result.value

    # Get the agent plugin for commands registration
    agent_plugin = _get_agent_plugin(resolved_agent, commands_dir_override)

    if dry_run:
        _print_dry_run(plan, agent_plugin)
        return

    write_result = write_scaffold(plan)
    if not write_result.ok:
        _fail(write_result.error)
    scaffold_result = write_result.value
    scaffold_result.agent_source = agent_source

    # Plugin integration — stack rules for governance
    extra_rules = _get_plugin_rules(resolved_stack, arch)

    # Generate governance prompt files after scaffold directories exist
    gov_result = generate_governance_files(
        config, extra_rules_by_domain=extra_rules,
    )
    if not gov_result.ok:
        _fail(gov_result.error)

    # Agent config generation via plugin
    _generate_agent_config(resolved_agent, config.target_dir, config)

    # Register command files for the selected agent
    commands_dir = agent_plugin.commands_dir if agent_plugin else "commands"
    cmd_result = _register_commands(
        agent_plugin, config, force,
    )
    if cmd_result and cmd_result.ok:
        scaffold_result.commands_written = cmd_result.value

    # Write extended config.json with agent + commands_dir
    _write_extended_config(config, resolved_agent, commands_dir)

    _handle_git(config, scaffold_result)
    _print_summary(scaffold_result, resolved_agent, agent_source, commands_dir)


def _resolve_agent(explicit: str | None) -> tuple[str, str]:
    """Resolve agent via explicit flag, interactive prompt, or auto-detect."""
    if explicit:
        return explicit, "explicit"

    if sys.stdin.isatty():
        return _prompt_agent_selection()

    detection = detect_agent()
    return detection.agent, detection.source


def _prompt_agent_selection() -> tuple[str, str]:
    """Present interactive agent selection prompt."""
    from rich.prompt import Prompt

    from specforge.plugins.plugin_manager import PluginManager

    mgr = PluginManager()
    mgr.discover()
    plugins = mgr.list_agent_plugins()
    agent_names = [p.agent_name() for p in plugins if p.agent_name() != "generic"]
    agent_names.sort()
    agent_names.append("generic")

    try:
        selected = Prompt.ask(
            "Which AI agent do you want to use?",
            choices=agent_names,
            default="generic",
        )
    except KeyboardInterrupt:
        click.echo("\nAborted.", err=True)
        sys.exit(1)

    return selected, "interactive"


def _prompt_commands_dir() -> str:
    """Prompt for custom commands directory when generic is selected."""
    from rich.prompt import Prompt

    while True:
        try:
            path = Prompt.ask("Commands directory", default="commands")
        except KeyboardInterrupt:
            click.echo("\nAborted.", err=True)
            sys.exit(1)

        validation = _validate_commands_dir(path)
        if validation.ok:
            return validation.value
        click.echo(f"Error: {validation.error}", err=True)


def _validate_commands_dir(path: str) -> Result[str, str]:
    """Validate a custom commands directory path."""
    from specforge.core.result import Err, Ok

    if not path or not path.strip():
        return Err("Commands directory must not be empty.")
    normalized = path.strip().replace("\\", "/")
    if Path(normalized).is_absolute() or normalized.startswith("/"):
        return Err("Commands directory must be a relative path.")
    if ".." in Path(normalized).parts:
        return Err(
            "Commands directory must not traverse outside project root."
        )
    return Ok(normalized)


def _get_agent_plugin(
    agent: str, commands_dir_override: str | None = None,
) -> object | None:
    """Get agent plugin instance, optionally with custom commands dir."""
    from specforge.plugins.agents.generic_plugin import GenericPlugin
    from specforge.plugins.plugin_manager import PluginManager

    if agent == "generic" and commands_dir_override:
        return GenericPlugin(commands_dir=commands_dir_override)

    mgr = PluginManager()
    mgr.discover()
    result = mgr.get_agent_plugin(agent)
    return result.value if result.ok else None


def _register_commands(
    agent_plugin: object | None,
    config: ProjectConfig,
    force: bool,
) -> Result | None:
    """Register command files for the selected agent."""
    if agent_plugin is None:
        return None

    from specforge.core.command_registrar import CommandRegistrar

    registrar = CommandRegistrar()
    context = {
        "project_name": config.name,
        "stack": config.stack,
        "architecture": config.architecture,
    }
    return registrar.register_commands(
        agent_plugin, config.target_dir, context, force=force,
    )


def _write_extended_config(
    config: ProjectConfig, agent: str, commands_dir: str,
) -> None:
    """Write config.json with agent and commands_dir fields."""
    from specforge.core.prompt_manager import _write_config_json

    _write_config_json(
        config.target_dir, config.name, config.stack,
        agent=agent, commands_dir=commands_dir,
    )


def _get_plugin_rules(
    stack: str, arch: str,
) -> dict[str, list] | None:
    """Get stack plugin rules for the given architecture."""
    from specforge.plugins.plugin_manager import PluginManager

    mgr = PluginManager()
    mgr.discover()
    result = mgr.get_stack_plugin(stack)
    if result.ok:
        rules = result.value.get_prompt_rules(arch)
        return rules if rules else None
    return None


def _generate_agent_config(
    agent: str, target_dir: Path, config: ProjectConfig,
) -> None:
    """Generate agent-specific config files via plugin."""
    from specforge.plugins.plugin_manager import PluginManager

    mgr = PluginManager()
    mgr.discover()
    result = mgr.get_agent_plugin(agent)
    if result.ok:
        context = {
            "project_name": config.name,
            "stack": config.stack,
            "architecture": config.architecture,
            "governance_summary": "",
            "agent_name": agent,
        }
        result.value.generate_config(target_dir, context)


def _validate_args(name: str | None, here: bool) -> None:
    """Validate mutual exclusion of NAME and --here."""
    if not name and not here:
        raise click.UsageError(
            "Missing argument 'NAME'. "
            "Use --here to scaffold into the current directory."
        )
    if name and here:
        _fail(
            "Cannot specify both NAME and --here. "
            "Use --here to scaffold into the current directory."
        )


def _resolve_target(name: str | None, here: bool) -> Path:
    """Resolve the target directory path."""
    if here:
        return Path.cwd().resolve()
    return (Path.cwd() / name).resolve()


def _check_existing(
    target_dir: Path,
    name: str | None,
    here: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Check for existing directory conflicts."""
    if dry_run:
        return
    if here:
        specforge_dir = target_dir / ".specforge"
        if specforge_dir.exists() and not force:
            _fail(".specforge/ already exists. Use --force to add missing files.")
    elif target_dir.exists() and not force:
        _fail(
            f"Directory '{name}' already exists.\n"
            f"Use --force to scaffold into it: specforge init {name} --force"
        )


def _handle_git(config: ProjectConfig, result: object) -> None:
    """Handle git initialization based on config."""
    if config.no_git:
        return
    if not is_git_available():
        _fail(
            "git is not installed. "
            "Install git or use --no-git to skip git initialization."
        )
    git_result = init_repo(config.target_dir)
    if git_result.ok:
        result.git_committed = True


def _print_dry_run(plan: object, agent_plugin: object | None = None) -> None:
    """Print the dry-run tree preview."""
    from specforge.cli.output import console, render_dry_run_tree

    tree = render_dry_run_tree(plan)

    # Add command files to dry-run preview
    if agent_plugin is not None:
        from specforge.core.command_registrar import CommandRegistrar

        registrar = CommandRegistrar()
        context = {
            "project_name": plan.config.name,
            "stack": plan.config.stack,
            "architecture": plan.config.architecture,
        }
        cmd_files = registrar.build_command_files(agent_plugin, context)

        cmd_branch = tree.add(f"[bold]{agent_plugin.commands_dir}/[/bold]")
        for cf in cmd_files:
            cmd_branch.add(f"[dim]{cf.filename}[/dim]")

    console.print("\n[bold yellow][DRY RUN][/bold yellow] Would create:")
    console.print(tree)
    console.print("No files were written.")


def _print_summary(
    result: object,
    agent: str = "generic",
    agent_source: str = "generic",
    commands_dir: str = "commands",
) -> None:
    """Print the Rich summary."""
    from specforge.cli.output import render_summary

    render_summary(result)

    from specforge.cli.output import console

    console.print(f"  ✓ Agent: {agent} ({agent_source})")
    console.print(f"  ✓ Commands directory: {commands_dir}")


def _fail(message: str) -> None:
    """Print error and exit with code 1."""
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)
