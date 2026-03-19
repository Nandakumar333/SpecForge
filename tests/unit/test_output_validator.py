"""Unit tests for OutputValidator — per-phase section checking."""

from __future__ import annotations

from specforge.core.output_validator import OutputValidator


# ── validate() ───────────────────────────────────────────────────────


class TestOutputValidatorValidate:
    def test_returns_ok_when_all_sections_present(self) -> None:
        validator = OutputValidator()
        content = (
            "# Feature Specification: Auth\n\n"
            "## User Scenarios & Testing\n\nScenarios here\n\n"
            "## Requirements\n\nFR-001: Must authenticate\n\n"
            "## Success Criteria\n\nSC-001: Login works\n"
        )
        result = validator.validate("spec", content)

        assert result.ok is True
        assert result.value == content

    def test_returns_err_with_missing_sections(self) -> None:
        validator = OutputValidator()
        content = "# Feature Specification: Auth\n\n## User Scenarios & Testing\n"
        result = validator.validate("spec", content)

        assert result.ok is False
        missing = result.error
        assert isinstance(missing, list)
        assert "Requirements" in missing
        assert "Success Criteria" in missing

    def test_returns_ok_for_unknown_phase(self) -> None:
        validator = OutputValidator()
        result = validator.validate("unknown-phase", "any content")

        assert result.ok is True

    def test_returns_ok_for_research_with_r1(self) -> None:
        validator = OutputValidator()
        content = "# Research\n\n## R1: Database Choice\n\nDecision: PostgreSQL\n"
        result = validator.validate("research", content)

        assert result.ok is True

    def test_returns_err_for_research_without_r1(self) -> None:
        validator = OutputValidator()
        content = "# Research\n\nSome text without proper sections.\n"
        result = validator.validate("research", content)

        assert result.ok is False

    def test_returns_ok_for_tasks_with_phase_1(self) -> None:
        validator = OutputValidator()
        content = "# Tasks\n\n## Phase 1: Setup\n\n- [ ] T001 Create files\n"
        result = validator.validate("tasks", content)

        assert result.ok is True

    def test_returns_ok_for_datamodel_with_both_sections(self) -> None:
        validator = OutputValidator()
        content = (
            "# Data Model\n\n"
            "## Entity Diagram\n\n```text\nDiagram\n```\n\n"
            "## Entities\n\n### User\n"
        )
        result = validator.validate("datamodel", content)

        assert result.ok is True

    def test_returns_ok_for_checklist_with_chk_prefix(self) -> None:
        validator = OutputValidator()
        content = "# Checklist\n\n- [ ] CHK-001 Validate auth\n"
        result = validator.validate("checklist", content)

        assert result.ok is True

    def test_returns_ok_for_decompose_with_features_heading(self) -> None:
        validator = OutputValidator()
        # Decompose validation expects a markdown heading containing "features"
        content = "# Decomposition\n\n## features\n\n```json\n{}\n```\n"
        result = validator.validate("decompose", content)

        assert result.ok is True

    def test_returns_err_for_decompose_json_without_heading(self) -> None:
        validator = OutputValidator()
        # Pure JSON has no markdown heading, so "features" section is missing
        content = '{"features": [{"id": "001"}], "services": []}'
        result = validator.validate("decompose", content)

        assert result.ok is False

    def test_returns_ok_for_edgecase_with_heading(self) -> None:
        validator = OutputValidator()
        content = "# Edge Cases: Auth\n\n## Edge Cases\n\n### EC-001\n"
        result = validator.validate("edgecase", content)

        assert result.ok is True


# ── Case-insensitive heading matching ────────────────────────────────


class TestOutputValidatorCaseInsensitive:
    def test_lowercase_heading_matches(self) -> None:
        validator = OutputValidator()
        content = (
            "# Spec\n\n"
            "## user scenarios & testing\n\nScenarios\n\n"
            "## requirements\n\nFR-001\n\n"
            "## success criteria\n\nSC-001\n"
        )
        result = validator.validate("spec", content)

        assert result.ok is True

    def test_mixed_case_heading_matches(self) -> None:
        validator = OutputValidator()
        content = (
            "# Spec\n\n"
            "## User scenarios & Testing\n\nScenarios\n\n"
            "## REQUIREMENTS\n\nFR-001\n\n"
            "## Success criteria\n\nSC-001\n"
        )
        result = validator.validate("spec", content)

        assert result.ok is True


# ── build_correction_prompt() ────────────────────────────────────────


class TestBuildCorrectionPrompt:
    def test_includes_missing_section_names(self) -> None:
        prompt = OutputValidator.build_correction_prompt(
            phase="spec",
            missing=["Requirements", "Success Criteria"],
            original_output="# Spec\n\n## User Scenarios",
        )

        assert "Requirements" in prompt
        assert "Success Criteria" in prompt

    def test_includes_phase_name(self) -> None:
        prompt = OutputValidator.build_correction_prompt(
            phase="spec",
            missing=["Requirements"],
            original_output="# Spec\npartial",
        )

        assert "spec" in prompt

    def test_includes_original_output(self) -> None:
        original = "# Original Output\nSome content here"
        prompt = OutputValidator.build_correction_prompt(
            phase="tasks",
            missing=["Phase 1"],
            original_output=original,
        )

        assert original in prompt

    def test_missing_sections_quoted(self) -> None:
        prompt = OutputValidator.build_correction_prompt(
            phase="plan",
            missing=["Summary", "Technical Context"],
            original_output="# Plan\n",
        )

        assert '"Summary"' in prompt
        assert '"Technical Context"' in prompt
