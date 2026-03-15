"""PromptValidator — detects threshold conflicts across governance prompt files."""

from __future__ import annotations

from specforge.core.config import EQUAL_PRIORITY_DOMAINS
from specforge.core.prompt_models import (
    ConflictEntry,
    ConflictReport,
    PromptFile,
    PromptRule,
    PromptSet,
    PromptThreshold,
)


class PromptValidator:
    """Detects cross-file threshold conflicts in a PromptSet."""

    def detect_conflicts(self, prompt_set: PromptSet) -> ConflictReport:
        """Scan all prompt files for threshold conflicts, returning a full ConflictReport."""
        index = self._build_threshold_index(prompt_set)
        conflicts = self._find_conflicts(index, prompt_set)
        return ConflictReport(
            conflicts=tuple(conflicts),
            has_conflicts=len(conflicts) > 0,
        )

    # ── Internal helpers ────────────────────────────────────────────────

    def _build_threshold_index(
        self, prompt_set: PromptSet
    ) -> dict[str, list[tuple[str, PromptRule, PromptThreshold]]]:
        """Build index: threshold_key → [(domain, rule, threshold), ...]."""
        index: dict[str, list[tuple[str, PromptRule, PromptThreshold]]] = {}
        for domain, pf in prompt_set.files.items():
            for rule in pf.rules:
                for threshold in rule.thresholds:
                    index.setdefault(threshold.key, []).append(
                        (domain, rule, threshold)
                    )
        return index

    def _find_conflicts(
        self,
        index: dict[str, list[tuple[str, PromptRule, PromptThreshold]]],
        prompt_set: PromptSet,
    ) -> list[ConflictEntry]:
        """Compare every pair of domains that share a threshold key."""
        conflicts: list[ConflictEntry] = []
        for key, entries in index.items():
            if len(entries) < 2:
                continue
            # Compare all pairs
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    domain_a, rule_a, thresh_a = entries[i]
                    domain_b, rule_b, thresh_b = entries[j]
                    if thresh_a.value == thresh_b.value:
                        continue  # Same value — no conflict
                    pf_a = prompt_set.files[domain_a]
                    pf_b = prompt_set.files[domain_b]
                    conflict = self._make_conflict_entry(
                        key, domain_a, rule_a, thresh_a, pf_a,
                        domain_b, rule_b, thresh_b, pf_b,
                    )
                    conflicts.append(conflict)
        return conflicts

    def _make_conflict_entry(
        self,
        threshold_key: str,
        domain_a: str,
        rule_a: PromptRule,
        thresh_a: PromptThreshold,
        pf_a: PromptFile,
        domain_b: str,
        rule_b: PromptRule,
        thresh_b: PromptThreshold,
        pf_b: PromptFile,
    ) -> ConflictEntry:
        """Determine winner and ambiguity, build suggested resolution."""
        prec_a = pf_a.meta.precedence
        prec_b = pf_b.meta.precedence

        if prec_a < prec_b:
            winning_domain = domain_a
            winning_value = thresh_a.value
            is_ambiguous = False
        elif prec_b < prec_a:
            winning_domain = domain_b
            winning_value = thresh_b.value
            is_ambiguous = False
        else:
            # Equal precedence — check if truly equal-priority domains
            winning_domain = "AMBIGUOUS"
            winning_value = thresh_a.value  # Placeholder — both values shown
            is_ambiguous = True

        suggestion = self._build_suggestion(
            threshold_key, domain_a, thresh_a, domain_b, thresh_b,
            winning_domain, is_ambiguous
        )

        return ConflictEntry(
            threshold_key=threshold_key,
            rule_id_a=rule_a.rule_id,
            domain_a=domain_a,
            value_a=thresh_a.value,
            rule_id_b=rule_b.rule_id,
            domain_b=domain_b,
            value_b=thresh_b.value,
            winning_domain=winning_domain,
            winning_value=winning_value,
            is_ambiguous=is_ambiguous,
            suggested_resolution=suggestion,
        )

    def _build_suggestion(
        self,
        key: str,
        domain_a: str,
        thresh_a: PromptThreshold,
        domain_b: str,
        thresh_b: PromptThreshold,
        winning_domain: str,
        is_ambiguous: bool,
    ) -> str:
        """Build a human-readable resolution suggestion."""
        if is_ambiguous:
            return (
                f"AMBIGUOUS: '{domain_a}' sets {key}={thresh_a.value} and "
                f"'{domain_b}' sets {key}={thresh_b.value} at equal precedence. "
                f"Manually reconcile: edit one of the governance files to agree on a value, "
                f"or remove the threshold from the less-authoritative file."
            )
        loser = domain_b if winning_domain == domain_a else domain_a
        winner_val = thresh_a.value if winning_domain == domain_a else thresh_b.value
        return (
            f"Use '{winning_domain}' value ({key}={winner_val}, higher precedence). "
            f"Update '{loser}' governance file to align, or remove the threshold to avoid confusion."
        )
