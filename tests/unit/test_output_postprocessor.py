"""Unit tests for OutputPostprocessor — preamble stripping, normalization, truncation."""

from __future__ import annotations

from specforge.core.output_postprocessor import OutputPostprocessor


# ── strip_preamble() ─────────────────────────────────────────────────


class TestStripPreamble:
    def test_removes_text_before_first_heading(self) -> None:
        content = "Here is the document.\n\n# Feature Spec\n\nContent"
        result = OutputPostprocessor.strip_preamble(content)

        assert result.startswith("# Feature Spec")
        assert "Here is the document" not in result

    def test_no_op_when_starts_with_heading(self) -> None:
        content = "# Feature Spec\n\nContent here"
        result = OutputPostprocessor.strip_preamble(content)

        assert result == content

    def test_no_op_when_no_heading_present(self) -> None:
        content = "Just plain text without any headings"
        result = OutputPostprocessor.strip_preamble(content)

        assert result == content

    def test_removes_multi_line_preamble(self) -> None:
        content = (
            "Sure, here is your spec.\n"
            "Based on the requirements:\n\n"
            "## Specification\n\nContent"
        )
        result = OutputPostprocessor.strip_preamble(content)

        assert result.startswith("## Specification")

    def test_handles_h2_as_first_heading(self) -> None:
        content = "Preamble text\n\n## Section Title\n\nBody"
        result = OutputPostprocessor.strip_preamble(content)

        assert result.startswith("## Section Title")


# ── normalize_headings() ─────────────────────────────────────────────


class TestNormalizeHeadings:
    def test_shifts_h2_to_h1(self) -> None:
        content = "## Top Heading\n\n### Sub Heading\n\nText"
        result = OutputPostprocessor.normalize_headings(content, expected_top_level=1)

        assert result.startswith("# Top Heading")
        assert "## Sub Heading" in result

    def test_no_shift_when_already_correct(self) -> None:
        content = "# Top Heading\n\n## Sub Heading\n\nText"
        result = OutputPostprocessor.normalize_headings(content, expected_top_level=1)

        assert result == content

    def test_shifts_h3_to_h1(self) -> None:
        content = "### Deep Heading\n\n#### Deeper\n\nText"
        result = OutputPostprocessor.normalize_headings(content, expected_top_level=1)

        assert result.startswith("# Deep Heading")
        assert "## Deeper" in result

    def test_preserves_non_heading_lines(self) -> None:
        content = "## Heading\n\nSome paragraph text\n\n- List item"
        result = OutputPostprocessor.normalize_headings(content, expected_top_level=1)

        assert "Some paragraph text" in result
        assert "- List item" in result

    def test_no_heading_content_unchanged(self) -> None:
        content = "Just text\nNo headings here"
        result = OutputPostprocessor.normalize_headings(content, expected_top_level=1)

        assert result == content


# ── detect_truncation() ──────────────────────────────────────────────


class TestDetectTruncation:
    def test_returns_true_when_required_sections_missing(self) -> None:
        content = "# Spec\n\n## User Scenarios & Testing\n\nScenarios"
        result = OutputPostprocessor.detect_truncation(
            "spec",
            content,
            required_sections=("User Scenarios & Testing", "Requirements", "Success Criteria"),
        )

        assert result is True

    def test_returns_false_when_all_sections_present(self) -> None:
        content = (
            "# Spec\n\n"
            "## User Scenarios & Testing\n\nScenarios\n\n"
            "## Requirements\n\nFR-001\n\n"
            "## Success Criteria\n\nSC-001.\n"
        )
        result = OutputPostprocessor.detect_truncation(
            "spec",
            content,
            required_sections=("User Scenarios & Testing", "Requirements", "Success Criteria"),
        )

        assert result is False

    def test_returns_true_with_abrupt_ending(self) -> None:
        # Missing section + abrupt ending (no punctuation)
        content = "# Spec\n\n## User Scenarios & Testing\n\nSome text that just cuts"
        result = OutputPostprocessor.detect_truncation(
            "spec",
            content,
            required_sections=("User Scenarios & Testing", "Requirements"),
        )

        assert result is True

    def test_returns_true_with_unclosed_code_block(self) -> None:
        content = (
            "# Spec\n\n"
            "## User Scenarios & Testing\n\n"
            "```python\ndef foo():\n    pass\n"
        )
        result = OutputPostprocessor.detect_truncation(
            "spec",
            content,
            required_sections=("User Scenarios & Testing", "Requirements"),
        )

        assert result is True

    def test_uses_default_required_sections(self) -> None:
        content = (
            "# Spec\n\n"
            "## User Scenarios & Testing\n\nScenarios\n\n"
            "## Requirements\n\nFR-001\n\n"
            "## Success Criteria\n\nSC-001.\n"
        )
        result = OutputPostprocessor.detect_truncation("spec", content)

        assert result is False


# ── cap_output() ─────────────────────────────────────────────────────


class TestCapOutput:
    def test_enforces_max_length(self) -> None:
        content = "A" * 1000
        result = OutputPostprocessor.cap_output(content, max_chars=500)

        assert len(result) == 500

    def test_no_op_within_limit(self) -> None:
        content = "Short content"
        result = OutputPostprocessor.cap_output(content, max_chars=500)

        assert result == content

    def test_exact_limit(self) -> None:
        content = "A" * 500
        result = OutputPostprocessor.cap_output(content, max_chars=500)

        assert result == content
        assert len(result) == 500


# ── build_continuation_prompt() ──────────────────────────────────────


class TestBuildContinuationPrompt:
    def test_returns_tuple_of_strings(self) -> None:
        system, user = OutputPostprocessor.build_continuation_prompt("partial doc")

        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_continuation_instruction(self) -> None:
        system, _ = OutputPostprocessor.build_continuation_prompt("partial")

        assert "Continue" in system
        assert "repeat" in system.lower()

    def test_user_contains_partial_output(self) -> None:
        partial = "# Spec\n\n## User Scenarios\n\nSome content"
        _, user = OutputPostprocessor.build_continuation_prompt(partial)

        assert partial in user

    def test_user_contains_continue_instruction(self) -> None:
        _, user = OutputPostprocessor.build_continuation_prompt("partial doc")

        assert "Continue from here" in user
