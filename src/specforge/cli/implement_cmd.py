"""CLI command: specforge implement <service> [--shared-infra] [--resume] [--mode]."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from specforge.core.config import IMPLEMENTATION_MODES, MAX_FIX_ATTEMPTS

console = Console()


@click.command()
@click.argument("target", required=False, default=None)
@click.option(
    "--shared-infra", is_flag=True,
    help="Build cross-service infrastructure first",
)
@click.option(
    "--resume", is_flag=True,
    help="Resume from last completed task",
)
@click.option(
    "--mode",
    type=click.Choice(list(IMPLEMENTATION_MODES)),
    default="prompt-display",
    help="Execution mode",
)
@click.option(
    "--max-fix-attempts",
    type=int, default=MAX_FIX_ATTEMPTS,
    help="Max auto-fix retry attempts per task",
)
@click.pass_context
def implement(
    ctx: click.Context,
    target: str | None,
    shared_infra: bool,
    resume: bool,
    mode: str,
    max_fix_attempts: int,
) -> None:
    """Implement a service or module by executing its tasks.md."""
    project_root = Path.cwd()

    if shared_infra and target:
        console.print("[red]Error: --shared-infra and target are mutually exclusive[/]")
        sys.exit(2)
    if not shared_infra and not target:
        console.print("[red]Error: provide a target service or --shared-infra[/]")
        sys.exit(2)
    if resume and not target:
        console.print("[red]Error: --resume requires a target service[/]")
        sys.exit(2)

    if shared_infra:
        console.print("[yellow]Shared infrastructure not yet implemented[/]")
        sys.exit(3)

    from specforge.core.context_builder import ContextBuilder
    from specforge.core.contract_resolver import ContractResolver
    from specforge.core.quality_checker import QualityChecker
    from specforge.core.sub_agent_executor import SubAgentExecutor
    from specforge.core.task_runner import TaskRunner

    contract_resolver = ContractResolver(project_root)
    context_builder = ContextBuilder(
        project_root=project_root,
        prompt_loader=None,
        contract_resolver=contract_resolver,
    )
    task_runner = TaskRunner(project_root)

    executor = SubAgentExecutor(
        context_builder=context_builder,
        task_runner=task_runner,
        quality_checker_factory=QualityChecker,
        auto_fix_loop=None,
        docker_manager=None,
        project_root=project_root,
    )

    result = executor.execute(target, mode, resume=resume)

    if result.ok:
        state = result.value
        completed = sum(1 for t in state.tasks if t.status == "completed")
        failed = sum(1 for t in state.tasks if t.status == "failed")
        skipped = sum(1 for t in state.tasks if t.status == "skipped")
        total = len(state.tasks)

        console.print(f"\n[bold green]Implementation Summary: {target}[/]")
        console.print(f"  Tasks completed: {completed}/{total}")
        if failed:
            console.print(f"  Tasks failed: {failed}")
        if skipped:
            console.print(f"  Tasks skipped: {skipped}")
        sys.exit(0)
    else:
        console.print(f"\n[bold red]Implementation halted: {result.error}[/]")
        sys.exit(1)
