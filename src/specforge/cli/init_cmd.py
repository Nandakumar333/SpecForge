"""specforge init command — scaffold a new project."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from specforge.core.agent_detector import detect_agent
from specforge.core.config import AGENT_PRIORITY, SUPPORTED_STACKS
from specforge.core.git_ops import init_repo, is_git_available
from specforge.core.project import ProjectConfig
from specforge.core.scaffold_builder import build_scaffold_plan
from specforge.core.scaffold_writer import write_scaffold


@click.command()
@click.argument("name", required=False, default=None)
@click.option("--here", is_flag=True, help="Scaffold into CWD instead of creating a subdirectory.")
@click.option("--agent", type=click.Choice(AGENT_PRIORITY, case_sensitive=False), default=None, help="AI agent to configure.")
@click.option("--stack", type=click.Choice(SUPPORTED_STACKS, case_sensitive=False), default=None, help="Technology stack.")
@click.option("--force", is_flag=True, help="Allow scaffolding into an existing directory.")
@click.option("--no-git", is_flag=True, help="Skip git initialization.")
@click.option("--dry-run", is_flag=True, help="Preview file tree without writing.")
def init(
    name: str | None,
    here: bool,
    agent: str | None,
    stack: str | None,
    force: bool,
    no_git: bool,
    dry_run: bool,
) -> None:
    """Scaffold a new SpecForge project."""
    _validate_args(name, here)
    target_dir = _resolve_target(name, here)
    _check_existing(target_dir, name, here, force, dry_run)
    detection = detect_agent(explicit=agent)
    resolved_stack = stack or "agnostic"
    config_result = ProjectConfig.create(
        name=name or "", target_dir=target_dir, here=here,
        agent=detection.agent, stack=resolved_stack,
        no_git=no_git, force=force, dry_run=dry_run,
    )
    if not config_result.ok:
        _fail(config_result.error)
    config = config_result.value
    plan_result = build_scaffold_plan(config)
    if not plan_result.ok:
        _fail(plan_result.error)
    plan = plan_result.value
    if dry_run:
        _print_dry_run(plan)
        return
    write_result = write_scaffold(plan)
    if not write_result.ok:
        _fail(write_result.error)
    scaffold_result = write_result.value
    scaffold_result.agent_source = detection.source
    _handle_git(config, scaffold_result)
    _print_summary(scaffold_result)


def _validate_args(name: str | None, here: bool) -> None:
    """Validate mutual exclusion of NAME and --here."""
    if not name and not here:
        raise click.UsageError(
            "Missing argument 'NAME'. Use --here to scaffold into the current directory."
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
    target_dir: Path, name: str | None, here: bool,
    force: bool, dry_run: bool,
) -> None:
    """Check for existing directory conflicts."""
    if dry_run:
        return
    if here:
        specforge_dir = target_dir / ".specforge"
        if specforge_dir.exists() and not force:
            _fail(
                ".specforge/ already exists. "
                "Use --force to add missing files."
            )
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


def _print_dry_run(plan: object) -> None:
    """Print the dry-run tree preview."""
    from specforge.cli.output import console, render_dry_run_tree
    tree = render_dry_run_tree(plan)
    console.print("\n[bold yellow][DRY RUN][/bold yellow] Would create:")
    console.print(tree)
    console.print("No files were written.")


def _print_summary(result: object) -> None:
    """Print the Rich summary."""
    from specforge.cli.output import render_summary
    render_summary(result)


def _fail(message: str) -> None:
    """Print error and exit with code 1."""
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)
