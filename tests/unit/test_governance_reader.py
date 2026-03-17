"""Tests for GovernanceReader — read-only prompt rule extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specforge.core.result import Err, Ok


def _make_prompt_set(rules_by_domain: dict[str, list]) -> MagicMock:
    """Build a mock PromptSet with given domain→rules mapping."""
    prompt_set = MagicMock()
    files = {}
    for domain, rules in rules_by_domain.items():
        pf = MagicMock()
        pf.rules = tuple(rules)
        pf.meta = MagicMock()
        pf.meta.domain = domain
        files[domain] = pf
    prompt_set.files = files
    prompt_set.precedence = list(rules_by_domain.keys())
    return prompt_set


def _make_rule(rule_id: str, scope: str = "backend") -> MagicMock:
    """Build a mock PromptRule."""
    rule = MagicMock()
    rule.rule_id = rule_id
    rule.scope = scope
    rule.severity = "ERROR"
    return rule


class TestGovernanceReaderRules:
    """GovernanceReader.get_relevant_rules() tests."""

    def test_returns_matching_rules(self) -> None:
        from specforge.core.governance_reader import GovernanceReader

        loader = MagicMock()
        loader.load_for_feature.return_value = Ok(
            _make_prompt_set({
                "backend": [_make_rule("BACK-001")],
                "architecture": [_make_rule("ARCH-001")],
            })
        )
        reader = GovernanceReader(loader)
        rules = reader.get_relevant_rules("service_layer", "microservice")
        assert "BACK-001" in rules
        assert "ARCH-001" in rules

    def test_empty_when_no_governance_files(self) -> None:
        from specforge.core.governance_reader import GovernanceReader

        loader = MagicMock()
        loader.load_for_feature.return_value = Err("No files found")
        reader = GovernanceReader(loader)
        rules = reader.get_relevant_rules("domain_models", "microservice")
        assert rules == ()

    def test_filters_by_layer(self) -> None:
        from specforge.core.governance_reader import GovernanceReader

        loader = MagicMock()
        loader.load_for_feature.return_value = Ok(
            _make_prompt_set({
                "backend": [_make_rule("BACK-001")],
                "testing": [_make_rule("TEST-001")],
            })
        )
        reader = GovernanceReader(loader)
        # scaffolding layer should match architecture, not testing
        rules = reader.get_relevant_rules("scaffolding", "microservice")
        assert "TEST-001" not in rules

    def test_unmapped_layer_returns_empty(self) -> None:
        from specforge.core.governance_reader import GovernanceReader

        loader = MagicMock()
        loader.load_for_feature.return_value = Ok(
            _make_prompt_set({"backend": [_make_rule("BACK-001")]})
        )
        reader = GovernanceReader(loader)
        rules = reader.get_relevant_rules("unknown_layer", "microservice")
        assert rules == ()

    def test_read_only_contract(self, tmp_path: Path) -> None:
        """GovernanceReader never writes to prompts directory."""
        from specforge.core.governance_reader import GovernanceReader

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        before = set(prompts_dir.iterdir())

        loader = MagicMock()
        loader.load_for_feature.return_value = Err("No files")
        reader = GovernanceReader(loader)
        reader.get_relevant_rules("service_layer", "microservice")

        after = set(prompts_dir.iterdir())
        assert before == after
