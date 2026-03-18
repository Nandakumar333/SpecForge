"""Snapshot tests for stack plugin rule output."""

from __future__ import annotations

import pytest

from specforge.plugins.rule_formatter import format_plugin_rules
from specforge.plugins.stacks.dotnet_plugin import DotnetPlugin
from specforge.plugins.stacks.nodejs_plugin import NodejsPlugin
from specforge.plugins.stacks.python_plugin import PythonPlugin

PLUGINS = [DotnetPlugin(), PythonPlugin(), NodejsPlugin()]
ARCHS = ["microservice", "monolithic", "modular-monolith"]


@pytest.mark.parametrize("plugin", PLUGINS, ids=lambda p: p.plugin_name)
@pytest.mark.parametrize("arch", ARCHS)
def test_plugin_rules_snapshot(
    plugin: DotnetPlugin | PythonPlugin | NodejsPlugin,
    arch: str,
    snapshot: object,
) -> None:
    rules = plugin.get_prompt_rules(arch)
    all_rules = []
    for domain_rules in rules.values():
        all_rules.extend(domain_rules)
    formatted = format_plugin_rules(all_rules)
    assert formatted == snapshot
