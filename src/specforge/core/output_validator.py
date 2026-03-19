"""OutputValidator — per-phase required section checking (Feature 015)."""

from __future__ import annotations

import re

from specforge.core.config import PHASE_REQUIRED_SECTIONS
from specforge.core.result import Err, Ok, Result


class OutputValidator:
    """Validates LLM output against per-phase structural requirements."""

    def validate(self, phase: str, content: str) -> Result[str, list[str]]:
        """Check required sections present. Returns Ok or Err(missing)."""
        required = PHASE_REQUIRED_SECTIONS.get(phase, ())
        if not required:
            return Ok(content)

        missing = self._check_sections(phase, content, required)
        if missing:
            return Err(missing)
        return Ok(content)

    @staticmethod
    def _check_sections(
        phase: str,
        content: str,
        required: tuple[str, ...],
    ) -> list[str]:
        """Return list of missing section headings."""
        missing = []
        for heading in required:
            pattern = re.compile(
                r"^#{1,3}\s*.*" + re.escape(heading),
                re.MULTILINE | re.IGNORECASE,
            )
            if not pattern.search(content):
                # Also check for raw text match (e.g., "CHK-" in content)
                if heading.endswith(":") or heading.startswith("CHK-"):
                    if heading.rstrip(":") not in content:
                        missing.append(heading)
                else:
                    missing.append(heading)
        return missing

    @staticmethod
    def build_correction_prompt(
        phase: str,
        missing: list[str],
        original_output: str,
    ) -> str:
        """Construct retry prompt listing missing sections."""
        missing_list = ", ".join(f'"{m}"' for m in missing)
        return (
            f"The following required sections are missing from your "
            f"{phase} output: {missing_list}.\n\n"
            f"Please regenerate the complete document including ALL "
            f"required sections. Here is your previous output for "
            f"reference:\n\n{original_output}"
        )
