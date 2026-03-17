"""CLI command: specforge clarify <target> [--report]."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from specforge.core.boundary_analyzer import BoundaryAnalyzer
from specforge.core.clarification_analyzer import AmbiguityScanner, default_patterns
from specforge.core.clarification_models import ClarificationAnswer
from specforge.core.clarification_recorder import ClarificationRecorder
from specforge.core.config import (
    MANIFEST_PATH,
    PIPELINE_LOCK_FILENAME,
)
from specforge.core.pipeline_lock import acquire_lock, release_lock
from specforge.core.question_generator import QuestionGenerator
from specforge.core.service_context import load_service_context, resolve_target
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer

_console = Console()


@click.command("clarify")
@click.argument("target")
@click.option("--report", is_flag=True, help="Generate report without interactive mode")
def clarify(target: str, report: bool) -> None:
    """Detect and resolve ambiguities in a service spec."""
    project_root = Path.cwd()
    console = _console

    # Resolve target to service slug
    slug_result = resolve_target(target, project_root)
    if not slug_result.ok:
        console.print(f"[red]Error:[/red] {slug_result.error}")
        raise SystemExit(1)

    ctx_result = load_service_context(slug_result.value, project_root)
    if not ctx_result.ok:
        console.print(f"[red]Error:[/red] {ctx_result.error}")
        raise SystemExit(1)

    service_ctx = ctx_result.value
    spec_path = service_ctx.output_dir / "spec.md"
    if not spec_path.exists():
        console.print(f"[red]Error:[/red] spec.md not found at {spec_path}")
        raise SystemExit(1)

    # Acquire pipeline lock
    lock_path = project_root / MANIFEST_PATH.rsplit("/", 1)[0] / PIPELINE_LOCK_FILENAME
    lock_result = acquire_lock(lock_path, service_ctx.service_slug)
    if not lock_result.ok:
        console.print(f"[red]Error:[/red] {lock_result.error}")
        raise SystemExit(1)

    try:
        _run_clarify(project_root, service_ctx, spec_path, report, console)
    finally:
        release_lock(lock_path)


def _run_clarify(
    project_root: Path,
    service_ctx: object,
    spec_path: Path,
    report: bool,
    console: Console,
) -> None:
    """Core clarification logic after lock acquisition."""
    console.print(
        f"[bold]Scanning {service_ctx.service_slug} spec for ambiguities...[/bold]"
    )
    spec_text = spec_path.read_text(encoding="utf-8")

    # 1. Scan for pattern-based ambiguities
    scanner = AmbiguityScanner(default_patterns())
    matches = list(scanner.scan(spec_text))

    # 2. Boundary analysis
    manifest_path = project_root / MANIFEST_PATH
    manifest = _load_manifest_dict(manifest_path)
    if manifest:
        boundary = BoundaryAnalyzer(manifest)
        matches.extend(boundary.analyze(service_ctx.service_slug))
        if boundary.detect_remap(manifest):
            matches.extend(boundary.get_remap_questions(service_ctx.service_slug))
            recorder = ClarificationRecorder()
            recorder.mark_revalidation(
                spec_path, ("service_boundary", "communication"),
            )

    if not matches:
        console.print("[green]No ambiguities detected.[/green]")
        return

    # 3. Generate questions
    generator = QuestionGenerator()
    questions = generator.generate(tuple(matches), service_ctx)

    cats = {}
    for q in questions:
        cats[q.category] = cats.get(q.category, 0) + 1
    cat_summary = ", ".join(f"{v} {k}" for k, v in sorted(cats.items()))
    console.print(
        f"Found {len(questions)} ambiguities ({cat_summary})"
    )

    # 4. Report mode
    if report:
        _generate_report(project_root, service_ctx, questions, console)
        return

    # 5. Interactive mode
    answers = _interactive_session(questions, console)
    if answers:
        recorder = ClarificationRecorder()
        result = recorder.record(spec_path, tuple(answers), questions)
        if result.ok:
            console.print(f"\n[green]Updated:[/green] {spec_path}")
        else:
            console.print(f"[red]Error recording:[/red] {result.error}")

    answered = len(answers)
    skipped = len(questions) - answered
    console.print(
        f"\nClarification complete: {answered} answered, {skipped} skipped"
    )


def _interactive_session(
    questions: tuple,
    console: Console,
) -> list[ClarificationAnswer]:
    """Present questions interactively and collect answers."""
    answers: list[ClarificationAnswer] = []
    total = len(questions)
    for idx, q in enumerate(questions, start=1):
        console.print(f"\n[bold]Q{idx} [{q.category}] ({idx}/{total})[/bold]")
        console.print(f'[dim]Context: "{q.context_excerpt}"[/dim]')
        console.print(f"[bold]{q.question_text}[/bold]")

        table = Table(show_header=True)
        table.add_column("Option", width=6)
        table.add_column("Answer")
        table.add_column("Implications")
        for a in q.suggested_answers:
            table.add_row(a.label, a.text, a.implications)
        console.print(table)

        labels = [a.label for a in q.suggested_answers] + ["skip"]
        try:
            choice = click.prompt(
                "Your choice",
                type=click.Choice(labels, case_sensitive=False),
                default="skip",
            )
        except (click.Abort, EOFError):
            break

        if choice.lower() == "skip":
            continue

        selected = next(
            (a for a in q.suggested_answers if a.label == choice.upper()),
            None,
        )
        answer_text = selected.text if selected else choice
        is_custom = selected is None
        answers.append(ClarificationAnswer(
            question_id=q.id,
            answer_text=answer_text,
            is_custom=is_custom,
            answered_at=datetime.now(tz=UTC).isoformat(),
        ))
    return answers


def _generate_report(
    project_root: Path,
    service_ctx: object,
    questions: tuple,
    console: Console,
) -> None:
    """Render the clarifications-report.md.j2 template."""
    registry = TemplateRegistry(project_root)
    registry.discover()
    renderer = TemplateRenderer(registry)

    context = {
        "project_name": getattr(service_ctx, "project_description", ""),
        "date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "service": {
            "slug": service_ctx.service_slug,
            "name": service_ctx.service_name,
        },
        "architecture": service_ctx.architecture,
        "questions": [
            {
                "id": q.id,
                "category": q.category,
                "context_excerpt": q.context_excerpt,
                "question_text": q.question_text,
                "suggested_answers": [
                    {"label": a.label, "text": a.text, "implications": a.implications}
                    for a in q.suggested_answers
                ],
            }
            for q in questions
        ],
    }
    result = renderer.render(
        "clarifications-report", TemplateType.feature, context,
    )
    if not result.ok:
        console.print(f"[red]Template error:[/red] {result.error}")
        raise SystemExit(1)

    out_path = service_ctx.output_dir / "clarifications-report.md"
    out_path.write_text(result.value, encoding="utf-8")
    console.print(f"Report written to: {out_path}")


def _load_manifest_dict(manifest_path: Path) -> dict | None:
    """Load manifest.json as a plain dict, or None on failure."""
    import json

    with contextlib.suppress(OSError, json.JSONDecodeError):
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return None
