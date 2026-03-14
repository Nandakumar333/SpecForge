"""specforge decompose command — decompose app description into features."""

from __future__ import annotations

import click


@click.command()
@click.argument("description")
def decompose(description: str) -> None:
    """Decompose an application description into features."""
    click.echo("specforge decompose: not yet implemented")
