"""GovernanceReader — read-only prompt rule extraction (Feature 008)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specforge.core.config import GOVERNANCE_SCOPE_TO_LAYERS

if TYPE_CHECKING:
    from specforge.core.prompt_loader import PromptLoader


class GovernanceReader:
    """Reads governance rules to inform task descriptions (read-only)."""

    def __init__(self, prompt_loader: PromptLoader) -> None:
        self._loader = prompt_loader

    def get_relevant_rules(
        self, layer: str, architecture: str,
    ) -> tuple[str, ...]:
        """Return rule IDs relevant to a task layer."""
        result = self._loader.load_for_feature("*")
        if not result.ok:
            return ()
        prompt_set = result.value
        matching_domains = self._domains_for_layer(layer)
        if not matching_domains:
            return ()
        return self._collect_rule_ids(prompt_set, matching_domains)

    def _domains_for_layer(self, layer: str) -> tuple[str, ...]:
        """Find governance domains that apply to a task layer."""
        domains: list[str] = []
        for domain, layers in GOVERNANCE_SCOPE_TO_LAYERS.items():
            if layer in layers:
                domains.append(domain)
        return tuple(domains)

    def _collect_rule_ids(
        self, prompt_set: object, domains: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Extract rule IDs from matching governance domains."""
        rule_ids: list[str] = []
        files = getattr(prompt_set, "files", {})
        for domain in domains:
            pf = files.get(domain)
            if pf is None:
                continue
            for rule in pf.rules:
                rule_ids.append(rule.rule_id)
        return tuple(sorted(set(rule_ids)))
