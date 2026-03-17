"""Prompt-rule checker — validates governance thresholds and collects Tier 2 rules."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import THRESHOLD_KEY_MAPPING
from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
)
from specforge.core.result import Err, Ok

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PromptRuleChecker:
    """Extracts governance thresholds and collects descriptive Tier 2 rules."""

    def __init__(self, prompt_loader: object | None = None) -> None:
        self._loader = prompt_loader
        self._extracted_thresholds: dict[str, str] = {}

    @property
    def extracted_thresholds(self) -> dict[str, str]:
        """Threshold values extracted during last check, keyed by checker id."""
        return dict(self._extracted_thresholds)

    @property
    def name(self) -> str:
        return "prompt-rule"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.LINT

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.TASK,)

    def is_applicable(self, architecture: str) -> bool:
        return True

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Load governance rules and classify into Tier 1 / Tier 2."""
        if self._loader is None:
            return Ok(
                CheckResult(
                    checker_name=self.name,
                    passed=True,
                    category=self.category,
                    skipped=True,
                    skip_reason="No prompt loader configured",
                )
            )

        return self._run_check()

    # ── Private helpers ───────────────────────────────────────────────

    def _run_check(self) -> Ok[CheckResult] | Err[str]:
        """Execute the prompt-rule check with a configured loader."""
        prompt_set = self._loader.load_for_feature("")  # type: ignore[union-attr]
        if not prompt_set.ok:
            return Err(f"Failed to load prompts: {prompt_set.error}")

        tier1, tier2 = _classify_rules(prompt_set.value)
        self._apply_thresholds(tier1)
        output = _build_output(tier1, tier2)

        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=True,
                category=self.category,
                output=output,
            )
        )

    def _apply_thresholds(
        self, tier1: list[tuple[str, str]],
    ) -> None:
        """Store extracted threshold values for other checkers to read."""
        self._extracted_thresholds = {k: v for k, v in tier1}


def _classify_rules(
    prompt_set: object,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Split rules into Tier 1 (threshold-mapped) and Tier 2 (descriptive)."""
    tier1: list[tuple[str, str]] = []
    tier2: list[str] = []

    for _domain, pfile in prompt_set.files.items():  # type: ignore[union-attr]
        for rule in pfile.rules:
            _classify_single_rule(rule, tier1, tier2)

    return tier1, tier2


def _classify_single_rule(
    rule: object,
    tier1: list[tuple[str, str]],
    tier2: list[str],
) -> None:
    """Classify one rule as Tier 1 or Tier 2."""
    for threshold in rule.thresholds:  # type: ignore[union-attr]
        if threshold.key in THRESHOLD_KEY_MAPPING:
            mapped = THRESHOLD_KEY_MAPPING[threshold.key]
            tier1.append((mapped, threshold.value))
        else:
            logger.warning("Unmapped threshold key: %s", threshold.key)
            tier2.append(
                f"[{rule.rule_id}] {threshold.key}={threshold.value}"  # type: ignore[union-attr]
            )

    if not rule.thresholds:  # type: ignore[union-attr]
        tier2.append(f"[{rule.rule_id}] {rule.title}: {rule.description}")  # type: ignore[union-attr]


def _build_output(
    tier1: list[tuple[str, str]],
    tier2: list[str],
) -> str:
    """Format the checker output string."""
    parts: list[str] = []
    if tier1:
        items = ", ".join(f"{k}={v}" for k, v in tier1)
        parts.append(f"Tier 1 thresholds: {items}")
    if tier2:
        parts.append("Tier 2 context:\n" + "\n".join(tier2))
    return "\n".join(parts) if parts else "No rules found"
