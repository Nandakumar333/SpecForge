"""BoundaryAnalyzer — cross-service entity detection via manifest analysis."""

from __future__ import annotations

import re

from specforge.core.clarification_models import AmbiguityMatch
from specforge.core.config import (
    BOUNDARY_STOP_WORDS,
    REMAP_QUESTION_TOPICS,
    UBIQUITY_THRESHOLD,
)


class BoundaryAnalyzer:
    """Detects concepts shared across service boundaries."""

    def __init__(self, manifest: dict) -> None:
        self._manifest = manifest
        self._service_keywords: dict[str, set[str]] = {}
        self._build_keyword_index()

    def analyze(self, service_slug: str) -> tuple[AmbiguityMatch, ...]:
        """Find concepts in target service shared with other services."""
        target_kw = self._service_keywords.get(service_slug, set())
        if not target_kw:
            return ()
        total_services = len(self._service_keywords)
        matches: list[AmbiguityMatch] = []
        for keyword in sorted(target_kw):
            sharing = self._services_sharing(keyword, service_slug)
            if not sharing:
                continue
            if self._is_ubiquitous(keyword, total_services):
                continue
            for _other_slug in sharing:
                matches.append(AmbiguityMatch(
                    text=keyword,
                    line_number=0,
                    category="service_boundary",
                    pattern_type="missing_boundary",
                    confidence=0.8,
                ))
        return tuple(matches)

    def detect_remap(self, manifest: dict) -> bool:
        """Check whether an architecture remap has occurred."""
        prev = manifest.get("previous_architecture")
        current = manifest.get("architecture")
        if prev is None or current is None:
            return False
        return prev != current

    def get_remap_questions(
        self, service_slug: str,
    ) -> tuple[AmbiguityMatch, ...]:
        """Generate architecture-change AmbiguityMatch entries."""
        category_map = {
            "service boundaries": "service_boundary",
            "communication patterns": "communication",
            "data ownership": "service_boundary",
            "shared state": "service_boundary",
            "eventual consistency": "communication",
        }
        matches: list[AmbiguityMatch] = []
        for topic in REMAP_QUESTION_TOPICS:
            cat = category_map.get(topic, "service_boundary")
            matches.append(AmbiguityMatch(
                text=f"Architecture change: {topic} for {service_slug}",
                line_number=0,
                category=cat,
                pattern_type="arch_change",
                confidence=1.0,
            ))
        return tuple(matches)

    # ── Private helpers ─────────────────────────────────────────────

    def _build_keyword_index(self) -> None:
        """Extract keywords per service from feature descriptions."""
        services = self._manifest.get("services", [])
        feature_map = _build_feature_map(self._manifest)
        for svc in services:
            slug = svc.get("slug", "")
            keywords: set[str] = set()
            for fid in svc.get("features", []):
                feat = feature_map.get(fid, {})
                desc = feat.get("description", "")
                keywords.update(_extract_keywords(desc))
            self._service_keywords[slug] = keywords

    def _services_sharing(
        self, keyword: str, exclude_slug: str,
    ) -> list[str]:
        """Return other service slugs that also have this keyword."""
        return [
            slug for slug, kw in self._service_keywords.items()
            if slug != exclude_slug and keyword in kw
        ]

    def _is_ubiquitous(self, keyword: str, total: int) -> bool:
        """True if the keyword appears in > UBIQUITY_THRESHOLD services.

        For 2-service manifests, shared concepts are always relevant
        since they represent a genuine boundary decision.
        """
        if total <= 2:
            return False
        count = sum(
            1 for kw in self._service_keywords.values() if keyword in kw
        )
        return count / total > UBIQUITY_THRESHOLD


def _build_feature_map(manifest: dict) -> dict[str, dict]:
    """Map feature IDs to their full feature dicts."""
    return {
        f.get("id", ""): f for f in manifest.get("features", [])
    }


def _extract_keywords(text: str) -> set[str]:
    """Split text into normalized keywords with basic stemming."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    keywords: set[str] = set()
    for word in words:
        if word in BOUNDARY_STOP_WORDS or len(word) < 3:
            continue
        keywords.add(_stem(word))
    return keywords


def _stem(word: str) -> str:
    """Basic English stemming: strip trailing s/es, normalize ies→y."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word
