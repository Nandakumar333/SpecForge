"""specforge decompose command — decompose app description into features."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from specforge.core.config import (
    MANIFEST_PATH,
    OVER_ENGINEERING_THRESHOLD,
    PARALLEL_DEFAULT_MAX_WORKERS,
    PARALLEL_STATE_FILENAME,
    STATE_PATH,
    VALID_ARCHITECTURES,
)
from specforge.core.decomposition_state import (
    DecompositionState,
    load_state,
    save_state,
)
from specforge.core.domain_analyzer import DomainAnalyzer
from specforge.core.domain_patterns import DOMAIN_PATTERNS, GENERIC_PATTERN

console = Console()


@click.command()
@click.argument("description")
@click.option(
    "--arch",
    type=click.Choice(VALID_ARCHITECTURES, case_sensitive=False),
    default=None,
    help="Architecture: monolithic, microservice, modular-monolith.",
)
@click.option(
    "-i", "--interactive",
    is_flag=True,
    default=False,
    help="Enable interactive prompts (default: auto mode with parallel).",
)
@click.option(
    "--remap",
    type=click.Choice(VALID_ARCHITECTURES, case_sensitive=False),
    default=None,
    help="Re-map existing features to new architecture.",
)
@click.option(
    "--sequential",
    is_flag=True,
    default=False,
    help="Run spec pipelines one at a time instead of in parallel.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Stop everything on first failure.",
)
# ── Hidden power-user flags (still functional, not in --help) ─────
@click.option("--no-warn", is_flag=True, default=False, hidden=True)
@click.option("--template-mode", is_flag=True, default=False, hidden=True)
@click.option("--dry-run-prompt", is_flag=True, default=False, hidden=True)
@click.option("--auto", is_flag=True, default=False, hidden=True)
@click.option("--parallel", is_flag=True, default=False, hidden=True)
@click.option("--max-parallel", type=int, default=None, hidden=True)
@click.option("--fail-fast", is_flag=True, default=False, hidden=True)
def decompose(
    description: str,
    arch: str | None,
    interactive: bool,
    remap: str | None,
    sequential: bool,
    strict: bool,
    no_warn: bool,
    template_mode: bool,
    dry_run_prompt: bool,
    auto: bool,
    parallel: bool,
    max_parallel: int | None,
    fail_fast: bool,
) -> None:
    """Decompose an application description into features.

    By default runs in auto mode: LLM-powered decomposition with parallel
    spec generation across all services. Use -i for interactive prompts.

    \b
    Examples:
      specforge decompose "Personal Finance App"
      specforge decompose "E-commerce Platform" --arch microservice
      specforge decompose "My App" -i            # interactive prompts
      specforge decompose "My App" --sequential   # no parallel
    """
    # Resolve semantic flags → internal flags
    is_auto = auto or not interactive
    is_parallel = parallel or (not sequential and not template_mode)
    is_fail_fast = fail_fast or strict

    if template_mode and dry_run_prompt:
        _exit_error("--template-mode and --dry-run-prompt are mutually exclusive.")
    if arch and remap:
        _exit_error(
            "Cannot use --arch and --remap together. "
            "Use --arch for new projects or --remap to change "
            "existing architecture."
        )
    if max_parallel is not None and max_parallel < 1:
        _exit_error("--max-parallel must be >= 1")
    project_root = Path.cwd()
    if remap:
        _handle_remap(project_root, description, remap, no_warn)
        return
    _handle_decompose(
        project_root,
        description,
        arch,
        no_warn if not is_auto else True,
        template_mode=template_mode,
        dry_run_prompt=dry_run_prompt,
        auto=is_auto,
        parallel=is_parallel,
        max_parallel=max_parallel,
        fail_fast=is_fail_fast,
    )


def _handle_decompose(
    root: Path,
    description: str,
    arch: str | None,
    no_warn: bool,
    *,
    template_mode: bool = False,
    dry_run_prompt: bool = False,
    auto: bool = False,
    parallel: bool = False,
    max_parallel: int | None = None,
    fail_fast: bool = False,
) -> None:
    """Main decompose flow: gate -> analyze -> map -> review -> write."""
    state_path = root / STATE_PATH
    state_result = load_state(state_path)
    if state_result.ok and state_result.value is not None:
        state = state_result.value
        if state.step != "complete":
            if auto:
                (root / STATE_PATH).unlink(missing_ok=True)
            else:
                _handle_resume(root, state, description, arch, no_warn)
                return

    manifest_path = root / MANIFEST_PATH
    if manifest_path.exists():
        if auto:
            pass  # auto mode: overwrite existing
        else:
            _handle_existing_manifest(root, description, arch, no_warn)
            return

    if not template_mode:
        llm_result = _try_llm_decompose(
            root, description, arch, dry_run_prompt=dry_run_prompt,
            auto=auto,
        )
        if llm_result:
            if parallel and not dry_run_prompt:
                _run_parallel_pipelines(
                    root, max_parallel=max_parallel, fail_fast=fail_fast,
                )
            return

    _run_fresh_decompose(root, description, arch, no_warn)


def _run_fresh_decompose(
    root: Path,
    description: str,
    arch: str | None,
    no_warn: bool,
) -> None:
    """Run a fresh decompose from scratch."""
    analyzer = DomainAnalyzer(DOMAIN_PATTERNS, GENERIC_PATTERN)

    if analyzer.is_gibberish(description):
        _exit_gibberish()

    architecture = arch or _prompt_architecture()
    _save_arch_state(root, description, architecture)

    match = analyzer.analyze(description)
    if not match.ok:
        _exit_error(f"Analysis failed: {match.error}")

    domain_match = match.value
    if domain_match.score < 2:
        description = _run_clarification(analyzer, description)
        match = analyzer.analyze(description)
        if not match.ok:
            _exit_error(f"Analysis failed: {match.error}")
        domain_match = match.value

    _display_domain_info(domain_match)

    features_result = analyzer.decompose(description, domain_match)
    if not features_result.ok:
        _exit_error(f"Decomposition failed: {features_result.error}")

    features = features_result.value
    if len(features) > 15:
        _warn_complexity(len(features))

    _check_overengineering(architecture, len(features), no_warn)
    _display_features(features)
    _save_decomp_state(root, description, architecture, domain_match, features)

    if architecture == "monolithic":
        _finalize_monolith(root, description, architecture, domain_match, features)
    else:
        _finalize_services(root, description, architecture, domain_match, features)


def _prompt_architecture() -> str:
    """Display architecture options and prompt for selection."""
    console.print(
        Panel(
            "[bold]1.[/bold] Monolithic - Single deployable unit, "
            "features as modules\n"
            "[bold]2.[/bold] Microservice - Independent services per "
            "bounded context\n"
            "[bold]3.[/bold] Modular Monolith - Single deployable, "
            "strict module boundaries",
            title="Architecture Selection",
        )
    )
    choice = Prompt.ask(
        "Select architecture",
        choices=["1", "2", "3"],
        default="1",
    )
    return {"1": "monolithic", "2": "microservice", "3": "modular-monolith"}[choice]


def _run_clarification(
    analyzer: DomainAnalyzer,
    description: str,
) -> str:
    """Ask clarification questions and augment the description."""
    console.print(
        "\n[yellow]Description is too vague. "
        "Answering these questions will help:[/yellow]\n"
    )
    questions = analyzer.clarify(description)
    answers: list[str] = []
    for q in questions:
        answer = Prompt.ask(f"  {q}")
        if answer.strip():
            answers.append(answer.strip())
    return f"{description} {' '.join(answers)}"


def _display_domain_info(domain_match: object) -> None:
    """Display matched domain information."""
    console.print(
        f"\nDomain detected: [bold]{domain_match.domain_name}[/bold] "
        f"(score: {domain_match.score})"
    )


def _display_features(features: list) -> None:
    """Display features as a Rich table."""
    table = Table(title="\nFeatures identified")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Priority", style="green")
    table.add_column("Category")
    for f in features:
        table.add_row(f.id, f.display_name, f.priority, f.category)
    console.print(table)


def _warn_complexity(count: int) -> None:
    """Warn about excessive features."""
    console.print(
        f"\n[yellow]Warning: {count} features identified. "
        "Consider consolidating related features.[/yellow]"
    )


def _check_overengineering(
    architecture: str,
    count: int,
    no_warn: bool,
) -> None:
    """Check if microservice is overkill for few features."""
    if no_warn or architecture == "monolithic":
        return
    if count > OVER_ENGINEERING_THRESHOLD:
        return
    if architecture in ("microservice", "modular-monolith"):
        console.print(
            f"\n[yellow]Warning: This project has {count} features. "
            "Microservices may be over-engineering. "
            "Consider Modular Monolith.[/yellow]"
        )
        proceed = Prompt.ask(
            "Proceed anyway?",
            choices=["y", "n"],
            default="y",
        )
        if proceed == "n":
            raise SystemExit(1)


def _finalize_monolith(
    root: Path,
    description: str,
    architecture: str,
    domain_match: object,
    features: list,
) -> None:
    """Finalize monolithic architecture — skip service mapping."""
    from specforge.core.service_mapper import ServiceMapper

    mapper = ServiceMapper()
    result = mapper.map_features(features, architecture)
    services = result.value if result.ok else []
    _write_manifest_and_dirs(
        root,
        description,
        architecture,
        domain_match,
        features,
        services,
        events=[],
    )


def _finalize_services(
    root: Path,
    description: str,
    architecture: str,
    domain_match: object,
    features: list,
) -> None:
    """Finalize microservice/modular-monolith with service mapping."""
    from specforge.core.communication_planner import CommunicationPlanner
    from specforge.core.service_mapper import ServiceMapper

    mapper = ServiceMapper()
    result = mapper.map_features(features, architecture)
    if not result.ok:
        _exit_error(f"Service mapping failed: {result.error}")
    services = result.value
    _display_services(services)
    _save_mapping_state(
        root, description, architecture, domain_match, features, services
    )
    services = _interactive_review(root, services, features)

    planner = CommunicationPlanner()
    services, events = planner.plan(services)
    cycles = planner.detect_cycles(services)
    if cycles:
        for cycle in cycles:
            console.print(f"[yellow]Circular dependency: {' -> '.join(cycle)}[/yellow]")

    _write_comm_map(root, architecture, services, events, planner)
    _write_manifest_and_dirs(
        root,
        description,
        architecture,
        domain_match,
        features,
        services,
        events,
    )


def _display_services(services: list) -> None:
    """Display service mapping as a Rich table."""
    table = Table(title="\nService Mapping")
    table.add_column("#", style="cyan")
    table.add_column("Service")
    table.add_column("Features")
    table.add_column("Rationale")
    for i, svc in enumerate(services, 1):
        table.add_row(
            str(i),
            svc.name,
            ", ".join(svc.feature_ids),
            svc.rationale,
        )
    console.print(table)


def _interactive_review(
    root: Path,
    services: list,
    features: list,
) -> list:
    """Interactive review/edit loop for service mapping."""
    try:
        from specforge.core.service_mapper import Service  # noqa: F401
    except ImportError:
        return services

    while True:
        cmd = Prompt.ask(
            "\nEdit mapping (combine/split/rename/add/remove/override/done)",
            default="done",
        )
        if cmd.strip().lower() == "done":
            break
        result = _apply_edit_command(cmd, services, features)
        if result is not None:
            services = result
            _display_services(services)
        else:
            _show_edit_help()
    return services


def _apply_edit_command(
    cmd: str,
    services: list,
    features: list,
) -> list | None:
    """Parse and apply an edit command. Returns updated list or None."""
    parts = cmd.strip().split()
    if not parts:
        return None
    action = parts[0].lower()
    match action:
        case "combine" if len(parts) >= 3:
            return _cmd_combine(services, parts[1], parts[2])
        case "split" if len(parts) >= 3:
            return _cmd_split(services, parts[1], parts[2])
        case "rename" if len(parts) >= 3:
            return _cmd_rename(services, parts[1], " ".join(parts[2:]))
        case "add" if len(parts) >= 2:
            return _cmd_add(services, " ".join(parts[1:]))
        case "remove" if len(parts) >= 2:
            return _cmd_remove(services, parts[1], features)
        case "override" if len(parts) >= 4:
            return _cmd_override(services, parts[1], parts[2], parts[3])
        case _:
            return None


def _cmd_combine(services: list, slug1: str, slug2: str) -> list | None:
    """Combine two services."""
    from specforge.core.service_mapper import Service

    svc1 = _find_service(services, slug1)
    svc2 = _find_service(services, slug2)
    if not svc1 or not svc2:
        console.print("[red]Service not found.[/red]")
        return None
    combined = Service(
        name=svc1.name,
        slug=svc1.slug,
        feature_ids=svc1.feature_ids + svc2.feature_ids,
        rationale=f"Combined: merged {svc1.name} and {svc2.name}",
        communication=svc1.communication,
    )
    result = [s for s in services if s.slug not in (slug1, slug2)]
    result.append(combined)
    return result


def _cmd_split(services: list, slug: str, feature_id: str) -> list | None:
    """Split a feature out of a service into a new one."""
    from specforge.core.service_mapper import Service

    svc = _find_service(services, slug)
    if not svc or feature_id not in svc.feature_ids:
        console.print("[red]Service or feature not found.[/red]")
        return None
    remaining = tuple(f for f in svc.feature_ids if f != feature_id)
    new_slug = f"{slug}-split"
    updated = Service(
        name=svc.name,
        slug=svc.slug,
        feature_ids=remaining,
        rationale=svc.rationale,
        communication=svc.communication,
    )
    new_svc = Service(
        name=f"{svc.name} Split",
        slug=new_slug,
        feature_ids=(feature_id,),
        rationale=f"Split from {svc.name}",
        communication=(),
    )
    result = [s if s.slug != slug else updated for s in services]
    result.append(new_svc)
    return result


def _cmd_rename(services: list, slug: str, new_name: str) -> list | None:
    """Rename a service."""
    from specforge.core.service_mapper import Service, _generate_slug

    svc = _find_service(services, slug)
    if not svc:
        console.print("[red]Service not found.[/red]")
        return None
    new_slug = _generate_slug(new_name)
    renamed = Service(
        name=new_name,
        slug=new_slug,
        feature_ids=svc.feature_ids,
        rationale=svc.rationale,
        communication=svc.communication,
    )
    return [renamed if s.slug == slug else s for s in services]


def _cmd_add(services: list, name: str) -> list | None:
    """Add a new empty service."""
    from specforge.core.service_mapper import Service, _generate_slug

    slug = _generate_slug(name)
    new_svc = Service(
        name=name,
        slug=slug,
        feature_ids=(),
        rationale="Manually added",
        communication=(),
    )
    return [*services, new_svc]


def _cmd_remove(services: list, slug: str, features: list) -> list | None:
    """Remove a service and reassign its features."""
    svc = _find_service(services, slug)
    if not svc:
        console.print("[red]Service not found.[/red]")
        return None
    if not svc.feature_ids:
        return [s for s in services if s.slug != slug]
    other = [s for s in services if s.slug != slug]
    if not other:
        console.print("[red]Cannot remove the only service.[/red]")
        return None
    console.print(f"Reassigning features from {svc.name}:")
    target_slug = Prompt.ask(
        "  Target service slug",
        choices=[s.slug for s in other],
    )
    target = _find_service(other, target_slug)
    if not target:
        return None
    from specforge.core.service_mapper import Service

    updated = Service(
        name=target.name,
        slug=target.slug,
        feature_ids=target.feature_ids + svc.feature_ids,
        rationale=target.rationale,
        communication=target.communication,
    )
    return [updated if s.slug == target_slug else s for s in other]


def _cmd_override(services: list, slug: str, target: str, pattern: str) -> list | None:
    """Override communication pattern between services."""
    from specforge.core.config import COMMUNICATION_PATTERNS

    if pattern not in COMMUNICATION_PATTERNS:
        console.print(f"[red]Invalid pattern. Use: {COMMUNICATION_PATTERNS}[/red]")
        return None
    console.print(f"Override: {slug} -> {target} = {pattern}")
    return services


def _find_service(services: list, slug: str) -> object | None:
    """Find a service by slug."""
    for svc in services:
        if svc.slug == slug:
            return svc
    return None


def _show_edit_help() -> None:
    """Show available edit commands."""
    console.print(
        "[dim]Commands: combine <s1> <s2>, split <s> <fid>, "
        "rename <s> <name>, add <name>, remove <s>, "
        "override <s> <target> <pattern>, done[/dim]"
    )


def _write_comm_map(
    root: Path,
    architecture: str,
    services: list,
    events: list,
    planner: object,
) -> None:
    """Write communication-map.md using Jinja2 template."""
    from specforge.core.config import COMMUNICATION_MAP_PATH

    mermaid = planner.generate_mermaid(services, events)
    svc_dicts = [
        {
            "name": s.name,
            "communication": [
                {
                    "target": lnk.target,
                    "pattern": lnk.pattern,
                    "required": lnk.required,
                    "description": lnk.description,
                }
                for lnk in s.communication
            ],
        }
        for s in services
    ]
    event_dicts = [
        {
            "name": e.name,
            "producer": e.producer,
            "consumers": list(e.consumers),
            "payload_summary": e.payload_summary,
        }
        for e in events
    ]
    context = {
        "app_name": "Project",
        "architecture": architecture,
        "services": svc_dicts,
        "events": event_dicts,
        "mermaid_diagram": mermaid,
    }
    try:
        from specforge.core.template_registry import TemplateRegistry
        from specforge.core.template_renderer import TemplateRenderer

        registry = TemplateRegistry()
        renderer = TemplateRenderer(registry)
        result = renderer.render_raw("base/features/communication-map.md.j2", context)
        if result.ok:
            comm_path = root / COMMUNICATION_MAP_PATH
            comm_path.parent.mkdir(parents=True, exist_ok=True)
            comm_path.write_text(result.value, encoding="utf-8")
            console.print(
                f"[green]Communication map written to {COMMUNICATION_MAP_PATH}[/green]"
            )
    except Exception:
        pass


def _write_manifest_and_dirs(
    root: Path,
    description: str,
    architecture: str,
    domain_match: object,
    features: list,
    services: list,
    events: list | None = None,
) -> None:
    """Write manifest.json and create feature directories."""
    from specforge.core.manifest_writer import ManifestWriter

    writer = ManifestWriter()
    manifest = writer.build_manifest(
        arch=architecture,
        domain=domain_match.domain_name,
        features=features,
        services=services,
        events=events or [],
        description=description,
    )
    manifest_path = root / MANIFEST_PATH
    result = writer.write(manifest_path, manifest)
    if not result.ok:
        _exit_error(f"Manifest write failed: {result.error}")
    val_result = writer.validate(manifest_path)
    if not val_result.ok:
        console.print(
            f"[yellow]Manifest validation warning: {val_result.error}[/yellow]"
        )
    console.print(f"\n[green]Manifest written to {MANIFEST_PATH}[/green]")
    _create_feature_dirs(root, features)
    _cleanup_state(root)
    console.print("[green]Done![/green]")


def _create_feature_dirs(root: Path, features: list) -> None:
    """Create feature directories under .specforge/features/."""
    from specforge.core.config import FEATURES_DIR

    features_dir = root / FEATURES_DIR
    for f in features:
        slug = f"{f.id}-{f.name}"
        feat_dir = features_dir / slug
        feat_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Feature directories created under {FEATURES_DIR}/[/green]")


def _save_arch_state(root: Path, description: str, architecture: str) -> None:
    """Save state after architecture selection."""
    state = DecompositionState(
        step="architecture",
        architecture=architecture,
        project_description=description,
    )
    save_state(root / STATE_PATH, state)


def _save_decomp_state(
    root: Path,
    description: str,
    architecture: str,
    domain_match: object,
    features: list,
) -> None:
    """Save state after feature decomposition."""
    feature_dicts = tuple(
        {"id": f.id, "name": f.name, "description": f.description} for f in features
    )
    state = DecompositionState(
        step="decomposition",
        architecture=architecture,
        project_description=description,
        domain=domain_match.domain_name,
        features=feature_dicts,
    )
    save_state(root / STATE_PATH, state)


def _save_mapping_state(
    root: Path,
    description: str,
    architecture: str,
    domain_match: object,
    features: list,
    services: list,
) -> None:
    """Save state after service mapping."""
    feature_dicts = tuple(
        {"id": f.id, "name": f.name, "description": f.description} for f in features
    )
    service_dicts = tuple(
        {"name": s.name, "slug": s.slug, "feature_ids": list(s.feature_ids)}
        for s in services
    )
    state = DecompositionState(
        step="mapping",
        architecture=architecture,
        project_description=description,
        domain=domain_match.domain_name,
        features=feature_dicts,
        services=service_dicts,
    )
    save_state(root / STATE_PATH, state)


def _cleanup_state(root: Path) -> None:
    """Delete state file on successful completion."""
    state_path = root / STATE_PATH
    if state_path.exists():
        state_path.unlink()


def _handle_resume(
    root: Path,
    state: DecompositionState,
    description: str,
    arch: str | None,
    no_warn: bool,
) -> None:
    """Handle resuming from a saved state."""
    console.print(
        f"\n[yellow]Existing decomposition state found (step: {state.step}).[/yellow]"
    )
    choice = Prompt.ask(
        "Resume or start fresh?",
        choices=["resume", "fresh"],
        default="resume",
    )
    if choice == "fresh":
        (root / STATE_PATH).unlink(missing_ok=True)
        _run_fresh_decompose(root, description, arch, no_warn)
    else:
        _run_fresh_decompose(root, description, arch, no_warn)


def _handle_existing_manifest(
    root: Path,
    description: str,
    arch: str | None,
    no_warn: bool,
) -> None:
    """Handle existing manifest.json on re-run."""
    console.print(
        "\n[yellow]Existing decomposition found (.specforge/manifest.json).[/yellow]"
    )
    choice = Prompt.ask(
        "Start fresh (overwrites existing)?",
        choices=["y", "n"],
        default="y",
    )
    if choice == "y":
        _run_fresh_decompose(root, description, arch, no_warn)
    else:
        console.print("Keeping existing decomposition.")


def _handle_remap(
    root: Path,
    description: str,
    remap: str,
    no_warn: bool,
) -> None:
    """Handle --remap flow: reload features, re-map to new architecture."""
    import json

    manifest_path = root / MANIFEST_PATH
    if not manifest_path.exists():
        _exit_error("No existing manifest found. Run decompose first.")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    from specforge.core.domain_analyzer import Feature

    features = [
        Feature(
            id=f["id"],
            name=f["name"],
            display_name=f.get("display_name", f["name"]),
            description=f["description"],
            priority=f["priority"],
            category=f["category"],
            always_separate=False,
            data_keywords=(),
        )
        for f in data["features"]
    ]
    from specforge.core.domain_analyzer import DomainMatch

    domain = DomainMatch(data.get("domain", "generic"), 0, ())
    console.print(f"\nRe-mapping {len(features)} features to {remap}")
    _check_overengineering(remap, len(features), no_warn)

    if remap == "monolithic":
        _finalize_monolith(root, description, remap, domain, features)
    else:
        _finalize_services(root, description, remap, domain, features)


def _exit_error(message: str) -> None:
    """Print error and exit."""
    console.print(f"\n[red]{message}[/red]")
    raise SystemExit(1)


def _exit_gibberish() -> None:
    """Exit with gibberish error message."""
    _exit_error(
        "Could not understand the description. Try something like:\n"
        '  specforge decompose "Create a personal finance webapp"\n'
        '  specforge decompose "Build an e-commerce platform"\n'
        '  specforge decompose "Create a social media app"'
    )


def _try_llm_decompose(
    root: Path,
    description: str,
    arch: str | None,
    *,
    dry_run_prompt: bool = False,
    auto: bool = False,
) -> bool:
    """Attempt LLM-based decomposition. Returns True if successful."""

    try:
        from specforge.core.llm_provider import ProviderFactory
        from specforge.core.output_postprocessor import OutputPostprocessor
        from specforge.core.phase_prompts import PHASE_PROMPTS
    except ImportError:
        return False

    config_path = root / ".specforge" / "config.json"
    factory_result = ProviderFactory.create(config_path)
    if not factory_result.ok:
        console.print(
            f"[yellow]Warning:[/yellow] {factory_result.error}. "
            "Falling back to rule-based decomposition."
        )
        return False

    provider = factory_result.value
    phase_prompt = PHASE_PROMPTS["decompose"]
    architecture = arch or "microservice"

    from specforge.core.architecture_adapter import create_adapter

    adapter = create_adapter(architecture)

    system_parts = [
        phase_prompt.clean_markdown_instruction,
        phase_prompt.system_instructions,
        f"Target architecture: {architecture}",
        adapter.serialize_for_prompt(),
    ]
    system_prompt = "\n\n".join(system_parts)
    user_prompt = (
        f"Decompose this application into features and services:\n\n"
        f"{description}\n\n"
        f"Architecture: {architecture}\n\n"
        f"Output format:\n{phase_prompt.skeleton}"
    )

    if dry_run_prompt:
        prompt_dir = root / ".specforge"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = prompt_dir / "decompose.prompt.md"
        content = (
            f"# System Prompt\n\n{system_prompt}\n\n"
            f"---\n\n# User Prompt\n\n{user_prompt}\n"
        )
        prompt_path.write_text(content, encoding="utf-8")
        console.print(f"[green]Dry run:[/green] Prompt written to {prompt_path}")
        return True

    console.print("[dim]Calling LLM for feature decomposition...[/dim]")
    call_result = provider.call(system_prompt, user_prompt)
    if not call_result.ok:
        console.print(
            f"[yellow]Warning:[/yellow] LLM call failed: "
            f"{call_result.error}. Falling back to rule-based."
        )
        return False

    raw_output = OutputPostprocessor.strip_preamble(call_result.value)
    parsed = _parse_llm_decompose(raw_output)
    if parsed is None:
        console.print(
            "[yellow]Warning:[/yellow] Could not parse LLM output. "
            "Falling back to rule-based decomposition."
        )
        return False

    _write_llm_manifest(root, parsed, architecture, description)
    return True


def _parse_llm_decompose(raw: str) -> dict | None:
    """Parse LLM decompose output as JSON."""
    import json as _json
    import re

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return None
    try:
        data = _json.loads(json_match.group())
        if "features" in data:
            return data
    except _json.JSONDecodeError:
        pass
    return None


def _write_llm_manifest(
    root: Path,
    data: dict,
    architecture: str,
    description: str,
) -> None:
    """Write manifest.json from LLM decompose output."""
    import json as _json

    from specforge.core.config import FEATURES_DIR, MANIFEST_PATH, SCHEMA_VERSION

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "architecture": architecture,
        "project_description": description,
        "features": data.get("features", []),
        "services": data.get("services", []),
        "events": data.get("events", []),
    }
    manifest_path = root / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(_json.dumps(manifest, indent=2), encoding="utf-8")
    console.print(
        f"[green]LLM decomposition complete.[/green] "
        f"{len(manifest['features'])} features across "
        f"{len(manifest['services'])} services."
    )

    features_dir = root / FEATURES_DIR
    for svc in manifest.get("services", []):
        slug = svc.get("slug", "")
        if slug:
            (features_dir / slug).mkdir(parents=True, exist_ok=True)


# ── Parallel Execution (Feature 016) ─────────────────────────────────


def _run_parallel_pipelines(
    root: Path,
    *,
    max_parallel: int | None = None,
    fail_fast: bool = False,
) -> None:
    """Run spec pipelines in parallel for all services in the manifest."""
    import json as _json

    manifest_path = root / MANIFEST_PATH
    if not manifest_path.exists():
        return
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    services = manifest.get("services", [])
    if not services:
        return

    slugs = tuple(s["slug"] for s in services if s.get("slug"))
    if not slugs:
        return

    max_workers = _resolve_max_workers(root, max_parallel)

    console.print(
        f"\n[bold]Running parallel spec pipelines[/bold] "
        f"({len(slugs)} services, {max_workers} workers)"
    )

    from specforge.core.parallel_pipeline_runner import ParallelPipelineRunner
    from specforge.core.parallel_progress_tracker import ProgressTracker

    state_path = root / PARALLEL_STATE_FILENAME
    tracker = ProgressTracker(
        console=console,
        total_services=len(slugs),
        state_path=state_path,
    )

    def _make_orchestrator():
        from specforge.core.spec_pipeline import PipelineOrchestrator
        from specforge.core.template_registry import TemplateRegistry
        from specforge.core.template_renderer import TemplateRenderer

        registry = TemplateRegistry(root)
        registry.discover()
        renderer = TemplateRenderer(registry)
        provider, assembler, validator, postprocessor = _resolve_llm_for_parallel(root)
        return PipelineOrchestrator(
            renderer=renderer,
            registry=registry,
            provider=provider,
            assembler=assembler,
            validator=validator,
            postprocessor=postprocessor,
        )

    runner = ParallelPipelineRunner(
        orchestrator_factory=_make_orchestrator,
        tracker=tracker,
        max_workers=max_workers,
        fail_fast=fail_fast,
    )

    result = runner.run(slugs, root)
    _print_parallel_summary(result)


def _resolve_llm_for_parallel(root: Path) -> tuple:
    """Resolve LLM provider for parallel pipeline (each thread gets its own)."""
    try:
        from specforge.core.llm_provider import ProviderFactory
        from specforge.core.output_postprocessor import OutputPostprocessor
        from specforge.core.output_validator import OutputValidator
        from specforge.core.prompt_assembler import PromptAssembler
        from specforge.core.prompt_loader import PromptLoader

        config_path = root / ".specforge" / "config.json"
        factory_result = ProviderFactory.create(config_path)
        if not factory_result.ok:
            return None, None, None, None

        provider = factory_result.value
        constitution = root / ".specforge" / "memory" / "constitution.md"
        if not constitution.exists():
            constitution = root / "constitution.md"

        import contextlib

        loader = None
        with contextlib.suppress(Exception):
            loader = PromptLoader(root)

        assembler = PromptAssembler(
            constitution_path=constitution,
            prompt_loader=loader,
        )
        validator = OutputValidator()
        postprocessor = OutputPostprocessor()
        return provider, assembler, validator, postprocessor
    except Exception:
        return None, None, None, None


def _resolve_max_workers(root: Path, cli_override: int | None) -> int:
    """Resolve max workers from CLI flag or config.json."""
    if cli_override is not None:
        return cli_override
    try:
        import json as _json

        config_path = root / ".specforge" / "config.json"
        if config_path.exists():
            data = _json.loads(config_path.read_text(encoding="utf-8"))
            parallel_config = data.get("parallel", {})
            return parallel_config.get("max_workers", PARALLEL_DEFAULT_MAX_WORKERS)
    except (ValueError, OSError):
        pass
    return PARALLEL_DEFAULT_MAX_WORKERS


def _print_parallel_summary(result) -> None:
    """Print summary table after parallel execution."""
    from rich.table import Table

    if not result.ok:
        console.print(f"\n[red]Parallel execution failed: {result.error}[/red]")
        return

    state = result.value
    table = Table(title="\nParallel Execution Summary")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Phases")
    table.add_column("Error")

    for svc in state.services:
        status_style = {
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
            "blocked": "yellow",
        }.get(svc.status, "dim")
        table.add_row(
            svc.slug,
            f"[{status_style}]{svc.status}[/{status_style}]",
            f"{svc.phases_completed}/{svc.phases_total}",
            svc.error or "",
        )
    console.print(table)

    completed = sum(1 for s in state.services if s.status == "completed")
    failed = sum(1 for s in state.services if s.status == "failed")
    console.print(
        f"\n[bold]{completed}/{state.total_services} services completed"
        f"{'  (' + str(failed) + ' failed)' if failed else ''}[/bold]"
    )
