"""Unit tests for EnrichedPromptBuilder (Feature 017)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specforge.core.enriched_prompts import EnrichedPromptBuilder
from specforge.core.phase_prompts import (
    CHECKLIST_PROMPT,
    DATAMODEL_PROMPT,
    DECOMPOSE_PROMPT,
    EDGECASE_PROMPT,
    PLAN_PROMPT,
    RESEARCH_PROMPT,
    SPEC_PROMPT,
    TASKS_PROMPT,
)
from specforge.core.service_context import FeatureInfo, ServiceContext


def _make_service_context(arch: str = "monolithic") -> ServiceContext:
    return ServiceContext(
        service_slug="auth-service",
        service_name="Auth Service",
        architecture=arch,
        project_description="A user authentication service",
        domain="security",
        features=(
            FeatureInfo(
                id="001", name="login", display_name="Login",
                description="User login flow", priority="P1", category="core",
            ),
        ),
        dependencies=(),
        events=(),
        output_dir=Path("/tmp/auth-service"),
    )


def _find_template_dir() -> Path:
    """Locate enrichment templates directory."""
    import specforge
    pkg = Path(specforge.__file__).parent
    d = pkg / "templates" / "base" / "enrichment"
    if d.exists():
        return d
    return Path(__file__).parent.parent.parent / "src" / "specforge" / "templates" / "base" / "enrichment"


class TestEnrichedPromptBuilder:
    def setup_method(self) -> None:
        self.template_dir = _find_template_dir()
        self.builder = EnrichedPromptBuilder(
            template_dir=self.template_dir,
            governance_loader=None,
        )
        self.ctx = _make_service_context()

    @pytest.mark.parametrize("phase_prompt", [
        SPEC_PROMPT, RESEARCH_PROMPT, DATAMODEL_PROMPT, EDGECASE_PROMPT,
        PLAN_PROMPT, CHECKLIST_PROMPT, TASKS_PROMPT, DECOMPOSE_PROMPT,
    ])
    def test_build_enrichment_renders(self, phase_prompt) -> None:
        result = self.builder.build_enrichment(
            phase_prompt, self.ctx, "monolithic",
        )
        assert result.ok
        rendered = result.value
        assert len(rendered) > 0
        lines = rendered.strip().split("\n")
        assert len(lines) >= 20, f"{phase_prompt.phase_name}: only {len(lines)} lines"

    def test_enrichment_includes_anti_patterns(self) -> None:
        result = self.builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert "Anti-Patterns" in result.value

    def test_enrichment_includes_output_requirements(self) -> None:
        result = self.builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert "Output Requirements" in result.value

    def test_architecture_specific_microservice(self) -> None:
        ctx = _make_service_context("microservice")
        result = self.builder.build_enrichment(SPEC_PROMPT, ctx, "microservice")
        assert "microservice" in result.value.lower()

    def test_architecture_specific_monolith(self) -> None:
        result = self.builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert "monolith" in result.value.lower()

    def test_governance_rules_included(self) -> None:
        mock_loader = MagicMock()
        mock_rule = MagicMock()
        mock_rule.domain = "security"
        mock_rule.text = "All inputs must be validated"
        mock_file = MagicMock()
        mock_file.rules = [mock_rule]
        mock_set = MagicMock()
        mock_set.files = [mock_file]
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.value = mock_set
        mock_loader.load.return_value = mock_result

        builder = EnrichedPromptBuilder(
            template_dir=self.template_dir,
            governance_loader=mock_loader,
        )
        result = builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert "All inputs must be validated" in result.value

    def test_no_governance_graceful(self) -> None:
        result = self.builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert result.ok

    def test_missing_template_graceful(self) -> None:
        from specforge.core.phase_prompts import PhasePrompt
        fake = PhasePrompt(
            phase_name="fake",
            system_instructions="",
            skeleton="",
            required_sections=(),
            enrichment_template="nonexistent.md.j2",
        )
        result = self.builder.build_enrichment(fake, self.ctx, "monolithic")
        assert result.ok
        assert result.value == ""

    def test_quality_thresholds_in_output(self) -> None:
        result = self.builder.build_enrichment(SPEC_PROMPT, self.ctx, "monolithic")
        assert "30" in result.value  # max_function_lines
