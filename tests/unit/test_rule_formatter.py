"""Unit tests for rule_formatter — format_plugin_rules()."""

from __future__ import annotations

from specforge.plugins.stack_plugin_base import PluginRule


def _make_rule(
    rule_id: str = "BACK-001",
    title: str = "Test Rule",
    severity: str = "ERROR",
    scope: str = "all files",
    description: str = "All code MUST follow this rule.",
    thresholds: dict[str, str] | None = None,
    example_correct: str = "# correct",
    example_incorrect: str = "# incorrect",
) -> PluginRule:
    return PluginRule(
        rule_id=rule_id,
        title=title,
        severity=severity,
        scope=scope,
        description=description,
        thresholds=thresholds or {},
        example_correct=example_correct,
        example_incorrect=example_incorrect,
    )


class TestFormatSingleRule:
    """Single rule rendering."""

    def test_contains_rule_id_and_title(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(rule_id="BACK-001", title="My Rule")
        output = format_plugin_rules([rule])
        assert "### BACK-001: My Rule" in output

    def test_contains_severity(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(severity="WARNING")
        output = format_plugin_rules([rule])
        assert "severity: WARNING" in output

    def test_contains_scope(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(scope="all endpoints")
        output = format_plugin_rules([rule])
        assert "scope: all endpoints" in output

    def test_contains_description(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(description="Must use HTTPS.")
        output = format_plugin_rules([rule])
        assert "rule: Must use HTTPS." in output

    def test_contains_examples(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(
            example_correct="https://api.example.com",
            example_incorrect="http://api.example.com",
        )
        output = format_plugin_rules([rule])
        assert "example_correct:" in output
        assert "https://api.example.com" in output
        assert "example_incorrect:" in output
        assert "http://api.example.com" in output


class TestFormatThresholds:
    """Threshold rendering."""

    def test_empty_thresholds(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(thresholds={})
        output = format_plugin_rules([rule])
        assert "threshold:" not in output

    def test_single_threshold(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(thresholds={"max_lines": "30"})
        output = format_plugin_rules([rule])
        assert "threshold: max_lines=30" in output

    def test_multiple_thresholds(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(thresholds={"max_lines": "30", "min_cov": "80"})
        output = format_plugin_rules([rule])
        assert "max_lines=30" in output
        assert "min_cov=80" in output


class TestFormatMultipleRules:
    """Multiple rules concatenated."""

    def test_two_rules_both_present(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        r1 = _make_rule(rule_id="BACK-001", title="First")
        r2 = _make_rule(rule_id="BACK-002", title="Second")
        output = format_plugin_rules([r1, r2])
        assert "### BACK-001: First" in output
        assert "### BACK-002: Second" in output

    def test_rules_appear_in_order(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        r1 = _make_rule(rule_id="BACK-001", title="First")
        r2 = _make_rule(rule_id="BACK-002", title="Second")
        output = format_plugin_rules([r1, r2])
        assert output.index("BACK-001") < output.index("BACK-002")


class TestFormatEdgeCases:
    """Edge cases for format_plugin_rules."""

    def test_empty_list_returns_empty(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        output = format_plugin_rules([])
        assert output.strip() == ""

    def test_multiline_example(self) -> None:
        from specforge.plugins.rule_formatter import format_plugin_rules

        rule = _make_rule(
            example_correct="line1\nline2\nline3",
            example_incorrect="bad1\nbad2",
        )
        output = format_plugin_rules([rule])
        assert "line1" in output
        assert "line2" in output
        assert "bad1" in output
