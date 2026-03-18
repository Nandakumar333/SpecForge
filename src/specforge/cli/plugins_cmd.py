"""specforge plugins command — list and inspect plugins."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table


@click.group()
def plugins() -> None:
    """Manage SpecForge plugins."""


@plugins.command(name="list")
def list_plugins() -> None:
    """List all available stack and agent plugins."""
    from specforge.plugins.plugin_manager import PluginManager

    console = Console()
    mgr = PluginManager()
    mgr.discover()

    _print_stack_table(console, mgr)
    _print_agent_table(console, mgr)


def _print_stack_table(console: Console, mgr: object) -> None:
    """Render the stack plugins table."""
    stack_table = Table(title="Stack Plugins")
    stack_table.add_column("Name", style="cyan")
    stack_table.add_column("Description")
    stack_table.add_column("Architectures", style="green")
    for p in mgr.list_stack_plugins():
        stack_table.add_row(
            p.plugin_name,
            p.description,
            ", ".join(p.supported_architectures),
        )
    console.print(stack_table)


def _print_agent_table(console: Console, mgr: object) -> None:
    """Render the agent plugins table."""
    agent_table = Table(title="Agent Plugins")
    agent_table.add_column("Name", style="cyan")
    agent_table.add_column("Config Files", style="green")
    for a in mgr.list_agent_plugins():
        agent_table.add_row(
            a.agent_name(),
            ", ".join(a.config_files()),
        )
    console.print(agent_table)
