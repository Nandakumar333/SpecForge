"""Unit tests for template engine data models."""

from __future__ import annotations

import pytest

from specforge.core.config import (
    FEATURE_TEMPLATE_NAMES,
    GENERATION_HEADER,
    PROMPT_AGENT_NAMES,
    get_constitution_vars,
    get_feature_vars,
    get_prompt_vars,
)
from specforge.core.template_models import (
    StackProfile,
    TemplateInfo,
    TemplateSource,
    TemplateType,
    TemplateVarSchema,
    ValidationIssue,
    ValidationReport,
)


class TestTemplateType:
    def test_has_all_members(self) -> None:
        assert set(TemplateType) == {
            TemplateType.constitution,
            TemplateType.prompt,
            TemplateType.feature,
            TemplateType.partial,
        }

    def test_values_match_names(self) -> None:
        for member in TemplateType:
            assert member.value == member.name


class TestTemplateSource:
    def test_has_all_members(self) -> None:
        assert set(TemplateSource) == {
            TemplateSource.built_in,
            TemplateSource.user_override,
        }


class TestTemplateInfo:
    def test_frozen(self) -> None:
        info = TemplateInfo(
            logical_name="backend",
            template_type=TemplateType.prompt,
            source=TemplateSource.built_in,
            template_path="prompts/backend.md.j2",
        )
        with pytest.raises(AttributeError):
            info.logical_name = "changed"  # type: ignore[misc]

    def test_identity_tuple_uniqueness(self) -> None:
        a = TemplateInfo(
            logical_name="backend",
            template_type=TemplateType.prompt,
            source=TemplateSource.built_in,
            template_path="prompts/backend.md.j2",
        )
        b = TemplateInfo(
            logical_name="backend",
            template_type=TemplateType.prompt,
            source=TemplateSource.built_in,
            template_path="prompts/backend.md.j2",
            stack="dotnet",
        )
        assert a.identity != b.identity

    def test_identity_same_template(self) -> None:
        a = TemplateInfo(
            logical_name="spec",
            template_type=TemplateType.feature,
            source=TemplateSource.built_in,
            template_path="features/spec.md.j2",
        )
        b = TemplateInfo(
            logical_name="spec",
            template_type=TemplateType.feature,
            source=TemplateSource.built_in,
            template_path="features/spec.md.j2",
        )
        assert a.identity == b.identity

    def test_is_base_default_false(self) -> None:
        info = TemplateInfo(
            logical_name="backend",
            template_type=TemplateType.prompt,
            source=TemplateSource.built_in,
            template_path="prompts/backend.md.j2",
        )
        assert info.is_base is False

    def test_stack_default_none(self) -> None:
        info = TemplateInfo(
            logical_name="spec",
            template_type=TemplateType.feature,
            source=TemplateSource.built_in,
            template_path="features/spec.md.j2",
        )
        assert info.stack is None


class TestTemplateVarSchema:
    def test_frozen(self) -> None:
        schema = TemplateVarSchema(required={"name": str})
        with pytest.raises(AttributeError):
            schema.required = {}  # type: ignore[misc]

    def test_validate_missing_required(self) -> None:
        schema = TemplateVarSchema(required={"project_name": str, "date": str})
        errors = schema.validate({"date": "2026-01-01"})
        assert len(errors) == 1
        assert "project_name" in errors[0]

    def test_validate_type_mismatch(self) -> None:
        schema = TemplateVarSchema(required={"project_name": str})
        errors = schema.validate({"project_name": 42})
        assert len(errors) == 1
        assert "expected str" in errors[0]
        assert "got int" in errors[0]

    def test_validate_valid_context(self) -> None:
        schema = TemplateVarSchema(
            required={"project_name": str},
            optional={"stack": (str, "agnostic")},
        )
        errors = schema.validate({"project_name": "test", "stack": "python"})
        assert errors == []

    def test_validate_optional_type_mismatch(self) -> None:
        schema = TemplateVarSchema(
            optional={"count": (int, 0)},
        )
        errors = schema.validate({"count": "not-an-int"})
        assert len(errors) == 1
        assert "count" in errors[0]

    def test_validate_optional_missing_is_ok(self) -> None:
        schema = TemplateVarSchema(
            optional={"stack": (str, "agnostic")},
        )
        errors = schema.validate({})
        assert errors == []


class TestValidationIssue:
    def test_frozen(self) -> None:
        issue = ValidationIssue(
            line=1,
            issue_type="unresolved_placeholder",
            message="Found {{ name }}",
        )
        with pytest.raises(AttributeError):
            issue.line = 2  # type: ignore[misc]

    def test_placeholder_name_default_none(self) -> None:
        issue = ValidationIssue(
            line=5,
            issue_type="unclosed_code_block",
            message="Unclosed code block",
        )
        assert issue.placeholder_name is None


class TestValidationReport:
    def test_is_valid_when_no_issues(self) -> None:
        report = ValidationReport(template_name="test")
        assert report.is_valid is True

    def test_is_invalid_when_issues_present(self) -> None:
        issue = ValidationIssue(
            line=1,
            issue_type="unresolved_placeholder",
            message="Found {{ name }}",
            placeholder_name="name",
        )
        report = ValidationReport(template_name="test", issues=[issue])
        assert report.is_valid is False

    def test_frozen(self) -> None:
        report = ValidationReport(template_name="test")
        with pytest.raises(AttributeError):
            report.template_name = "changed"  # type: ignore[misc]


class TestStackProfile:
    def test_frozen(self) -> None:
        profile = StackProfile(
            stack_name="python",
            stack_hint="Python",
            conventions="PEP 8",
            patterns="Clean Architecture",
            testing_hint="pytest",
        )
        with pytest.raises(AttributeError):
            profile.stack_name = "changed"  # type: ignore[misc]

    def test_all_fields_populated(self) -> None:
        profile = StackProfile(
            stack_name="dotnet",
            stack_hint="C#/.NET",
            conventions="Microsoft C# conventions",
            patterns="Clean Architecture with MediatR",
            testing_hint="xUnit + Moq",
        )
        assert profile.stack_name == "dotnet"
        assert profile.stack_hint == "C#/.NET"
        assert profile.conventions == "Microsoft C# conventions"
        assert profile.patterns == "Clean Architecture with MediatR"
        assert profile.testing_hint == "xUnit + Moq"


class TestConfigConstants:
    def test_prompt_agent_names_count(self) -> None:
        assert len(PROMPT_AGENT_NAMES) == 7

    def test_feature_template_names_count(self) -> None:
        assert len(FEATURE_TEMPLATE_NAMES) == 7

    def test_generation_header_present(self) -> None:
        assert "SpecForge" in GENERATION_HEADER
        assert "<!--" in GENERATION_HEADER

    def test_constitution_vars_schema(self) -> None:
        schema = get_constitution_vars()
        assert "project_name" in schema.required
        assert "agent" in schema.required
        assert "stack" in schema.required
        assert "date" in schema.required
        assert "stack_hint" in schema.required

    def test_prompt_vars_schema(self) -> None:
        schema = get_prompt_vars()
        assert "project_name" in schema.required
        assert "conventions" in schema.optional
        assert "patterns" in schema.optional

    def test_feature_vars_schema(self) -> None:
        schema = get_feature_vars()
        assert "project_name" in schema.required
        assert "date" in schema.required
        assert "feature_name" in schema.optional
        assert "stack" in schema.optional
