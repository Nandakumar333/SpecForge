"""EffortEstimator — T-shirt sizing for task generation (Feature 008)."""

from __future__ import annotations

from specforge.core.config import (
    EFFORT_BUMP_TABLE,
    EFFORT_BUMP_THRESHOLD_DEPS,
    EFFORT_BUMP_THRESHOLD_FEATURES,
    EFFORT_SIZES,
)
from specforge.core.task_models import BuildStep, EffortSize


def _bump_size(current: str) -> str:
    """Bump effort by one level. Cap at XL."""
    idx = EFFORT_SIZES.index(current)
    return EFFORT_SIZES[min(idx + 1, len(EFFORT_SIZES) - 1)]


class EffortEstimator:
    """Assigns T-shirt effort estimates to tasks."""

    def estimate(
        self,
        step: BuildStep,
        feature_count: int,
        dependency_count: int,
    ) -> EffortSize:
        """Estimate effort for a build step."""
        return self._compute(
            step.category, step.default_effort,
            feature_count, dependency_count,
        )

    def _compute(
        self,
        category: str,
        default_effort: str,
        feature_count: int,
        dependency_count: int,
    ) -> EffortSize:
        """Apply bump rules from the effort table."""
        table_entry = EFFORT_BUMP_TABLE.get(category)
        if table_entry is None:
            return default_effort  # type: ignore[return-value]

        base, mid, high = table_entry
        if feature_count >= 5:  # noqa: PLR2004
            result = high
        elif feature_count > EFFORT_BUMP_THRESHOLD_FEATURES:
            result = mid
        else:
            result = base

        if (
            category == "communication_clients"
            and dependency_count > EFFORT_BUMP_THRESHOLD_DEPS
        ):
            result = _bump_size(result)

        # Cap at XL
        if EFFORT_SIZES.index(result) > EFFORT_SIZES.index("XL"):
            return "XL"
        return result  # type: ignore[return-value]
