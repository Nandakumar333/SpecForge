"""Unit tests for ServiceMapper (UT-004 through UT-008)."""

from __future__ import annotations

from specforge.core.domain_analyzer import Feature
from specforge.core.service_mapper import ServiceMapper


def _feat(
    fid: str,
    name: str,
    category: str = "core",
    always_separate: bool = False,
    data_keywords: tuple[str, ...] = (),
) -> Feature:
    return Feature(
        id=fid,
        name=name,
        display_name=name.replace("-", " ").title(),
        description=f"Test {name}",
        priority="P1",
        category=category,
        always_separate=always_separate,
        data_keywords=data_keywords,
    )


class TestAffinityScoring:
    """UT-004: pairwise affinity scoring."""

    def test_same_category_gives_plus_3(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "a", category="core")
        f2 = _feat("002", "b", category="core")
        scores = mapper._compute_pairwise_scores([f1, f2])
        assert scores[("001", "002")] >= 3

    def test_shared_data_keywords_gives_plus_2(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "a", data_keywords=("user", "account"))
        f2 = _feat("002", "b", data_keywords=("account", "balance"))
        scores = mapper._compute_pairwise_scores([f1, f2])
        assert scores[("001", "002")] >= 2

    def test_different_scaling_gives_minus_2(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "a", category="foundation")  # low
        f2 = _feat("002", "b", category="integration")  # high-variance
        scores = mapper._compute_pairwise_scores([f1, f2])
        assert scores[("001", "002")] <= -2

    def test_different_failure_mode_gives_minus_2(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "a", category="foundation")  # infrastructure
        f2 = _feat("002", "b", category="core")  # business-logic
        scores = mapper._compute_pairwise_scores([f1, f2])
        # Different failure + different scaling
        assert scores[("001", "002")] < 0


class TestAlwaysSeparate:
    """UT-005: always_separate rules."""

    def test_auth_always_separate(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "auth", always_separate=True)
        f2 = _feat("002", "crud", category="core")
        result = mapper.map_features([f1, f2], "microservice")
        assert result.ok
        auth_svc = [s for s in result.value if "001" in s.feature_ids]
        assert len(auth_svc) == 1
        assert len(auth_svc[0].feature_ids) == 1

    def test_notification_always_separate(self) -> None:
        mapper = ServiceMapper()
        f_notif = _feat("001", "notifications", always_separate=True)
        f_core = _feat("002", "crud", category="core")
        f_core2 = _feat("003", "reports", category="core")
        result = mapper.map_features([f_notif, f_core, f_core2], "microservice")
        assert result.ok
        notif_svc = [s for s in result.value if "001" in s.feature_ids]
        assert len(notif_svc[0].feature_ids) == 1


class TestGreedyMerge:
    """UT-006: greedy merge for affinity >= 3."""

    def test_high_affinity_features_combined(self) -> None:
        mapper = ServiceMapper()
        # Same category = +3, should merge
        f1 = _feat("001", "a", category="core", data_keywords=("x",))
        f2 = _feat("002", "b", category="core", data_keywords=("x",))
        f3 = _feat("003", "c", category="admin", data_keywords=("y",))
        result = mapper.map_features([f1, f2, f3], "microservice")
        assert result.ok
        # f1 and f2 should be in same service
        for svc in result.value:
            if "001" in svc.feature_ids:
                assert "002" in svc.feature_ids

    def test_low_affinity_features_separate(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "a", category="foundation", data_keywords=("x",))
        f2 = _feat("002", "b", category="integration", data_keywords=("y",))
        result = mapper.map_features([f1, f2], "microservice")
        assert result.ok
        for svc in result.value:
            assert len(svc.feature_ids) == 1


class TestMaxFeaturesCap:
    """UT-007: max 4 features per service."""

    def test_service_cannot_exceed_4_features(self) -> None:
        mapper = ServiceMapper()
        features = [
            _feat(f"{i:03d}", f"f{i}", category="core", data_keywords=("shared",))
            for i in range(1, 7)
        ]
        result = mapper.map_features(features, "microservice")
        assert result.ok
        for svc in result.value:
            assert len(svc.feature_ids) <= 4


class TestRationaleGeneration:
    """UT-008: every service gets WHY COMBINED or WHY SEPARATE."""

    def test_every_service_has_rationale(self) -> None:
        mapper = ServiceMapper()
        features = [
            _feat("001", "auth", always_separate=True),
            _feat("002", "ledger", category="core", data_keywords=("account",)),
            _feat("003", "budget", category="core", data_keywords=("account",)),
        ]
        result = mapper.map_features(features, "microservice")
        assert result.ok
        for svc in result.value:
            assert svc.rationale, f"Service {svc.name} has no rationale"
            assert (
                "combined" in svc.rationale.lower()
                or "separate" in svc.rationale.lower()
            )

    def test_singleton_gets_separate_rationale(self) -> None:
        mapper = ServiceMapper()
        f1 = _feat("001", "auth", always_separate=True)
        result = mapper.map_features([f1], "microservice")
        assert result.ok
        assert "separate" in result.value[0].rationale.lower()


class TestMonolithicMapping:
    """Monolithic architecture produces single service."""

    def test_monolithic_single_service(self) -> None:
        mapper = ServiceMapper()
        features = [
            _feat("001", "auth"),
            _feat("002", "crud"),
        ]
        result = mapper.map_features(features, "monolithic")
        assert result.ok
        assert len(result.value) == 1
        assert len(result.value[0].feature_ids) == 2
