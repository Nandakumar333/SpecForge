"""CLI command: specforge specify <target>."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from specforge.core.config import PIPELINE_PHASES
from specforge.core.spec_pipeline import PipelineOrchestrator
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer


@click.command("specify")
@click.argument("target")
@click.option("--force", is_flag=True, help="Regenerate all artifacts")
@click.option(
    "--from",
    "from_phase",
    type=click.Choice(PIPELINE_PHASES),
    default=None,
    help="Start from a specific phase",
)
@click.pass_context
def specify(
    ctx: click.Context,
    target: str,
    force: bool,
    from_phase: str | None,
) -> None:
    """Generate specification artifacts for a service or feature."""
    console = Console()
    project_root = Path.cwd()

    registry = TemplateRegistry(project_root)
    registry.discover()
    renderer = TemplateRenderer(registry)
    prompt_context = _load_prompt_context(project_root)

    orchestrator = PipelineOrchestrator(
        renderer=renderer,
        registry=registry,
        prompt_context=prompt_context,
    )

    console.print(f"[bold]Generating specs for:[/bold] {target}")
    result = orchestrator.run(
        target, project_root, force=force, from_phase=from_phase
    )

    if result.ok:
        console.print(
            f"[green]Pipeline complete.[/green] "
            f"Artifacts in: {result.value}"
        )
    else:
        console.print(f"[red]Pipeline failed:[/red] {result.error}")
        raise SystemExit(1)


def _load_prompt_context(project_root: Path) -> str:
    """Load governance prompt context if available (FR-065 graceful)."""
    try:
        from specforge.core.prompt_context import PromptContextBuilder
        from specforge.core.prompt_loader import PromptLoader

        loader = PromptLoader(project_root)
        load_result = loader.load()
        if load_result.ok and load_result.value is not None:
            return PromptContextBuilder.build(load_result.value)
    except (ImportError, Exception):
        pass
    return ""
