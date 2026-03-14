"""Rich rendering for CLI output — dry-run tree and summary."""

from __future__ import annotations

from rich.console import Console
from rich.tree import Tree

from specforge.core.project import ScaffoldPlan, ScaffoldResult

console = Console()


def render_dry_run_tree(plan: ScaffoldPlan) -> Tree:
    """Build a Rich Tree showing the file structure that would be created."""
    root_name = plan.config.name
    tree = Tree(f"[bold]{root_name}/[/bold]")
    _build_tree(tree, plan)
    return tree


def _build_tree(tree: Tree, plan: ScaffoldPlan) -> None:
    """Add directory and file nodes to the tree."""
    nodes: dict[str, Tree] = {}
    for scaffold_file in plan.files:
        parts = scaffold_file.relative_path.parts
        parent = tree
        for i, part in enumerate(parts[:-1]):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                nodes[key] = parent.add(f"[bold blue]{part}/[/bold blue]")
            parent = nodes[key]
        parent.add(parts[-1])


def render_summary(result: ScaffoldResult) -> None:
    """Print a Rich-formatted summary of the scaffold operation."""
    plan = result.plan
    config = plan.config
    total = len(result.written)
    console.print(f"\n[green]✓[/green] Created .specforge/ structure ({total} files)")
    agent_label = f"{config.agent} ({result.agent_source})"
    console.print(f"[green]✓[/green] Agent configured: {agent_label}")
    console.print(f"[green]✓[/green] Stack: {config.stack}")
    if result.git_committed:
        console.print("[green]✓[/green] Git initialized with initial commit")
    elif config.no_git:
        console.print("[dim]- Git skipped (--no-git)[/dim]")
    _print_next_steps(config)


def _print_next_steps(config: object) -> None:
    """Print suggested next steps."""
    console.print("\n[bold]Next steps:[/bold]")
    if not getattr(config, "here", False):
        console.print(f"  cd {getattr(config, 'name', '')}")
    console.print("  specforge check")
    console.print('  specforge specify "your first feature"')
