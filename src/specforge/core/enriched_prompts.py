"""EnrichedPromptBuilder — rich phase prompt enrichment via Jinja2 (Feature 017)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from specforge.core.config import MAX_CLASS_LINES, MAX_FUNCTION_LINES
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.phase_prompts import PhasePrompt
    from specforge.core.prompt_loader import PromptLoader
    from specforge.core.service_context import ServiceContext

logger = logging.getLogger(__name__)

_QUALITY_THRESHOLDS = {
    "max_function_lines": MAX_FUNCTION_LINES,
    "max_class_lines": MAX_CLASS_LINES,
    "type_hints": "required on all function signatures",
    "error_handling": "Result[T, E] for recoverable errors",
    "constructor_injection": "required for all dependencies",
}


class EnrichedPromptBuilder:
    """Renders enrichment templates for forge phase prompts."""

    def __init__(
        self,
        template_dir: Path,
        governance_loader: PromptLoader | None = None,
    ) -> None:
        self._template_dir = template_dir
        self._governance_loader = governance_loader
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_enrichment(
        self,
        phase_prompt: PhasePrompt,
        service_context: ServiceContext,
        arch_type: str,
    ) -> Result[str, str]:
        """Render enrichment template for a phase."""
        template_name = getattr(phase_prompt, "enrichment_template", None)
        if not template_name:
            return Ok("")

        governance_rules = self._load_governance_rules()
        context = self._build_context(
            service_context, arch_type, governance_rules,
        )

        try:
            template = self._env.get_template(template_name)
            rendered = template.render(**context)
            return Ok(rendered)
        except TemplateNotFound:
            logger.warning("Enrichment template not found: %s", template_name)
            return Ok("")
        except Exception as exc:
            return Err(f"Enrichment render failed: {exc}")

    def _load_governance_rules(self) -> list[str]:
        if not self._governance_loader:
            return []
        try:
            result = self._governance_loader.load()
            if not result.ok or result.value is None:
                return []
            rules: list[str] = []
            for pfile in result.value.files:
                for rule in pfile.rules:
                    rules.append(f"{rule.domain}: {rule.text}")
            return rules[:20]
        except Exception:
            return []

    @staticmethod
    def _build_context(
        service_context: ServiceContext,
        arch_type: str,
        governance_rules: list[str],
    ) -> dict:
        return {
            "service_name": service_context.service_name,
            "service_slug": service_context.service_slug,
            "service_description": service_context.project_description,
            "arch_type": arch_type,
            "governance_rules": governance_rules,
            "quality_thresholds": _QUALITY_THRESHOLDS,
            "features": [
                {"name": f.display_name, "description": f.description}
                for f in service_context.features
            ],
            "dependencies": [
                {"target": d.target_slug, "pattern": d.pattern}
                for d in service_context.dependencies
            ],
        }
