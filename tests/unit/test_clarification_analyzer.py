"""Unit tests for AmbiguityScanner — pattern-based ambiguity detection."""

from __future__ import annotations

from specforge.core.clarification_analyzer import AmbiguityScanner, default_patterns
from specforge.core.clarification_models import AmbiguityMatch


def _make_scanner() -> AmbiguityScanner:
    """Return a scanner initialised with the default pattern set."""
    return AmbiguityScanner(default_patterns())


def _make_ledger_spec() -> str:
    """Spec text for a ledger-service with intentional ambiguities."""
    return (
        "## Ledger Service\n"
        "\n"
        "The ledger service manages financial data.\n"
        "\n"
        "Transactions should be processed appropriately based on\n"
        "the account type and relevant context.\n"
        "\n"
        "Each transaction will include proper validation.\n"
        "\n"
        "Edge cases should be handled as needed.\n"
    )


def _make_multi_feature_spec() -> str:
    """Spec covering accounts AND transactions with ambiguities in both."""
    return (
        "## Account Management\n"
        "\n"
        "Accounts should provide suitable access controls.\n"
        "Users can configure their account settings as needed.\n"
        "\n"
        "## Transaction Tracking\n"
        "\n"
        "Transactions should be processed appropriately.\n"
        "Either REST or gRPC will be used for communication.\n"
        "The data format is TBD.\n"
    )


def _make_clean_spec() -> str:
    """Spec text with no ambiguities."""
    return (
        "## Overview\n"
        "\n"
        "The service exposes a REST API on port 8080.\n"
        "Authentication uses JWT tokens with RS256 signing.\n"
        "Data is stored in PostgreSQL 15 with pgcrypto.\n"
    )


class TestDefaultPatterns:
    """Tests for the default_patterns() factory."""

    def test_returns_four_patterns(self) -> None:
        patterns = default_patterns()
        assert len(patterns) == 4

    def test_pattern_types(self) -> None:
        types = {p.pattern_type for p in default_patterns()}
        assert types == {
            "vague_term",
            "undefined_concept",
            "missing_boundary",
            "unspecified_choice",
        }

    def test_categories_covered(self) -> None:
        cats = {p.category for p in default_patterns()}
        assert "domain" in cats
        assert "technical" in cats


class TestScanVagueTerms:
    """AmbiguityScanner.scan() detection of vague/imprecise terms."""

    def test_detects_appropriate(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Data should be handled appropriately.")
        texts = [m.text.lower() for m in matches]
        assert any("appropriate" in t for t in texts)

    def test_detects_appropriately_adverb(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Process transactions appropriately.")
        texts = [m.text.lower() for m in matches]
        assert any("appropriate" in t for t in texts)

    def test_detects_as_needed(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Add caching as needed for performance.")
        texts = [m.text.lower() for m in matches]
        assert any("as needed" in t for t in texts)

    def test_detects_various(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Support various output formats.")
        texts = [m.text.lower() for m in matches]
        assert any("various" in t for t in texts)

    def test_vague_category_is_domain(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Handle errors appropriately.")
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) >= 1
        assert all(m.category == "domain" for m in vague)

    def test_correct_line_number(self) -> None:
        scanner = _make_scanner()
        text = "Line one is fine.\nLine two is appropriate.\nLine three ok."
        matches = scanner.scan(text)
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert any(m.line_number == 2 for m in vague)


class TestScanUnspecifiedChoices:
    """AmbiguityScanner.scan() detection of TBD / to-be-determined markers."""

    def test_detects_either_or(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Either REST or gRPC will be used.")
        assert len(matches) >= 1
        assert any(m.category == "technical" for m in matches)

    def test_detects_tbd(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("The deployment strategy is TBD.")
        technical = [m for m in matches if m.pattern_type == "unspecified_choice"]
        assert len(technical) >= 1

    def test_detects_to_be_determined(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("Caching policy is to be determined later.")
        assert any(m.pattern_type == "unspecified_choice" for m in matches)


class TestScanEmptyInput:
    """Edge cases: empty or clean spec text."""

    def test_empty_string_returns_empty(self) -> None:
        scanner = _make_scanner()
        assert scanner.scan("") == ()

    def test_whitespace_only_returns_empty(self) -> None:
        scanner = _make_scanner()
        assert scanner.scan("   \n  \n  ") == ()

    def test_clean_spec_returns_no_vague(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_clean_spec())
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) == 0


class TestScanSkipsStructural:
    """Scanner must ignore headings, code blocks, tables, and comments."""

    def test_skips_headings(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan("# Appropriately named heading\n")
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) == 0

    def test_skips_code_blocks(self) -> None:
        scanner = _make_scanner()
        text = "```\nhandle_appropriately()\n```\n"
        matches = scanner.scan(text)
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) == 0

    def test_skips_tables(self) -> None:
        scanner = _make_scanner()
        text = "| appropriately | value |\n| --- | --- |\n"
        matches = scanner.scan(text)
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) == 0

    def test_skips_html_comments(self) -> None:
        scanner = _make_scanner()
        text = "<!-- appropriately handle this -->\n"
        matches = scanner.scan(text)
        vague = [m for m in matches if m.pattern_type == "vague_term"]
        assert len(vague) == 0


class TestScanForCategory:
    """AmbiguityScanner.scan_for_category() filters correctly."""

    def test_filters_to_domain_only(self) -> None:
        scanner = _make_scanner()
        text = "Handle appropriately.\nThe strategy is TBD."
        domain = scanner.scan_for_category(text, "domain")
        assert all(m.category == "domain" for m in domain)

    def test_filters_to_technical_only(self) -> None:
        scanner = _make_scanner()
        text = "Handle appropriately.\nThe strategy is TBD."
        technical = scanner.scan_for_category(text, "technical")
        assert all(m.category == "technical" for m in technical)

    def test_empty_for_absent_category(self) -> None:
        scanner = _make_scanner()
        text = "Handle appropriately."
        comm = scanner.scan_for_category(text, "communication")
        assert comm == ()


class TestScanSorting:
    """Matches must be sorted by line_number."""

    def test_sorted_by_line_number(self) -> None:
        scanner = _make_scanner()
        text = (
            "Line one is appropriate.\n"
            "Line two is fine.\n"
            "Line three is TBD.\n"
            "Line four is proper.\n"
        )
        matches = scanner.scan(text)
        line_nums = [m.line_number for m in matches]
        assert line_nums == sorted(line_nums)


class TestScanConfidence:
    """Confidence values must fall within [0.0, 1.0]."""

    def test_confidence_bounds(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_multi_feature_spec())
        assert len(matches) >= 1
        for m in matches:
            assert 0.0 <= m.confidence <= 1.0


class TestLedgerServiceSpec:
    """Integration-style: ledger-service spec with realistic ambiguities."""

    def test_returns_at_least_one_domain_match(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_ledger_spec())
        domain = [m for m in matches if m.category == "domain"]
        assert len(domain) >= 1

    def test_appropriately_detected_in_ledger(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_ledger_spec())
        texts = [m.text.lower() for m in matches]
        assert any("appropriate" in t for t in texts)


class TestMultiFeatureSpec:
    """Spec covering multiple feature areas returns matches from both."""

    def test_matches_from_both_areas(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_multi_feature_spec())
        lines = {m.line_number for m in matches}
        # Matches should span at least two disjoint line regions
        assert max(lines) - min(lines) >= 3

    def test_returns_match_instances(self) -> None:
        scanner = _make_scanner()
        matches = scanner.scan(_make_multi_feature_spec())
        for m in matches:
            assert isinstance(m, AmbiguityMatch)
