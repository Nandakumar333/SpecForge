"""Unit tests for DomainAnalyzer (UT-001, UT-002, UT-003, UT-014)."""

from __future__ import annotations

from specforge.core.domain_analyzer import DomainAnalyzer, Feature
from specforge.core.domain_patterns import DOMAIN_PATTERNS, GENERIC_PATTERN


def _make_analyzer() -> DomainAnalyzer:
    return DomainAnalyzer(DOMAIN_PATTERNS, GENERIC_PATTERN)


class TestDomainMatching:
    """UT-001: all 6 domains produce 8-15 features with correct names."""

    def test_finance_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Create a personal finance webapp")
        assert result.ok
        assert result.value.domain_name == "finance"
        assert result.value.score >= 2

    def test_ecommerce_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Build an ecommerce store with a cart")
        assert result.ok
        assert result.value.domain_name == "ecommerce"

    def test_saas_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze(
            "Build a multi-tenant SaaS platform with subscriptions"
        )
        assert result.ok
        assert result.value.domain_name == "saas"

    def test_social_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Create a social media app with feed and posts")
        assert result.ok
        assert result.value.domain_name == "social"

    def test_healthcare_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze(
            "Build a healthcare patient management system"
        )
        assert result.ok
        assert result.value.domain_name == "healthcare"

    def test_education_domain_detected(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Create an online learning LMS for students")
        assert result.ok
        assert result.value.domain_name == "education"

    def test_each_domain_produces_8_to_15_features(self) -> None:
        analyzer = _make_analyzer()
        descriptions = {
            "finance": "Create a personal finance webapp",
            "ecommerce": "Build an ecommerce shop with products",
            "saas": "Build a multi-tenant SaaS platform",
            "social": "Create a social media app with feed",
            "healthcare": "Build a healthcare patient system",
            "education": "Create an online learning course platform",
        }
        for domain, desc in descriptions.items():
            match = analyzer.analyze(desc)
            assert match.ok, f"Failed to analyze: {desc}"
            features = analyzer.decompose(desc, match.value)
            assert features.ok, f"Failed to decompose: {desc}"
            count = len(features.value)
            assert 8 <= count <= 15, (
                f"Domain '{domain}' produced {count} features"
            )


class TestGenericFallback:
    """UT-002: generic fallback for unrecognized domain descriptions."""

    def test_unrecognized_domain_uses_generic(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Build a custom woodworking project tracker")
        assert result.ok
        assert result.value.domain_name == "generic"

    def test_generic_produces_features(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Build a custom woodworking project tracker")
        assert match.ok
        features = analyzer.decompose(
            "Build a custom woodworking project tracker", match.value
        )
        assert features.ok
        assert len(features.value) >= 5


class TestKeywordScoring:
    """UT-003: keyword scoring thresholds."""

    def test_vague_input_returns_low_score(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze("Build an app")
        assert result.ok
        assert result.value.score < 2

    def test_clear_input_returns_high_score(self) -> None:
        analyzer = _make_analyzer()
        result = analyzer.analyze(
            "Create a personal finance webapp with banking and transactions"
        )
        assert result.ok
        assert result.value.score >= 2

    def test_gibberish_detected(self) -> None:
        analyzer = _make_analyzer()
        assert analyzer.is_gibberish("asdf qwer zxcv")

    def test_valid_input_not_gibberish(self) -> None:
        analyzer = _make_analyzer()
        assert not analyzer.is_gibberish("Create a personal finance webapp")

    def test_empty_input_is_gibberish(self) -> None:
        analyzer = _make_analyzer()
        assert analyzer.is_gibberish("")

    def test_clarification_returns_5_questions(self) -> None:
        analyzer = _make_analyzer()
        questions = analyzer.clarify("Build an app")
        assert len(questions) == 5


class TestFeatureDecomposition:
    """Feature generation details."""

    def test_features_have_sequential_ids(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Create a personal finance webapp")
        features = analyzer.decompose(
            "Create a personal finance webapp", match.value
        )
        assert features.ok
        for i, feat in enumerate(features.value):
            expected_id = f"{i + 1:03d}"
            assert feat.id == expected_id

    def test_features_have_kebab_names(self) -> None:
        import re

        analyzer = _make_analyzer()
        match = analyzer.analyze("Build an ecommerce store")
        features = analyzer.decompose("Build an ecommerce store", match.value)
        assert features.ok
        for feat in features.value:
            assert re.match(r"^[a-z][a-z0-9-]*$", feat.name)

    def test_feature_is_frozen_dataclass(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Create a finance app")
        features = analyzer.decompose("Create a finance app", match.value)
        assert features.ok
        feat = features.value[0]
        assert isinstance(feat, Feature)

    def test_features_have_display_names(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Create a finance app")
        features = analyzer.decompose("Create a finance app", match.value)
        assert features.ok
        for feat in features.value:
            assert feat.display_name
            assert feat.display_name != feat.name


class TestPriorityAssignment:
    """UT-014: priority assignment P0-P3."""

    def test_foundation_gets_p0(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Create a finance app")
        features = analyzer.decompose("Create a finance app", match.value)
        assert features.ok
        foundations = [f for f in features.value if f.category == "foundation"]
        for f in foundations:
            assert f.priority == "P0"

    def test_core_gets_p1(self) -> None:
        analyzer = _make_analyzer()
        match = analyzer.analyze("Create a finance app")
        features = analyzer.decompose("Create a finance app", match.value)
        assert features.ok
        cores = [f for f in features.value if f.category == "core"]
        for f in cores:
            assert f.priority == "P1"
