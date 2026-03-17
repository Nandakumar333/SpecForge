"""Edge case budget allocation and prioritization (Feature 007)."""

from __future__ import annotations

from specforge.core.config import (
    EDGE_CASE_BASE_COUNT,
    EDGE_CASE_CATEGORY_PRIORITY,
    EDGE_CASE_MAX_PER_SERVICE,
    EDGE_CASE_PER_DEPENDENCY,
    EDGE_CASE_PER_EVENT,
    EDGE_CASE_PER_EXTRA_FEATURE,
)
from specforge.core.edge_case_models import EdgeCase

SEVERITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class EdgeCaseBudget:
    """Computes budget and prioritizes edge cases within cap."""

    def allocate(
        self,
        deps_count: int,
        events_count: int,
        features_count: int,
    ) -> int:
        """Return the edge case budget for given service topology."""
        raw = (
            EDGE_CASE_BASE_COUNT
            + EDGE_CASE_PER_DEPENDENCY * deps_count
            + EDGE_CASE_PER_EVENT * events_count
            + EDGE_CASE_PER_EXTRA_FEATURE * max(0, features_count - 1)
        )
        return min(raw, EDGE_CASE_MAX_PER_SERVICE)

    def prioritize(
        self,
        cases: tuple[EdgeCase, ...],
        budget: int,
    ) -> tuple[EdgeCase, ...]:
        """Sort by severity then category priority; truncate to budget."""
        sorted_cases = sorted(cases, key=self._sort_key)
        return tuple(sorted_cases[:budget])

    @staticmethod
    def _sort_key(case: EdgeCase) -> tuple[int, int]:
        """Return (severity_rank, category_priority) for sorting."""
        sev = SEVERITY_ORDER.get(case.severity, 99)
        cat = EDGE_CASE_CATEGORY_PRIORITY.get(case.category, 99)
        return (sev, cat)
