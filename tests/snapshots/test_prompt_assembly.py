"""Deterministic assertion-based tests for assembled prompt structure."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    MonolithAdapter,
)
from specforge.core.phase_prompts import (
    DECOMPOSE_PROMPT,
    PLAN_PROMPT,
    SPEC_PROMPT,
    TASKS_PROMPT,
)
from specforge.core.prompt_assembler import PromptAssembler
from specforge.core.service_context import FeatureInfo, ServiceContext


def _make_ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="billing-service",
        service_name="Billing Service",
        architecture=arch,
        project_description="A billing microservice for payments",
        domain="finance",
        features=(
            FeatureInfo("001", "invoices", "Invoices", "Invoice mgmt", "P0", "core"),
            FeatureInfo("002", "payments", "Payments", "Payment processing", "P1", "core"),
        ),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


def _make_constitution(tmp_path: Path) -> Path:
    p = tmp_path / "constitution.md"
    p.write_text(
        "# Project Constitution\n\n"
        "## Principle I: Spec-First\nAlways write spec before code.\n\n"
        "## Principle II: Test-Driven\nTDD for all features.\n",
        encoding="utf-8",
    )
    return p


# ── Spec phase + microservice ───────────────────────────────────────


class TestSpecPhaseMicroservice:
    """Assemble spec prompt with microservice architecture context."""

    def test_system_prompt_contains_skeleton(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        assert result.ok is True
        system_prompt, _ = result.value
        assert "Target Format" in system_prompt
        assert "Feature Specification" in system_prompt

    def test_system_prompt_contains_clean_markdown_instruction(
        self, tmp_path: Path
    ) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Output ONLY the Markdown" in system_prompt

    def test_system_prompt_contains_microservice_architecture(
        self, tmp_path: Path
    ) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "## Architecture: Microservice" in system_prompt

    def test_user_prompt_contains_service_info(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "Billing Service" in user_prompt
        assert "billing-service" in user_prompt
        assert "billing microservice" in user_prompt

    def test_user_prompt_lists_features(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "Invoices" in user_prompt
        assert "Payments" in user_prompt


# ── Plan phase + monolith ───────────────────────────────────────────


class TestPlanPhaseMonolith:
    """Assemble plan prompt with monolith architecture context."""

    def test_system_prompt_contains_monolith_architecture(
        self, tmp_path: Path
    ) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MonolithAdapter()
        ctx = _make_ctx(tmp_path, "monolithic")

        result = asm.assemble(PLAN_PROMPT, ctx, adapter, {})

        assert result.ok is True
        system_prompt, _ = result.value
        assert "## Architecture: Monolithic" in system_prompt

    def test_system_prompt_contains_plan_skeleton(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MonolithAdapter()
        ctx = _make_ctx(tmp_path, "monolithic")

        result = asm.assemble(PLAN_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Implementation Plan" in system_prompt
        assert "Technical Context" in system_prompt

    def test_system_prompt_includes_constitution(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MonolithAdapter()
        ctx = _make_ctx(tmp_path, "monolithic")

        result = asm.assemble(PLAN_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Spec-First" in system_prompt
        assert "Test-Driven" in system_prompt


# ── Tasks phase + prior artifacts ───────────────────────────────────


class TestTasksPhasePriorArtifacts:
    """Assemble tasks prompt with prior artifacts included."""

    def test_user_prompt_includes_prior_artifacts(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")
        artifacts = {
            "spec.md": "# Spec\nFR-001: Create invoices",
            "plan.md": "# Plan\nPhase 1: Setup database",
        }

        result = asm.assemble(TASKS_PROMPT, ctx, adapter, artifacts)

        assert result.ok is True
        _, user_prompt = result.value
        assert "Prior Artifacts" in user_prompt
        assert "FR-001: Create invoices" in user_prompt
        assert "Phase 1: Setup database" in user_prompt

    def test_system_prompt_contains_tasks_skeleton(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")
        artifacts = {"spec.md": "# Spec\nContent"}

        result = asm.assemble(TASKS_PROMPT, ctx, adapter, artifacts)

        system_prompt, _ = result.value
        assert "Tasks" in system_prompt
        assert "TDD" in system_prompt

    def test_artifacts_separated_by_section_markers(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")
        artifacts = {
            "spec.md": "# Spec\nContent A",
            "plan.md": "# Plan\nContent B",
        }

        result = asm.assemble(TASKS_PROMPT, ctx, adapter, artifacts)

        _, user_prompt = result.value
        assert "### spec.md" in user_prompt
        assert "### plan.md" in user_prompt


# ── Decompose phase + features ──────────────────────────────────────


class TestDecomposePhaseFeatures:
    """Assemble decompose prompt — verify features list included."""

    def test_user_prompt_includes_features_section(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(DECOMPOSE_PROMPT, ctx, adapter, {})

        assert result.ok is True
        _, user_prompt = result.value
        assert "## Features" in user_prompt
        assert "Invoices" in user_prompt
        assert "Payments" in user_prompt

    def test_system_prompt_contains_decompose_skeleton(
        self, tmp_path: Path
    ) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = _make_ctx(tmp_path, "microservice")

        result = asm.assemble(DECOMPOSE_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "features" in system_prompt
        assert "services" in system_prompt

    def test_no_features_section_when_empty(self, tmp_path: Path) -> None:
        asm = PromptAssembler(constitution_path=_make_constitution(tmp_path))
        adapter = MicroserviceAdapter()
        ctx = ServiceContext(
            service_slug="empty-svc",
            service_name="Empty Service",
            architecture="microservice",
            project_description="No features yet",
            domain="test",
            features=(),
            dependencies=(),
            events=(),
            output_dir=tmp_path,
        )

        result = asm.assemble(DECOMPOSE_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "## Features" not in user_prompt
