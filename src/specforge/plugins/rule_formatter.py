"""Rule formatter — renders PluginRule lists to governance-compatible markdown."""

from __future__ import annotations

from jinja2 import Environment, PackageLoader

from specforge.plugins.stack_plugin_base import PluginRule


def format_plugin_rules(rules: list[PluginRule]) -> str:
    """Format PluginRule list to governance-compatible markdown."""
    if not rules:
        return ""
    env = Environment(
        loader=PackageLoader("specforge", "templates/base/governance"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("plugin_rule_block.md.j2")
    return template.render(rules=rules)
