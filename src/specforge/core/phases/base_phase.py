"""BasePhase — template method pattern for pipeline phases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import TemplateType

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.llm_provider import LLMProvider
    from specforge.core.output_postprocessor import OutputPostprocessor
    from specforge.core.output_validator import OutputValidator
    from specforge.core.phase_prompts import PhasePrompt
    from specforge.core.prompt_assembler import PromptAssembler
    from specforge.core.service_context import ServiceContext
    from specforge.core.template_registry import TemplateRegistry
    from specforge.core.template_renderer import TemplateRenderer


class BasePhase(ABC):
    """Abstract base for pipeline phases using template method pattern."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Phase name (e.g., 'spec', 'research')."""

    @property
    @abstractmethod
    def artifact_filename(self) -> str:
        """Output filename (e.g., 'spec.md')."""

    def run(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        renderer: TemplateRenderer,
        registry: TemplateRegistry,
        input_artifacts: dict[str, str],
        *,
        provider: LLMProvider | None = None,
        assembler: PromptAssembler | None = None,
        validator: OutputValidator | None = None,
        postprocessor: OutputPostprocessor | None = None,
        dry_run_prompt: bool = False,
    ) -> Result:
        """Execute phase: LLM mode or template mode."""
        if provider and assembler:
            return self._run_llm_mode(
                service_ctx,
                adapter,
                input_artifacts,
                provider=provider,
                assembler=assembler,
                validator=validator,
                postprocessor=postprocessor,
                dry_run_prompt=dry_run_prompt,
            )
        return self._run_template_mode(
            service_ctx, adapter, renderer, registry, input_artifacts
        )

    def _run_template_mode(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        renderer: TemplateRenderer,
        registry: TemplateRegistry,
        input_artifacts: dict[str, str],
    ) -> Result:
        """Original template rendering path."""
        context = self._build_context(service_ctx, adapter, input_artifacts)
        render_result = renderer.render(
            self._template_name(),
            TemplateType.feature,
            context,
        )
        if not render_result.ok:
            return render_result
        return self._write_artifact(service_ctx, render_result.value)

    def _run_llm_mode(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
        *,
        provider: LLMProvider,
        assembler: PromptAssembler,
        validator: OutputValidator | None = None,
        postprocessor: OutputPostprocessor | None = None,
        dry_run_prompt: bool = False,
    ) -> Result:
        """LLM generation path with validation and retry."""
        from specforge.core.phase_prompts import PHASE_PROMPTS

        phase_prompt = PHASE_PROMPTS.get(self.name)
        if not phase_prompt:
            return Err(f"No PhasePrompt defined for phase '{self.name}'")

        extra_ctx = self._build_prompt(service_ctx, adapter, input_artifacts)
        assemble_result = assembler.assemble(
            phase_prompt, service_ctx, adapter, input_artifacts, extra_ctx
        )
        if not assemble_result.ok:
            return assemble_result

        system_prompt, user_prompt = assemble_result.value

        if dry_run_prompt:
            return self._write_prompt_file(service_ctx, system_prompt, user_prompt)

        return self._execute_llm_call(
            service_ctx,
            provider,
            system_prompt,
            user_prompt,
            phase_prompt,
            validator,
            postprocessor,
        )

    def _execute_llm_call(
        self,
        service_ctx: ServiceContext,
        provider: LLMProvider,
        system_prompt: str,
        user_prompt: str,
        phase_prompt: PhasePrompt,
        validator: OutputValidator | None,
        postprocessor: OutputPostprocessor | None,
    ) -> Result:
        """Call LLM, post-process, validate, retry if needed."""

        call_result = provider.call(system_prompt, user_prompt)
        if not call_result.ok:
            return call_result

        content = call_result.value
        if postprocessor:
            content = postprocessor.strip_preamble(content)
            content = postprocessor.normalize_headings(content)
            content = self._continuation_loop(provider, postprocessor, content)
            content = postprocessor.cap_output(content)

        if validator:
            val_result = validator.validate(self.name, content)
            if not val_result.ok:
                retry_result = self._retry_validation(
                    service_ctx,
                    provider,
                    validator,
                    postprocessor,
                    content,
                    val_result.error,
                )
                if retry_result is not None:
                    return retry_result
                return self._save_draft(service_ctx, content, val_result.error)

        return self._write_artifact(service_ctx, content)

    def _continuation_loop(
        self,
        provider: LLMProvider,
        postprocessor: OutputPostprocessor,
        content: str,
    ) -> str:
        """Issue continuation calls for truncated output."""
        from specforge.core.config import MAX_CONTINUATIONS, MAX_OUTPUT_CHARS

        for _ in range(MAX_CONTINUATIONS):
            if len(content) >= MAX_OUTPUT_CHARS:
                break
            if not postprocessor.detect_truncation(self.name, content):
                break
            sys_p, usr_p = postprocessor.build_continuation_prompt(content)
            cont_result = provider.call(sys_p, usr_p)
            if not cont_result.ok:
                break
            continuation = postprocessor.strip_preamble(cont_result.value)
            content += "\n" + continuation
        return content

    def _retry_validation(
        self,
        service_ctx: ServiceContext,
        provider: LLMProvider,
        validator: OutputValidator,
        postprocessor: OutputPostprocessor | None,
        content: str,
        missing: list[str],
    ) -> Result | None:
        """Retry with correction prompt. Returns Result or None."""
        from specforge.core.config import LLM_DEFAULT_MAX_RETRIES

        correction = validator.build_correction_prompt(self.name, missing, content)
        for _ in range(LLM_DEFAULT_MAX_RETRIES):
            retry_result = provider.call(
                "Regenerate the document with all required sections.",
                correction,
            )
            if not retry_result.ok:
                continue
            retried = retry_result.value
            if postprocessor:
                retried = postprocessor.strip_preamble(retried)
                retried = postprocessor.normalize_headings(retried)
            val = validator.validate(self.name, retried)
            if val.ok:
                return self._write_artifact(service_ctx, retried)
        return None

    def _save_draft(
        self,
        service_ctx: ServiceContext,
        content: str,
        missing: list[str],
    ) -> Result:
        """Save raw output as .draft.md and return Err."""
        import contextlib

        output_dir = service_ctx.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        draft_name = self.artifact_filename.replace(".md", ".draft.md")
        draft_path = output_dir / draft_name
        with contextlib.suppress(OSError):
            draft_path.write_text(content, encoding="utf-8")
        return Err(
            f"Validation failed for {self.artifact_filename}: "
            f"missing sections {missing}. Draft saved to {draft_name}"
        )

    def _write_prompt_file(
        self,
        service_ctx: ServiceContext,
        system_prompt: str,
        user_prompt: str,
    ) -> Result:
        """Write .prompt.md for dry-run mode."""
        output_dir = service_ctx.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_name = self.artifact_filename.replace(".md", ".prompt.md")
        prompt_path = output_dir / prompt_name
        content = (
            f"# System Prompt\n\n{system_prompt}\n\n"
            f"---\n\n# User Prompt\n\n{user_prompt}\n"
        )
        try:
            prompt_path.write_text(content, encoding="utf-8")
            return Ok(prompt_path)
        except OSError as exc:
            return Err(f"Failed to write prompt file: {exc}")

    def _build_prompt(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, str]:
        """Build extra context for LLM user prompt. Override per phase."""
        return {}

    @abstractmethod
    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build template context dict. Subclasses implement this."""

    def _template_name(self) -> str:
        """Template logical name for registry lookup."""
        return self.name

    def _post_render(  # noqa: B027
        self, service_ctx: ServiceContext, artifact_path: Path
    ) -> None:
        """Optional hook after artifact is written. Override if needed."""

    def _write_artifact(self, service_ctx: ServiceContext, content: str) -> Result:
        """Write rendered content to the artifact file."""
        output_dir = service_ctx.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_dir / self.artifact_filename
        try:
            artifact_path.write_text(content, encoding="utf-8")
            self._post_render(service_ctx, artifact_path)
            return Ok(artifact_path)
        except OSError as exc:
            return Err(f"Failed to write {self.artifact_filename}: {exc}")
