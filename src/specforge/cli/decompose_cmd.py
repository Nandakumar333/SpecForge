"""specforge decompose command — decompose app description into features."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command()
@click.argument("description")
def decompose(description: str) -> None:
    """Decompose an application description into features."""
    console.print(f'\nDecomposing: "{description}"\n')
    console.print(
        "[yellow]App Analyzer integration pending (Feature 004).[/yellow]\n"
        "This command will invoke the App Analyzer agent to identify "
        "features from your description.\n\n"
        'Run [bold]specforge specify "feature name"[/bold] '
        "to begin speccing a feature manually."
    )
