"""SpecForge CLI — root command group."""

from __future__ import annotations

import click

from specforge import __version__


@click.group()
@click.version_option(version=__version__, prog_name="specforge")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """SpecForge -- AI-powered spec-driven development engine.

    \b
    Workflow:
      init       Scaffold a new project
      decompose  Break app description into features & services
      specify    Generate spec artifacts for a service
      implement  Execute tasks to build the services
      status     View project-wide progress dashboard
    """
    ctx.ensure_object(dict)


# Import and register subcommands
from specforge.cli.decompose_cmd import decompose  # noqa: E402
from specforge.cli.forge_cmd import forge  # noqa: E402
from specforge.cli.implement_cmd import implement  # noqa: E402
from specforge.cli.init_cmd import init  # noqa: E402
from specforge.cli.plugins_cmd import plugins  # noqa: E402
from specforge.cli.specify_cmd import specify  # noqa: E402
from specforge.cli.status_cmd import status  # noqa: E402

cli.add_command(init)
cli.add_command(decompose)
cli.add_command(specify)
cli.add_command(implement)
cli.add_command(status)
cli.add_command(plugins)
cli.add_command(forge)
