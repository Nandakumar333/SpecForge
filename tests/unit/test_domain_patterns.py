"""Unit tests for domain pattern data integrity."""

from __future__ import annotations

from specforge.core.config import FEATURE_CATEGORIES, FEATURE_PRIORITIES
from specforge.core.domain_patterns import DOMAIN_PATTERNS, GENERIC_PATTERN


class TestDomainPatternStructure:
    """Validate structure and constraints of all domain patterns."""

    def test_six_built_in_domains(self) -> None:
        names = [p["name"] for p in DOMAIN_PATTERNS]
        assert len(names) == 6
        assert set(names) == {
            "finance",
            "ecommerce",
            "saas",
            "social",
            "healthcare",
            "education",
        }

    def test_generic_fallback_exists(self) -> None:
        assert GENERIC_PATTERN["name"] == "generic"
        assert len(GENERIC_PATTERN["features"]) >= 5

    def test_each_domain_has_8_to_15_features(self) -> None:
        for pattern in DOMAIN_PATTERNS:
            count = len(pattern["features"])
            assert 8 <= count <= 15, (
                f"Domain '{pattern['name']}' has {count} features, expected 8-15"
            )

    def test_generic_has_5_plus_features(self) -> None:
        assert len(GENERIC_PATTERN["features"]) >= 5

    def test_keyword_weights_are_1_to_3(self) -> None:
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for keyword, weight in pattern["keywords"]:
                assert isinstance(keyword, str), (
                    f"Keyword must be str in '{pattern['name']}'"
                )
                assert 1 <= weight <= 3, (
                    f"Weight {weight} for '{keyword}' in '{pattern['name']}' "
                    "must be 1-3"
                )

    def test_feature_template_has_required_fields(self) -> None:
        required_keys = {
            "name",
            "description",
            "category",
            "priority",
            "always_separate",
            "data_keywords",
        }
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                missing = required_keys - feat.keys()
                assert not missing, (
                    f"Feature '{feat.get('name', '?')}' in '{pattern['name']}' "
                    f"missing keys: {missing}"
                )

    def test_categories_are_valid(self) -> None:
        valid = set(FEATURE_CATEGORIES)
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                assert feat["category"] in valid, (
                    f"Invalid category '{feat['category']}' for "
                    f"'{feat['name']}' in '{pattern['name']}'"
                )

    def test_priorities_are_valid(self) -> None:
        valid = set(FEATURE_PRIORITIES)
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                assert feat["priority"] in valid, (
                    f"Invalid priority '{feat['priority']}' for "
                    f"'{feat['name']}' in '{pattern['name']}'"
                )

    def test_always_separate_is_bool(self) -> None:
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                assert isinstance(feat["always_separate"], bool), (
                    f"always_separate must be bool for '{feat['name']}' "
                    f"in '{pattern['name']}'"
                )

    def test_data_keywords_is_list_of_strings(self) -> None:
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                assert isinstance(feat["data_keywords"], list), (
                    f"data_keywords must be list for '{feat['name']}'"
                )
                for kw in feat["data_keywords"]:
                    assert isinstance(kw, str)

    def test_always_separate_on_auth_notification_integration(self) -> None:
        """Auth, notification, and integration features must be always_separate."""
        separate_names = {"authentication", "notifications", "notification"}
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                if feat["name"] in separate_names:
                    assert feat["always_separate"] is True, (
                        f"'{feat['name']}' in '{pattern['name']}' "
                        "must have always_separate=True"
                    )

    def test_domain_names_are_lowercase(self) -> None:
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            assert pattern["name"] == pattern["name"].lower()

    def test_feature_names_are_kebab_case(self) -> None:
        import re

        kebab_re = re.compile(r"^[a-z][a-z0-9-]*$")
        for pattern in [*DOMAIN_PATTERNS, GENERIC_PATTERN]:
            for feat in pattern["features"]:
                assert kebab_re.match(feat["name"]), (
                    f"Feature name '{feat['name']}' in '{pattern['name']}' "
                    "must be kebab-case"
                )
