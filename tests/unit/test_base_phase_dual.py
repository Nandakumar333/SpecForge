"""Unit tests for BasePhase dual-mode run() — template vs LLM mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from specforge.core.phases.base_phase import BasePhase
from specforge.core.result import Err, Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


class _TestPhase(BasePhase):
    """Concrete subclass for testing BasePhase."""

    @property
    def name(self) -> str:
        return "spec"

    @property
    def artifact_filename(self) -> str:
        return "spec.md"

    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: Any,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        return {"test": True}


def _make_service_ctx(tmp_path: Path) -> ServiceContext:
    return ServiceContext(
        service_slug="test-svc",
        service_name="Test Service",
        architecture="monolithic",
        project_description="A test project",
        domain="test",
        features=(
            FeatureInfo("001", "feat-a", "Feature A", "A feature", "P0", "core"),
        ),
        dependencies=(),
        events=(),
        output_dir=tmp_path,
    )


# ── Template mode (no provider) ─────────────────────────────────────


class TestBasePhaseTemplateMode:
    def test_run_without_provider_uses_template_mode(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_service_ctx(tmp_path)
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Spec\nRendered content")
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok is True
        renderer.render.assert_called_once()

    def test_template_mode_writes_artifact(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Spec\nContent")
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok is True
        artifact_path = result.value
        assert artifact_path.exists()
        assert artifact_path.name == "spec.md"

    def test_template_mode_propagates_render_error(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_service_ctx(tmp_path)
        renderer = MagicMock()
        renderer.render.return_value = Err("Template not found")
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(ctx, adapter, renderer, registry, {})

        assert result.ok is False
        assert "Template not found" in result.error


# ── LLM mode (with provider + assembler) ────────────────────────────


class TestBasePhaseLLMMode:
    def test_run_with_provider_uses_llm_mode(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        provider.call.return_value = Ok(
            "# Feature Specification: Test\n\n"
            "## User Scenarios & Testing\n\nScenarios\n\n"
            "## Requirements\n\nFR-001\n\n"
            "## Success Criteria\n\nSC-001\n"
        )
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("system prompt", "user prompt"))
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
        )

        assert result.ok is True
        provider.call.assert_called_once()
        renderer.render.assert_not_called()

    def test_llm_mode_writes_artifact(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        provider.call.return_value = Ok("# Generated\nContent here")
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
        )

        assert result.ok is True
        artifact_path = result.value
        assert artifact_path.exists()
        content = artifact_path.read_text(encoding="utf-8")
        assert "Generated" in content

    def test_llm_mode_assembler_error_propagated(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        assembler = MagicMock()
        assembler.assemble.return_value = Err("Assembly failed")
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
        )

        assert result.ok is False
        assert "Assembly failed" in result.error

    def test_llm_mode_provider_error_propagated(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        provider.call.return_value = Err("LLM call failed")
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
        )

        assert result.ok is False
        assert "LLM call failed" in result.error


# ── Dry run mode ─────────────────────────────────────────────────────


class TestBasePhaseDryRun:
    def test_dry_run_writes_prompt_file(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(
            ("system instructions here", "user query here")
        )
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
            dry_run_prompt=True,
        )

        assert result.ok is True
        prompt_path = result.value
        assert prompt_path.name == "spec.prompt.md"
        assert prompt_path.exists()
        content = prompt_path.read_text(encoding="utf-8")
        assert "System Prompt" in content
        assert "User Prompt" in content
        assert "system instructions here" in content
        assert "user query here" in content

    def test_dry_run_does_not_call_provider(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))
        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
            dry_run_prompt=True,
        )

        provider.call.assert_not_called()


# ── Validation + retry ───────────────────────────────────────────────


class TestBasePhaseValidation:
    def test_validation_failure_triggers_retry(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)

        # First call returns incomplete content, retry returns complete content
        provider = MagicMock()
        provider.call.side_effect = [
            Ok("# Spec\nIncomplete output"),
            Ok(
                "# Feature Specification\n\n"
                "## User Scenarios & Testing\n\nScenarios\n\n"
                "## Requirements\n\nFR-001\n\n"
                "## Success Criteria\n\nSC-001\n"
            ),
        ]

        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))

        validator = MagicMock()
        # First validate fails, retry validate passes
        validator.validate.side_effect = [
            Err(["Requirements", "Success Criteria"]),
            Ok("valid content"),
        ]
        validator.build_correction_prompt.return_value = "Please add missing sections"

        postprocessor = MagicMock()
        postprocessor.strip_preamble.side_effect = lambda x: x
        postprocessor.normalize_headings.side_effect = lambda x, **kw: x
        postprocessor.detect_truncation.return_value = False
        postprocessor.cap_output.side_effect = lambda x: x

        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
            validator=validator,
            postprocessor=postprocessor,
        )

        assert result.ok is True
        assert provider.call.call_count == 2
        validator.build_correction_prompt.assert_called_once()

    def test_failed_validation_after_retries_saves_draft(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_service_ctx(tmp_path)

        provider = MagicMock()
        # Initial call + all retry attempts fail
        provider.call.return_value = Ok("# Spec\nIncomplete output")

        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))

        validator = MagicMock()
        validator.validate.return_value = Err(["Requirements"])
        validator.build_correction_prompt.return_value = "Fix missing sections"

        postprocessor = MagicMock()
        postprocessor.strip_preamble.side_effect = lambda x: x
        postprocessor.normalize_headings.side_effect = lambda x, **kw: x
        postprocessor.detect_truncation.return_value = False
        postprocessor.cap_output.side_effect = lambda x: x

        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        result = phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
            validator=validator,
            postprocessor=postprocessor,
        )

        assert result.ok is False
        assert "Validation failed" in result.error
        assert "draft" in result.error.lower()

        draft_path = tmp_path / "spec.draft.md"
        assert draft_path.exists()
        draft_content = draft_path.read_text(encoding="utf-8")
        assert "Incomplete output" in draft_content


# ── Postprocessor integration ────────────────────────────────────────


class TestBasePhasePostprocessor:
    def test_postprocessor_pipeline_applied(self, tmp_path: Path) -> None:
        ctx = _make_service_ctx(tmp_path)
        provider = MagicMock()
        provider.call.return_value = Ok("Sure!\n\n# Generated\nContent")
        assembler = MagicMock()
        assembler.assemble.return_value = Ok(("sys", "usr"))

        postprocessor = MagicMock()
        postprocessor.strip_preamble.return_value = "# Generated\nContent"
        postprocessor.normalize_headings.return_value = "# Generated\nContent"
        postprocessor.detect_truncation.return_value = False
        postprocessor.cap_output.return_value = "# Generated\nContent"

        renderer = MagicMock()
        registry = MagicMock()
        adapter = MagicMock()

        phase = _TestPhase()
        phase.run(
            ctx, adapter, renderer, registry, {},
            provider=provider,
            assembler=assembler,
            postprocessor=postprocessor,
        )

        postprocessor.strip_preamble.assert_called_once()
        postprocessor.normalize_headings.assert_called_once()
        postprocessor.cap_output.assert_called_once()
