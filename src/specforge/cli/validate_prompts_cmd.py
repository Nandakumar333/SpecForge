"""CLI command: specforge validate-prompts."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from specforge.core.prompt_loader import PromptLoader
from specforge.core.prompt_models import ConflictEntry
from specforge.core.prompt_validator import PromptValidator

_console = Console()


@click.command("validate-prompts")
@click.option(
    "--project",
    default=".",
    type=click.Path(exists=False, file_okay=False),
    help="Path to the project root (default: current directory).",
)
def validate_prompts(project: str) -> None:
    """Validate governance prompt files for threshold conflicts.

    Exit codes:
      0 — No conflicts detected.
      1 — One or more threshold conflicts found.
      2 — Project not initialized (no .specforge/ directory).
    """
    project_root = Path(project).resolve()
    specforge_dir = project_root / ".specforge"

    if not specforge_dir.is_dir():
        _console.print(
            f"[red]Error:[/red] No .specforge/ directory found at {project_root}.\n"
            "Run 'specforge init' to initialize the project."
        )
        sys.exit(2)

    loader = PromptLoader(project_root)
    load_result = loader.load_for_feature("validate")

    if not load_result.ok:
        _console.print(f"[red]Error loading governance files:[/red] {load_result.error}")
        sys.exit(2)

    prompt_set = load_result.value
    validator = PromptValidator()
    report = validator.detect_conflicts(prompt_set)

    if not report.has_conflicts:
        _console.print("[green]No conflicts detected[/green] in governance prompt files.")
        sys.exit(0)

    _console.print(
        f"[yellow]Found {len(report.conflicts)} threshold conflict(s)[/yellow] "
        "in governance prompt files:\n"
    )
    _print_conflict_table(report.conflicts)
    sys.exit(1)


def _print_conflict_table(conflicts: tuple[ConflictEntry, ...]) -> None:
    """Render conflicts as a Rich table."""
    table = Table(
        title="Governance Threshold Conflicts",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Threshold Key", style="cyan", no_wrap=True)
    table.add_column("Domain A", style="white")
    table.add_column("Value A", style="white")
    table.add_column("Domain B", style="white")
    table.add_column("Value B", style="white")
    table.add_column("Winner", style="green")
    table.add_column("Status", style="yellow")

    for c in conflicts:
        status = "AMBIGUOUS" if c.is_ambiguous else "RESOLVED"
        winner = c.winning_domain if not c.is_ambiguous else "—"
        table.add_row(
            c.threshold_key,
            f"{c.domain_a} ({c.rule_id_a})",
            c.value_a,
            f"{c.domain_b} ({c.rule_id_b})",
            c.value_b,
            winner,
            status,
        )

    _console.print(table)

    _console.print("\n[bold]Suggested Resolutions:[/bold]")
    for i, c in enumerate(conflicts, start=1):
        _console.print(f"  {i}. {c.suggested_resolution}")
