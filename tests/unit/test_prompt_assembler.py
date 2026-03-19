"""Unit tests for PromptAssembler — prompt construction and budget trimming."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.phase_prompts import SPEC_PROMPT
from specforge.core.prompt_assembler import CHARS_PER_TOKEN_ESTIMATE, PromptAssembler
from specforge.core.service_context import FeatureInfo, ServiceContext


def _make_service_ctx(tmp_path: Path) -> ServiceContext:
    return ServiceContext(
        service_slug="auth-service",
        service_name="Auth Service",
        architecture="microservice",
        project_description="An authentication microservice",
        domain="identity",
        features=(
            FeatureInfo("001", "login", "Login", "User login", "P0", "core"),
        ),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


def _make_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.serialize_for_prompt.return_value = "Architecture: microservice"
    return adapter


# ── Basic assembly ───────────────────────────────────────────────────


class TestPromptAssemblerBasic:
    def test_assemble_returns_ok_tuple(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("# Constitution\nPrinciples here", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        assert result.ok is True
        system_prompt, user_prompt = result.value
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)

    def test_system_prompt_contains_clean_markdown_instruction(
        self, tmp_path: Path
    ) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Output ONLY the Markdown" in system_prompt

    def test_system_prompt_contains_skeleton(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Target Format" in system_prompt
        assert "User Scenarios" in system_prompt

    def test_system_prompt_contains_system_instructions(
        self, tmp_path: Path
    ) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "senior software architect" in system_prompt

    def test_user_prompt_contains_service_name(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "Auth Service" in user_prompt

    def test_user_prompt_contains_slug(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "auth-service" in user_prompt

    def test_user_prompt_contains_description(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "authentication microservice" in user_prompt


# ── Constitution handling ────────────────────────────────────────────


class TestPromptAssemblerConstitution:
    def test_missing_constitution_handled_gracefully(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent" / "constitution.md"
        asm = PromptAssembler(constitution_path=nonexistent)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        assert result.ok is True

    def test_constitution_content_included_in_system_prompt(
        self, tmp_path: Path
    ) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text(
            "# Constitution\n\nPrinciple: Always test first",
            encoding="utf-8",
        )

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "Always test first" in system_prompt


# ── Prior artifacts ──────────────────────────────────────────────────


class TestPromptAssemblerArtifacts:
    def test_prior_artifacts_included_in_user_prompt(
        self, tmp_path: Path
    ) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()
        artifacts = {"spec.md": "# Spec\nFeature content"}

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, artifacts)

        _, user_prompt = result.value
        assert "Prior Artifacts" in user_prompt
        assert "Feature content" in user_prompt


# ── Budget trimming ──────────────────────────────────────────────────


class TestPromptAssemblerBudget:
    def test_budget_truncates_lowest_priority_content(
        self, tmp_path: Path
    ) -> None:
        constitution = tmp_path / "constitution.md"
        # Create a very large constitution (low priority in assembly)
        large_content = "X" * 50_000
        constitution.write_text(large_content, encoding="utf-8")

        # Very small budget forces truncation
        budget_tokens = 100
        asm = PromptAssembler(
            constitution_path=constitution,
            token_budget=budget_tokens,
        )
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        assert result.ok is True
        system_prompt, _ = result.value
        max_chars = budget_tokens * CHARS_PER_TOKEN_ESTIMATE
        assert len(system_prompt) <= max_chars + 100  # +margin for join

    def test_no_truncation_within_budget(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("Short constitution", encoding="utf-8")

        asm = PromptAssembler(
            constitution_path=constitution,
            token_budget=100_000,
        )
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "[TRUNCATED]" not in system_prompt

    def test_truncated_content_has_marker(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        # Make constitution large enough that it must be truncated, but
        # budget large enough that earlier sections fit and truncation
        # occurs on a later section rather than skipping it entirely.
        constitution.write_text("Y" * 500_000, encoding="utf-8")

        # Budget allows ~8000 chars — fits instructions + skeleton but
        # must truncate the oversized constitution section.
        asm = PromptAssembler(
            constitution_path=constitution,
            token_budget=2_000,
        )
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        system_prompt, _ = result.value
        assert "[TRUNCATED]" in system_prompt


# ── Features formatting ──────────────────────────────────────────────


class TestPromptAssemblerFeatures:
    def test_features_included_in_user_prompt(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = _make_service_ctx(tmp_path)
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "Login" in user_prompt

    def test_no_features_section_when_empty(self, tmp_path: Path) -> None:
        constitution = tmp_path / "constitution.md"
        constitution.write_text("", encoding="utf-8")

        asm = PromptAssembler(constitution_path=constitution)
        ctx = ServiceContext(
            service_slug="bare",
            service_name="Bare Service",
            architecture="monolithic",
            project_description="test",
            domain="test",
            features=(),
            dependencies=(),
            events=(),
            output_dir=tmp_path,
        )
        adapter = _make_adapter()

        result = asm.assemble(SPEC_PROMPT, ctx, adapter, {})

        _, user_prompt = result.value
        assert "## Features" not in user_prompt
