"""SpecForge CLI — root command group."""

from __future__ import annotations

import click

from specforge import __version__


@click.group()
@click.version_option(version=__version__, prog_name="specforge")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """SpecForge — AI-powered spec-driven development engine."""
    ctx.ensure_object(dict)


# Import and register subcommands
from specforge.cli.check_cmd import check  # noqa: E402
from specforge.cli.decompose_cmd import decompose  # noqa: E402
from specforge.cli.init_cmd import init  # noqa: E402

cli.add_command(init)
cli.add_command(check)
cli.add_command(decompose)
