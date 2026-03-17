"""YAML pattern loader for edge case analysis (Feature 007)."""

from __future__ import annotations

import importlib.resources
from typing import Any

import yaml

from specforge.core.edge_case_models import EdgeCasePattern
from specforge.core.result import Err, Ok, Result


class PatternLoader:
    """Loads edge case patterns from bundled YAML files."""

    def __init__(self) -> None:
        self._cache: tuple[EdgeCasePattern, ...] | None = None

    def load_patterns(self) -> Result[tuple[EdgeCasePattern, ...], str]:
        """Load all YAML pattern files, returning cached result."""
        if self._cache is not None:
            return Ok(self._cache)
        return self._load_and_cache()

    def _load_and_cache(self) -> Result[tuple[EdgeCasePattern, ...], str]:
        """Discover and parse all YAML files in the patterns package."""
        try:
            patterns = self._discover_and_parse()
            self._cache = tuple(patterns)
            return Ok(self._cache)
        except Exception as e:
            return Err(f"Failed to load patterns: {e}")

    def _discover_and_parse(self) -> list[EdgeCasePattern]:
        """Iterate YAML files in the package and parse each."""
        pkg = importlib.resources.files(
            "specforge.knowledge.edge_case_patterns",
        )
        patterns: list[EdgeCasePattern] = []
        for resource in sorted(pkg.iterdir()):
            if not resource.name.endswith(".yaml"):
                continue
            parsed = self._parse_file(resource)
            patterns.extend(parsed)
        return patterns

    def _parse_file(self, resource: Any) -> list[EdgeCasePattern]:
        """Parse a single YAML file into EdgeCasePattern instances."""
        text = resource.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        category = data["category"]
        return [
            self._map_scenario(category, s)
            for s in data.get("scenarios", [])
        ]

    @staticmethod
    def _map_scenario(
        category: str,
        scenario: dict[str, Any],
    ) -> EdgeCasePattern:
        """Convert a YAML scenario dict to an EdgeCasePattern."""
        return EdgeCasePattern(
            category=category,
            scenario_template=scenario["scenario_template"],
            trigger_template=scenario["trigger_template"],
            handling_strategies=tuple(
                scenario.get("handling_strategies", []),
            ),
            severity_microservice=scenario.get("severity_microservice"),
            severity_monolith=scenario.get("severity_monolith"),
            test_template=scenario["test_template"],
            applicable_patterns=tuple(
                scenario.get("applicable_patterns", []),
            ),
        )
