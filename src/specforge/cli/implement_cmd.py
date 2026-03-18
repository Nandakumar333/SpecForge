"""CLI: specforge implement — single service, shared-infra, or --all."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

from specforge.core.config import IMPLEMENTATION_MODES, MAX_FIX_ATTEMPTS

if TYPE_CHECKING:
    from specforge.core.integration_orchestrator import IntegrationOrchestrator

console = Console()


@click.command()
@click.argument("target", required=False, default=None)
@click.option(
    "--shared-infra", is_flag=True,
    help="Build cross-service infrastructure first",
)
@click.option(
    "--all", "run_all", is_flag=True,
    help="Implement all services in dependency order",
)
@click.option(
    "--to-phase", "to_phase", type=int, default=None,
    help="Stop after completing this phase (0-indexed, requires --all)",
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
    run_all: bool,
    to_phase: int | None,
    resume: bool,
    mode: str,
    max_fix_attempts: int,
) -> None:
    """Implement a service or module by executing its tasks.md."""
    project_root = Path.cwd()

    # --all is mutually exclusive with target and --shared-infra
    if run_all and target:
        console.print("[red]Error: --all and target are mutually exclusive[/]")
        sys.exit(2)
    if run_all and shared_infra:
        console.print("[red]Error: --all and --shared-infra are mutually exclusive[/]")
        sys.exit(2)
    if to_phase is not None and not run_all:
        console.print("[red]Error: --to-phase requires --all[/]")
        sys.exit(2)
    if run_all:
        _implement_all(project_root, mode, resume, to_phase)
        return

    if shared_infra and target:
        console.print("[red]Error: --shared-infra and target are mutually exclusive[/]")
        sys.exit(2)
    if not shared_infra and not target:
        console.print(
            "[red]Error: provide a target service, --shared-infra, or --all[/]",
        )
        sys.exit(2)
    if resume and not target and not run_all:
        console.print("[red]Error: --resume requires a target service or --all[/]")
        sys.exit(2)

    if shared_infra:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver
        from specforge.core.quality_checker import QualityChecker
        from specforge.core.shared_infra_executor import SharedInfraExecutor
        from specforge.core.task_runner import TaskRunner

        contract_resolver = ContractResolver(project_root)
        context_builder = ContextBuilder(
            project_root=project_root,
            prompt_loader=None,
            contract_resolver=contract_resolver,
        )
        task_runner = TaskRunner(project_root)

        infra_executor = SharedInfraExecutor(
            context_builder=context_builder,
            task_runner=task_runner,
            quality_checker_factory=QualityChecker,
            auto_fix_loop=None,
            project_root=project_root,
        )
        result = infra_executor.execute(mode)
        if result.ok:
            console.print("[bold green]Shared infrastructure complete[/]")
            sys.exit(0)
        else:
            console.print(f"[bold red]Shared infrastructure failed: {result.error}[/]")
            sys.exit(1)

    from specforge.core.auto_fix_loop import AutoFixLoop
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

    def _make_checker(root: Path, slug: str) -> QualityChecker:
        return QualityChecker(root, slug)

    checker_for_fix = QualityChecker(project_root, target)
    auto_fix = AutoFixLoop(task_runner, checker_for_fix, max_attempts=max_fix_attempts)

    executor = SubAgentExecutor(
        context_builder=context_builder,
        task_runner=task_runner,
        quality_checker_factory=_make_checker,
        auto_fix_loop=auto_fix,
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


# ── --all orchestration ───────────────────────────────────────────────


def _implement_all(
    project_root: Path,
    mode: str,
    resume: bool,
    phase_ceiling: int | None,
) -> None:
    """Implement all services in dependency order."""
    orch = _build_orchestrator(project_root)
    result = orch.execute(mode, resume=resume, phase_ceiling=phase_ceiling)

    if result.ok:
        report = result.value
        console.print(f"\n[bold green]Orchestration Complete ({report.verdict})[/]")
        console.print(f"  Architecture: {report.architecture}")
        console.print(
            f"  Phases: {report.total_phases}  Services: {report.total_services}",
        )
        console.print(
            f"  Succeeded: {report.succeeded_services}  "
            f"Failed: {report.failed_services}  "
            f"Skipped: {report.skipped_services}",
        )
        sys.exit(0 if report.verdict == "pass" else 1)
    else:
        console.print(f"\n[bold red]Orchestration failed: {result.error}[/]")
        sys.exit(1)


def _build_orchestrator(project_root: Path) -> IntegrationOrchestrator:
    """Construct IntegrationOrchestrator with all collaborators."""
    from specforge.core.auto_fix_loop import AutoFixLoop
    from specforge.core.context_builder import ContextBuilder
    from specforge.core.contract_enforcer import ContractEnforcer
    from specforge.core.contract_resolver import ContractResolver
    from specforge.core.integration_orchestrator import IntegrationOrchestrator
    from specforge.core.integration_reporter import IntegrationReporter
    from specforge.core.integration_test_runner import IntegrationTestRunner
    from specforge.core.quality_checker import QualityChecker
    from specforge.core.shared_infra_executor import SharedInfraExecutor
    from specforge.core.sub_agent_executor import SubAgentExecutor
    from specforge.core.task_runner import TaskRunner

    contract_resolver = ContractResolver(project_root)
    context_builder = ContextBuilder(
        project_root=project_root,
        prompt_loader=None,
        contract_resolver=contract_resolver,
    )
    task_runner = TaskRunner(project_root)

    def _make_checker(root: Path, slug: str) -> QualityChecker:
        return QualityChecker(root, slug)

    sub_agent_executor = SubAgentExecutor(
        context_builder=context_builder,
        task_runner=task_runner,
        quality_checker_factory=_make_checker,
        auto_fix_loop=AutoFixLoop(task_runner, None, max_attempts=3),
        docker_manager=None,
        project_root=project_root,
    )

    shared_infra_executor = SharedInfraExecutor(
        context_builder=context_builder,
        task_runner=task_runner,
        quality_checker_factory=QualityChecker,
        auto_fix_loop=None,
        project_root=project_root,
    )

    return IntegrationOrchestrator(
        sub_agent_executor=sub_agent_executor,
        shared_infra_executor=shared_infra_executor,
        contract_enforcer=ContractEnforcer(project_root),
        integration_test_runner=IntegrationTestRunner(project_root),
        integration_reporter=IntegrationReporter(project_root),
        project_root=project_root,
    )
