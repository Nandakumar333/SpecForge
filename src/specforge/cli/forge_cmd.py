"""CLI command: specforge forge — single-command full spec generation."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specforge.core.config import (
    FORGE_DEFAULT_WORKERS,
    SUPPORTED_STACKS,
    VALID_ARCHITECTURES,
)
from specforge.core.forge_orchestrator import STATE_EXISTS


@click.command("forge")
@click.argument("description", default="")
@click.option(
    "--arch",
    type=click.Choice(VALID_ARCHITECTURES, case_sensitive=False),
    default="monolithic",
    help="Architecture type (default: monolithic).",
)
@click.option(
    "--stack",
    type=click.Choice([*SUPPORTED_STACKS, "auto"], case_sensitive=False),
    default="auto",
    help="Technology stack (default: auto-detect).",
)
@click.option(
    "--max-parallel",
    type=click.IntRange(min=1),
    default=FORGE_DEFAULT_WORKERS,
    help=f"Max concurrent workers (default: {FORGE_DEFAULT_WORKERS}).",
)
@click.option("--dry-run", is_flag=True, help="Preview prompts without LLM calls.")
@click.option("--resume", is_flag=True, help="Resume from interrupted run.")
@click.option("--skip-init", is_flag=True, help="Skip auto-initialization.")
@click.option("--force", is_flag=True, help="Overwrite existing forge state.")
def forge(
    description: str,
    arch: str,
    stack: str,
    max_parallel: int,
    dry_run: bool,
    resume: bool,
    skip_init: bool,
    force: bool,
) -> None:
    """Run the full spec generation pipeline in a single command."""
    console = Console()

    if resume and force:
        raise click.UsageError("--resume and --force are mutually exclusive.")

    if not description and not resume:
        console.print("[red]Error:[/red] Description is required.")
        sys.exit(2)

    orchestrator, progress = _build_forge(console)
    if orchestrator is None:
        sys.exit(2)

    if progress:
        progress.start()

    try:
        result = orchestrator.run_forge(
            description=description,
            arch_type=arch,
            stack=stack,
            max_parallel=max_parallel,
            dry_run=dry_run,
            resume=resume,
            force=force,
            skip_init=skip_init,
        )
    finally:
        if progress:
            progress.stop()

    if not result.ok:
        if result.error == STATE_EXISTS:
            _handle_state_exists(
                console, orchestrator, description, arch, stack,
                max_parallel, dry_run, skip_init,
            )
            return
        console.print(f"[red]Forge failed:[/red] {result.error}")
        sys.exit(2)

    report = result.value
    _print_report(console, report, dry_run)
    sys.exit(report.exit_code)


def _build_forge(console: Console) -> tuple:
    """Build ForgeOrchestrator with all dependencies."""
    from pathlib import Path

    from specforge.core.forge_orchestrator import ForgeOrchestrator
    from specforge.core.forge_progress import ForgeProgress
    from specforge.core.llm_provider import ProviderFactory

    project_dir = Path.cwd()
    config_path = project_dir / ".specforge" / "config.json"

    # Provider is optional — may not exist yet (auto-init will create it)
    provider = None
    if config_path.exists():
        factory_result = ProviderFactory.create(config_path)
        if factory_result.ok:
            provider = factory_result.value
        else:
            console.print(
                f"[yellow]Warning:[/yellow] {factory_result.error}"
            )

    if provider is None:
        provider = _make_deferred_provider(project_dir, console)

    progress = ForgeProgress(console)

    assembler = _build_assembler(project_dir)
    extractor, builder = _build_enrichment(project_dir)

    orchestrator = ForgeOrchestrator(
        project_dir=project_dir,
        llm_provider=provider,
        progress=progress,
        enriched_builder=builder,
        artifact_extractor=extractor,
        assembler=assembler,
    )
    return orchestrator, progress


def _make_deferred_provider(project_dir, console):
    """Create a provider that resolves after auto-init."""
    from specforge.core.llm_provider import ProviderFactory
    from specforge.core.result import Err

    class DeferredProvider:
        def __init__(self):
            self._inner = None

        def _resolve(self):
            if self._inner:
                return
            config = project_dir / ".specforge" / "config.json"
            if config.exists():
                result = ProviderFactory.create(config)
                if result.ok:
                    self._inner = result.value

        def call(self, system_prompt, user_prompt):
            self._resolve()
            if self._inner:
                return self._inner.call(system_prompt, user_prompt)
            return Err("No LLM provider configured")

        def is_available(self):
            self._resolve()
            if self._inner:
                return self._inner.is_available()
            return Err("No LLM provider configured")

    return DeferredProvider()


def _build_assembler(project_dir):
    """Build PromptAssembler if constitution exists."""
    import contextlib

    from specforge.core.prompt_assembler import PromptAssembler
    from specforge.core.prompt_loader import PromptLoader

    constitution = project_dir / ".specforge" / "memory" / "constitution.md"
    if not constitution.exists():
        constitution = project_dir / "constitution.md"

    loader = None
    with contextlib.suppress(Exception):
        loader = PromptLoader(project_dir)

    extractor, builder = _build_enrichment(project_dir)

    return PromptAssembler(
        constitution_path=constitution,
        prompt_loader=loader,
        artifact_extractor=extractor,
        enriched_prompt_builder=builder,
    )


def _build_enrichment(project_dir):
    """Build ArtifactExtractor and EnrichedPromptBuilder."""
    import contextlib
    from pathlib import Path

    from specforge.core.artifact_extractor import ArtifactExtractor
    from specforge.core.enriched_prompts import EnrichedPromptBuilder
    from specforge.core.prompt_loader import PromptLoader

    extractor = ArtifactExtractor()

    template_dir = (
        project_dir / "src" / "specforge" / "templates" / "base" / "enrichment"
    )
    if not template_dir.exists():
        import specforge
        pkg_dir = Path(specforge.__file__).parent
        template_dir = pkg_dir / "templates" / "base" / "enrichment"

    loader = None
    with contextlib.suppress(Exception):
        loader = PromptLoader(project_dir)

    builder = EnrichedPromptBuilder(
        template_dir=template_dir,
        governance_loader=loader,
    )
    return extractor, builder


def _handle_state_exists(
    console, orchestrator, description, arch, stack,
    max_parallel, dry_run, skip_init,
):
    """Prompt user when previous state exists."""
    from rich.prompt import Prompt

    choice = Prompt.ask(
        "Previous forge run detected. [O]verwrite / [R]esume / [A]bort?",
        choices=["o", "r", "a"],
        default="a",
    )
    if choice == "a":
        console.print("Aborted.")
        sys.exit(0)

    result = orchestrator.run_forge(
        description=description,
        arch_type=arch,
        stack=stack,
        max_parallel=max_parallel,
        dry_run=dry_run,
        resume=(choice == "r"),
        force=(choice == "o"),
        skip_init=skip_init,
    )
    if result.ok:
        _print_report(console, result.value, dry_run)
        sys.exit(result.value.exit_code)
    else:
        console.print(f"[red]Forge failed:[/red] {result.error}")
        sys.exit(2)


def _print_report(console: Console, report, dry_run: bool) -> None:
    """Print forge completion summary."""
    if dry_run:
        console.print(Panel(
            f"[bold]Dry Run Complete[/bold]\n\n"
            f"Services: {len(report.services)}\n"
            f"Prompts: {len(report.services) * 7}\n"
            f"Estimated tokens: {report.estimated_tokens}",
            title="Forge Dry Run",
        ))
        return

    table = Table(title="Forge Results")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Artifacts", style="magenta")

    for svc in report.services:
        status_style = (
            "green" if svc.status == "complete"
            else "red" if "fail" in svc.status
            else "yellow"
        )
        table.add_row(
            svc.slug,
            f"[{status_style}]{svc.status}[/{status_style}]",
            f"{len(svc.artifacts)}/7",
        )

    console.print(table)
    console.print(f"\nTotal time: {report.total_elapsed:.1f}s")
    if report.exit_code == 0:
        label = "success"
    elif report.exit_code == 1:
        label = "partial failure"
    else:
        label = "failure"
    console.print(f"Exit code: {report.exit_code} ({label})")
