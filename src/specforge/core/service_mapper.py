"""Feature-to-service mapping with affinity scoring and rationale."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from specforge.core.config import (
    AFFINITY_DIFF_FAILURE,
    AFFINITY_DIFF_SCALING,
    AFFINITY_MERGE_THRESHOLD,
    AFFINITY_SAME_CATEGORY,
    AFFINITY_SHARED_DATA,
    FAILURE_MODE,
    MAX_FEATURES_PER_SERVICE,
    SCALING_PROFILE,
)
from specforge.core.result import Ok, Result

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Service:
    """A logical service grouping features."""

    name: str
    slug: str
    feature_ids: tuple[str, ...]
    rationale: str
    communication: tuple[Any, ...] = ()


class ServiceMapper:
    """Maps features to services using affinity scoring."""

    def map_features(
        self,
        features: list,
        architecture: str,
    ) -> Result:
        """Map features to services based on architecture type."""
        if architecture == "monolithic":
            return self._map_monolithic(features)
        return self._map_services(features)

    def _map_monolithic(self, features: list) -> Result:
        """All features in a single service for monolithic."""
        ids = tuple(f.id for f in features)
        svc = Service(
            name="Application",
            slug="application",
            feature_ids=ids,
            rationale=(
                "Monolithic: all features as modules "
                "within a single application"
            ),
        )
        return Ok([svc])

    def _map_services(self, features: list) -> Result:
        """Map features to services using affinity scoring."""
        separate, remaining = self._apply_always_separate(features)
        scores = self._compute_pairwise_scores(remaining)
        merged = self._greedy_merge(remaining, scores)
        merged = self._enforce_max_features(merged, scores)
        all_services = separate + merged
        all_services = self._add_rationale(all_services, scores)
        return Ok(all_services)

    def _apply_always_separate(
        self,
        features: list,
    ) -> tuple[list[Service], list]:
        """Extract always_separate features as singleton services."""
        separate: list[Service] = []
        remaining: list = []
        for f in features:
            if f.always_separate:
                svc = _make_singleton(f, is_forced=True)
                separate.append(svc)
            else:
                remaining.append(f)
        return separate, remaining

    def _compute_pairwise_scores(
        self,
        features: list,
    ) -> dict[tuple[str, str], int]:
        """Compute pairwise affinity scores between features."""
        scores: dict[tuple[str, str], int] = {}
        for i, fa in enumerate(features):
            for fb in features[i + 1 :]:
                score = _compute_pair_score(fa, fb)
                scores[(fa.id, fb.id)] = score
                scores[(fb.id, fa.id)] = score
        return scores

    def _greedy_merge(
        self,
        features: list,
        scores: dict[tuple[str, str], int],
    ) -> list[Service]:
        """Greedily merge features with highest affinity first."""
        pairs = _sorted_pairs(features, scores)
        merged: dict[str, list[str]] = {}
        assigned: set[str] = set()

        for (id_a, id_b), score in pairs:
            if score < AFFINITY_MERGE_THRESHOLD:
                break
            if id_a in assigned or id_b in assigned:
                continue
            merged[id_a] = [id_a, id_b]
            assigned.add(id_a)
            assigned.add(id_b)

        services: list[Service] = []
        feat_map = {f.id: f for f in features}

        for _leader, members in merged.items():
            services.append(_make_group(feat_map, members))

        for f in features:
            if f.id not in assigned:
                services.append(_make_singleton(f, is_forced=False))

        return services

    def _enforce_max_features(
        self,
        services: list[Service],
        scores: dict[tuple[str, str], int],
    ) -> list[Service]:
        """Split services exceeding max feature count."""
        result: list[Service] = []
        for svc in services:
            if len(svc.feature_ids) <= MAX_FEATURES_PER_SERVICE:
                result.append(svc)
            else:
                result.extend(_split_oversized(svc, scores))
        return result

    def _add_rationale(
        self,
        services: list[Service],
        scores: dict[tuple[str, str], int],
    ) -> list[Service]:
        """Add rationale to services that lack one."""
        result: list[Service] = []
        for svc in services:
            if not svc.rationale:
                rat = _generate_rationale(svc, scores)
                svc = Service(
                    name=svc.name,
                    slug=svc.slug,
                    feature_ids=svc.feature_ids,
                    rationale=rat,
                    communication=svc.communication,
                )
            result.append(svc)
        return result


def _compute_pair_score(fa: object, fb: object) -> int:
    """Compute affinity score between two features."""
    score = 0
    if fa.category == fb.category:
        score += AFFINITY_SAME_CATEGORY
    if set(fa.data_keywords) & set(fb.data_keywords):
        score += AFFINITY_SHARED_DATA
    if SCALING_PROFILE.get(fa.category) != SCALING_PROFILE.get(fb.category):
        score += AFFINITY_DIFF_SCALING
    if FAILURE_MODE.get(fa.category) != FAILURE_MODE.get(fb.category):
        score += AFFINITY_DIFF_FAILURE
    return score


def _sorted_pairs(
    features: list,
    scores: dict[tuple[str, str], int],
) -> list[tuple[tuple[str, str], int]]:
    """Sort unique pairs by score descending."""
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[tuple[str, str], int]] = []
    for i, fa in enumerate(features):
        for fb in features[i + 1 :]:
            key = (fa.id, fb.id)
            if key not in seen:
                seen.add(key)
                pairs.append((key, scores.get(key, 0)))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs


def _make_singleton(feature: object, is_forced: bool) -> Service:
    """Create a singleton service from a feature."""
    reason = "always isolated" if is_forced else "low affinity"
    return Service(
        name=_to_service_name(feature.name),
        slug=_generate_slug(feature.name),
        feature_ids=(feature.id,),
        rationale=f"Separate: {feature.name} is {reason}",
    )


def _make_group(feat_map: dict, ids: list[str]) -> Service:
    """Create a grouped service from feature IDs."""
    first = feat_map[ids[0]]
    return Service(
        name=_to_service_name(first.name),
        slug=_generate_slug(first.name),
        feature_ids=tuple(ids),
        rationale="",
    )


def _split_oversized(
    svc: Service,
    scores: dict[tuple[str, str], int],
) -> list[Service]:
    """Split an oversized service, keeping top-4 and ejecting rest."""
    ids = list(svc.feature_ids)
    keep = ids[:MAX_FEATURES_PER_SERVICE]
    eject = ids[MAX_FEATURES_PER_SERVICE:]
    kept = Service(
        name=svc.name,
        slug=svc.slug,
        feature_ids=tuple(keep),
        rationale=svc.rationale,
        communication=svc.communication,
    )
    ejected: list[Service] = []
    for fid in eject:
        ejected.append(
            Service(
                name=f"{svc.name} Overflow",
                slug=f"{svc.slug}-overflow",
                feature_ids=(fid,),
                rationale=f"Separate: split from {svc.name} (max cap)",
            )
        )
    return [kept, *ejected]


def _generate_rationale(
    svc: Service,
    scores: dict[tuple[str, str], int],
) -> str:
    """Generate WHY COMBINED or WHY SEPARATE rationale."""
    if len(svc.feature_ids) == 1:
        return f"Separate: {svc.name} standalone service"
    ids = list(svc.feature_ids)
    return (
        f"Combined: shared bounded context "
        f"({', '.join(ids)})"
    )


def _generate_slug(name: str) -> str:
    """Generate kebab-case slug from a name."""
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug or "service"


def _to_service_name(kebab: str) -> str:
    """Convert kebab-case to Service Title."""
    return " ".join(w.capitalize() for w in kebab.split("-")) + " Service"
