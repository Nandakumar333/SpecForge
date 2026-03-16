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
from specforge.cli.clarify_cmd import clarify  # noqa: E402
from specforge.cli.decompose_cmd import decompose  # noqa: E402
from specforge.cli.init_cmd import init  # noqa: E402
from specforge.cli.pipeline_status_cmd import pipeline_status  # noqa: E402
from specforge.cli.research_cmd import research  # noqa: E402
from specforge.cli.specify_cmd import specify  # noqa: E402
from specforge.cli.validate_prompts_cmd import validate_prompts  # noqa: E402

cli.add_command(init)
cli.add_command(check)
cli.add_command(decompose)
cli.add_command(validate_prompts)
cli.add_command(specify)
cli.add_command(pipeline_status)
cli.add_command(clarify)
cli.add_command(research)
