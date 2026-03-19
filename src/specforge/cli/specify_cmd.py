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
@click.option(
    "--template-mode",
    is_flag=True,
    default=False,
    help="Force Jinja2 template rendering (no LLM calls)",
)
@click.option(
    "--dry-run-prompt",
    is_flag=True,
    default=False,
    help="Write assembled prompts to .prompt.md without calling LLM",
)
@click.pass_context
def specify(
    ctx: click.Context,
    target: str,
    force: bool,
    from_phase: str | None,
    template_mode: bool,
    dry_run_prompt: bool,
) -> None:
    """Generate specification artifacts for a service or feature."""
    console = Console()
    project_root = Path.cwd()

    if template_mode and dry_run_prompt:
        console.print(
            "[red]Error:[/red] --template-mode and --dry-run-prompt "
            "are mutually exclusive."
        )
        raise SystemExit(1)

    registry = TemplateRegistry(project_root)
    registry.discover()
    renderer = TemplateRenderer(registry)
    prompt_context = _load_prompt_context(project_root)

    provider = None
    assembler = None
    validator = None
    postprocessor = None

    if not template_mode:
        provider, assembler, validator, postprocessor = _resolve_llm_deps(
            project_root, console
        )

    orchestrator = PipelineOrchestrator(
        renderer=renderer,
        registry=registry,
        prompt_context=prompt_context,
        provider=provider,
        assembler=assembler,
        validator=validator,
        postprocessor=postprocessor,
        dry_run_prompt=dry_run_prompt,
    )

    console.print(f"[bold]Generating specs for:[/bold] {target}")
    if provider:
        console.print("[dim]Mode: AI generation[/dim]")
    elif dry_run_prompt:
        console.print("[dim]Mode: Dry-run prompt[/dim]")
    else:
        console.print("[dim]Mode: Template rendering[/dim]")

    result = orchestrator.run(target, project_root, force=force, from_phase=from_phase)

    if result.ok:
        console.print(f"[green]Pipeline complete.[/green] Artifacts in: {result.value}")
    else:
        console.print(f"[red]Pipeline failed:[/red] {result.error}")
        raise SystemExit(1)


def _resolve_llm_deps(project_root: Path, console: Console) -> tuple:
    """Resolve LLM provider and dependencies, fallback to None."""
    try:
        from specforge.core.llm_provider import ProviderFactory
        from specforge.core.output_postprocessor import OutputPostprocessor
        from specforge.core.output_validator import OutputValidator
        from specforge.core.prompt_assembler import PromptAssembler
        from specforge.core.prompt_loader import PromptLoader

        config_path = project_root / ".specforge" / "config.json"
        factory_result = ProviderFactory.create(config_path)
        if not factory_result.ok:
            console.print(
                f"[yellow]Warning:[/yellow] {factory_result.error}. "
                "Falling back to template mode."
            )
            return None, None, None, None

        provider = factory_result.value
        constitution = project_root / ".specforge" / "memory" / "constitution.md"
        if not constitution.exists():
            constitution = project_root / "constitution.md"

        import contextlib

        loader: PromptLoader | None = None
        with contextlib.suppress(Exception):
            loader = PromptLoader(project_root)

        assembler = PromptAssembler(
            constitution_path=constitution,
            prompt_loader=loader,
        )
        validator = OutputValidator()
        postprocessor = OutputPostprocessor()
        return provider, assembler, validator, postprocessor
    except Exception as exc:
        console.print(
            f"[yellow]Warning:[/yellow] LLM setup failed: {exc}. "
            "Falling back to template mode."
        )
        return None, None, None, None


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
