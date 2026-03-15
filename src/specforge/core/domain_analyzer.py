"""Domain pattern matching, keyword scoring, and feature generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from specforge.core.config import CLARIFICATION_QUESTIONS, MIN_KEYWORD_SCORE
from specforge.core.result import Ok, Result

_GIBBERISH_RE = re.compile(r"[a-zA-Z]{2,}")
_KEBAB_RE = re.compile(r"[^a-z0-9]+")

_COMMON_WORDS: set[str] = {
    "create", "build", "make", "develop", "design", "implement",
    "app", "application", "webapp", "website", "system", "tool",
    "platform", "service", "project", "software", "program",
    "a", "an", "the", "for", "with", "and", "or", "to", "of",
    "that", "this", "from", "by", "on", "in", "is", "are", "was",
    "personal", "online", "web", "mobile", "simple", "small",
    "new", "my", "our", "management", "tracker", "manager",
    "list", "dashboard", "portal", "todo",
}


@dataclass(frozen=True)
class DomainMatch:
    """Result of domain pattern matching against a description."""

    domain_name: str
    score: int
    matched_keywords: tuple[str, ...]


@dataclass(frozen=True)
class Feature:
    """A decomposed application feature."""

    id: str
    name: str
    display_name: str
    description: str
    priority: str
    category: str
    always_separate: bool
    data_keywords: tuple[str, ...]


class DomainAnalyzer:
    """Analyzes descriptions against domain patterns to produce features."""

    def __init__(
        self,
        patterns: list[dict[str, Any]],
        generic: dict[str, Any],
    ) -> None:
        self._patterns = patterns
        self._generic = generic

    def analyze(self, description: str) -> Result:
        """Score description against all domains, return best match."""
        if self.is_gibberish(description):
            return Ok(DomainMatch("generic", 0, ()))
        best = self._score_all_domains(description)
        return Ok(best)

    def decompose(
        self,
        description: str,
        domain: DomainMatch,
    ) -> Result:
        """Generate features from matched domain pattern."""
        pattern = self._find_pattern(domain.domain_name)
        features = _build_features(pattern["features"])
        return Ok(features)

    def is_gibberish(self, description: str) -> bool:
        """Check if description is empty or nonsensical."""
        if not description or not description.strip():
            return True
        words = _GIBBERISH_RE.findall(description.lower())
        known = _COMMON_WORDS | self._all_keywords()
        real_words = [w for w in words if w in known]
        return len(real_words) < 2

    def clarify(self, description: str) -> list[str]:
        """Return clarification questions for vague input."""
        return list(CLARIFICATION_QUESTIONS)

    def _score_all_domains(self, description: str) -> DomainMatch:
        """Score description against all domains, return best."""
        tokens = _tokenize(description)
        best_name = "generic"
        best_score = 0
        best_keywords: list[str] = []

        for pattern in self._patterns:
            score, matched = _score_domain(tokens, pattern)
            if score > best_score:
                best_score = score
                best_name = pattern["name"]
                best_keywords = matched

        if best_score < MIN_KEYWORD_SCORE:
            return DomainMatch("generic", best_score, tuple(best_keywords))
        return DomainMatch(best_name, best_score, tuple(best_keywords))

    def _all_keywords(self) -> set[str]:
        """Collect all domain keywords for gibberish detection."""
        kws: set[str] = set()
        for p in self._patterns:
            for kw, _ in p["keywords"]:
                kws.add(kw)
        return kws

    def _find_pattern(self, domain_name: str) -> dict[str, Any]:
        """Find pattern by name, falling back to generic."""
        for p in self._patterns:
            if p["name"] == domain_name:
                return p
        return self._generic


def _tokenize(description: str) -> set[str]:
    """Tokenize description into lowercase words."""
    return set(description.lower().split())


def _score_domain(
    tokens: set[str],
    pattern: dict[str, Any],
) -> tuple[int, list[str]]:
    """Score tokens against a domain's weighted keywords."""
    score = 0
    matched: list[str] = []
    for keyword, weight in pattern["keywords"]:
        if keyword in tokens:
            score += weight
            matched.append(keyword)
    return score, matched


def _build_features(templates: list[dict[str, Any]]) -> list[Feature]:
    """Convert feature templates to Feature dataclasses with IDs."""
    features: list[Feature] = []
    for idx, tmpl in enumerate(templates):
        feature = Feature(
            id=f"{idx + 1:03d}",
            name=tmpl["name"],
            display_name=_to_display_name(tmpl["name"]),
            description=tmpl["description"],
            priority=tmpl["priority"],
            category=tmpl["category"],
            always_separate=tmpl["always_separate"],
            data_keywords=tuple(tmpl["data_keywords"]),
        )
        features.append(feature)
    return features


def _to_display_name(kebab_name: str) -> str:
    """Convert kebab-case to Title Case display name."""
    return " ".join(w.capitalize() for w in kebab_name.split("-"))
