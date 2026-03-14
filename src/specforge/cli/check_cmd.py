"""specforge check command — verify prerequisites."""

from __future__ import annotations

import click

from specforge.core.config import AGENT_PRIORITY


@click.command()
@click.option("--agent", type=click.Choice(AGENT_PRIORITY, case_sensitive=False), default=None, help="Include agent CLI in prerequisite check.")
def check(agent: str | None) -> None:
    """Check prerequisites for SpecForge."""
    click.echo("specforge check: not yet implemented")
