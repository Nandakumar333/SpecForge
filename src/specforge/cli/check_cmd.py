"""specforge check command — verify prerequisites."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from specforge.core.checker import check_prerequisites
from specforge.core.config import AGENT_PRIORITY

console = Console()


@click.command()
@click.option(
    "--agent",
    type=click.Choice(AGENT_PRIORITY, case_sensitive=False),
    default=None,
    help="Include agent CLI in prerequisite check.",
)
def check(agent: str | None) -> None:
    """Check prerequisites for SpecForge."""
    results = check_prerequisites(agent=agent)
    table = Table(title="Prerequisite Check", show_header=False)
    table.add_column("status", width=3)
    table.add_column("tool", min_width=12)
    table.add_column("detail")
    for r in results:
        icon = "[green]✓[/green]" if r.found else "[red]✗[/red]"
        detail = r.version or ""
        if not r.found and r.install_hint:
            detail = f"not found  →  Install: {r.install_hint}"
        elif not r.found:
            detail = "not found"
        table.add_row(icon, r.tool, detail)
    console.print(table)
    missing = [r for r in results if not r.found]
    if missing:
        console.print(f"\n[red]{len(missing)} prerequisites missing.[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]All prerequisites met.[/green]")
