"""Architecture-based edge case pattern filter (Feature 007)."""

from __future__ import annotations

import warnings

from specforge.core.config import (
    MODULAR_MONOLITH_EXTRA_CATEGORIES,
    STANDARD_EDGE_CASE_CATEGORIES,
)
from specforge.core.edge_case_models import EdgeCasePattern

_VALID_ARCHITECTURES = {"microservice", "monolithic", "modular-monolith"}


class ArchitectureEdgeCaseFilter:
    """Filters edge case patterns by architecture type."""

    def __init__(self, architecture: str) -> None:
        self._architecture = architecture

    @property
    def architecture(self) -> str:
        """Return the architecture this filter was configured for."""
        return self._architecture

    def filter_patterns(
        self,
        patterns: tuple[EdgeCasePattern, ...],
    ) -> tuple[EdgeCasePattern, ...]:
        """Keep only patterns relevant to the configured architecture."""
        if self._architecture == "microservice":
            return patterns
        if self._architecture == "monolithic":
            return self._keep_standard(patterns)
        if self._architecture == "modular-monolith":
            return self._keep_modular(patterns)
        return self._fallback_monolith(patterns)

    def _keep_standard(
        self,
        patterns: tuple[EdgeCasePattern, ...],
    ) -> tuple[EdgeCasePattern, ...]:
        """Monolith: keep only standard categories."""
        allowed = set(STANDARD_EDGE_CASE_CATEGORIES)
        return tuple(p for p in patterns if p.category in allowed)

    def _keep_modular(
        self,
        patterns: tuple[EdgeCasePattern, ...],
    ) -> tuple[EdgeCasePattern, ...]:
        """Modular-monolith: standard + interface_contract_violation."""
        allowed = set(STANDARD_EDGE_CASE_CATEGORIES) | set(
            MODULAR_MONOLITH_EXTRA_CATEGORIES,
        )
        return tuple(p for p in patterns if p.category in allowed)

    def _fallback_monolith(
        self,
        patterns: tuple[EdgeCasePattern, ...],
    ) -> tuple[EdgeCasePattern, ...]:
        """Unknown architecture: fall back to monolith with warning."""
        warnings.warn(
            f"Unknown architecture '{self._architecture}', "
            "falling back to monolithic edge case filter",
            UserWarning,
            stacklevel=2,
        )
        return self._keep_standard(patterns)
