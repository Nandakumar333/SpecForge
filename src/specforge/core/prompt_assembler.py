"""PromptAssembler — builds LLM prompts with token budgeting (Feature 015)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import GOVERNANCE_PHASE_MAP
from specforge.core.result import Ok, Result

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.phase_prompts import PhasePrompt
    from specforge.core.prompt_loader import PromptLoader
    from specforge.core.service_context import ServiceContext

# Existing constant reused for budget calculation
CHARS_PER_TOKEN_ESTIMATE: int = 4
DEFAULT_TOKEN_BUDGET: int = 100_000


class PromptAssembler:
    """Constructs complete prompts by combining all context sources."""

    def __init__(
        self,
        constitution_path: Path,
        prompt_loader: PromptLoader | None = None,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        governance_phase_map: dict[str, list[str]] | None = None,
    ) -> None:
        self._constitution_path = constitution_path
        self._prompt_loader = prompt_loader
        self._token_budget = token_budget
        self._governance_map = governance_phase_map or GOVERNANCE_PHASE_MAP

    def assemble(
        self,
        phase_prompt: PhasePrompt,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        prior_artifacts: dict[str, str],
        extra_context: dict[str, str] | None = None,
    ) -> Result[tuple[str, str], str]:
        """Build (system_prompt, user_prompt) with budget enforcement."""
        constitution = self._load_constitution()
        governance = self._load_governance(phase_prompt.phase_name)
        arch_context = self._serialize_architecture(adapter, service_ctx)
        artifacts_text = self._serialize_artifacts(prior_artifacts)

        system_parts = [
            ("instructions", phase_prompt.clean_markdown_instruction),
            ("instructions", phase_prompt.system_instructions),
            ("skeleton", f"## Target Format\n\n{phase_prompt.skeleton}"),
            ("architecture", arch_context),
            ("governance", governance),
            ("constitution", constitution),
        ]

        system_prompt = self._apply_budget(system_parts)

        user_parts = [
            f"Generate {phase_prompt.phase_name}.md for service: "
            f"{service_ctx.service_name}",
            f"\nService slug: {service_ctx.service_slug}",
            f"\nDescription: {service_ctx.project_description}",
        ]

        features_text = self._format_features(service_ctx)
        if features_text:
            user_parts.append(f"\n## Features\n\n{features_text}")

        if extra_context:
            for key, val in extra_context.items():
                user_parts.append(f"\n## {key}\n\n{val}")

        if artifacts_text:
            user_parts.append(f"\n## Prior Artifacts\n\n{artifacts_text}")

        user_prompt = "\n".join(user_parts)

        return Ok((system_prompt, user_prompt))

    def _load_constitution(self) -> str:
        """Read constitution.md text."""
        if self._constitution_path.exists():
            try:
                return self._constitution_path.read_text(encoding="utf-8")
            except OSError:
                return ""
        return ""

    def _load_governance(self, phase: str) -> str:
        """Load governance prompts filtered by phase map."""
        if not self._prompt_loader:
            return ""
        domains = self._governance_map.get(phase, [])
        if not domains:
            return ""
        try:
            result = self._prompt_loader.load_for_feature("015")
            if not result.ok:
                return ""
            prompt_set = result.value
            parts = []
            for pfile in prompt_set.files:
                if pfile.meta.domain in domains:
                    parts.append(pfile.raw_content)
            return "\n\n".join(parts)
        except Exception:
            return ""

    @staticmethod
    def _serialize_architecture(
        adapter: ArchitectureAdapter, service_ctx: ServiceContext
    ) -> str:
        """Serialize adapter context into prompt text."""
        if hasattr(adapter, "serialize_for_prompt"):
            return adapter.serialize_for_prompt()
        return ""

    @staticmethod
    def _serialize_artifacts(artifacts: dict[str, str]) -> str:
        """Concatenate prior artifacts with section markers."""
        if not artifacts:
            return ""
        parts = []
        for name, content in artifacts.items():
            parts.append(f"### {name}\n\n{content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _format_features(service_ctx: ServiceContext) -> str:
        """Format service features list."""
        if not service_ctx.features:
            return ""
        lines = []
        for f in service_ctx.features:
            lines.append(f"- **{f.display_name}** ({f.priority}): {f.description}")
        return "\n".join(lines)

    def _apply_budget(self, sections: list[tuple[str, str]]) -> str:
        """Priority-based trimming. Lower-index = higher priority."""
        max_chars = self._token_budget * CHARS_PER_TOKEN_ESTIMATE
        total = sum(len(s[1]) for s in sections)
        if total <= max_chars:
            return "\n\n".join(s[1] for s in sections if s[1])

        result_parts: list[str] = []
        remaining = max_chars
        for _priority, text in sections:
            if not text:
                continue
            if len(text) <= remaining:
                result_parts.append(text)
                remaining -= len(text)
            elif remaining > 100:
                result_parts.append(text[:remaining] + "\n[TRUNCATED]")
                remaining = 0
            # Skip if no budget left
        return "\n\n".join(result_parts)
