"""OutputPostprocessor — preamble stripping + continuation + capping (Feature 015)."""

from __future__ import annotations

import re

from specforge.core.config import MAX_OUTPUT_CHARS, PHASE_REQUIRED_SECTIONS


class OutputPostprocessor:
    """Post-processing pipeline for LLM output."""

    @staticmethod
    def strip_preamble(content: str) -> str:
        """Remove text before the first markdown heading."""
        match = re.search(r"^#{1,6}\s", content, re.MULTILINE)
        if match:
            return content[match.start() :]
        return content

    @staticmethod
    def normalize_headings(content: str, expected_top_level: int = 1) -> str:
        """Normalize heading levels to match expected structure."""
        lines = content.split("\n")
        min_level = 6
        for line in lines:
            m = re.match(r"^(#{1,6})\s", line)
            if m:
                min_level = min(min_level, len(m.group(1)))

        if min_level == 6 or min_level == expected_top_level:
            return content

        shift = expected_top_level - min_level
        result = []
        for line in lines:
            m = re.match(r"^(#{1,6})(\s)", line)
            if m:
                hashes = m.group(1)
                new_level = max(1, min(6, len(hashes) + shift))
                result.append("#" * new_level + line[len(hashes) :])
            else:
                result.append(line)
        return "\n".join(result)

    @staticmethod
    def detect_truncation(
        phase: str,
        content: str,
        required_sections: tuple[str, ...] | None = None,
    ) -> bool:
        """Check for truncated output via missing sections + trailing."""
        if required_sections is None:
            required_sections = PHASE_REQUIRED_SECTIONS.get(phase, ())

        # Check 1: Required sections missing
        has_missing = False
        for heading in required_sections:
            pattern = re.compile(
                r"^#{1,3}\s*.*" + re.escape(heading),
                re.MULTILINE | re.IGNORECASE,
            )
            if not pattern.search(content):
                if heading.endswith(":") or heading.startswith("CHK-"):
                    if heading.rstrip(":") not in content:
                        has_missing = True
                        break
                else:
                    has_missing = True
                    break

        if not has_missing:
            return False

        # Check 2: Content ends abruptly
        stripped = content.rstrip()
        if not stripped:
            return True
        last_char = stripped[-1]
        if last_char not in ".!?)|\n`":
            return True
        # Check unclosed code block
        if content.count("```") % 2 != 0:
            return True
        return has_missing

    @staticmethod
    def build_continuation_prompt(
        partial_output: str,
    ) -> tuple[str, str]:
        """Construct continuation call prompts."""
        system = (
            "Continue the document exactly from where it left off. "
            "Do not repeat any content that has already been written. "
            "Do not add any preamble or commentary."
        )
        user = f"Partial document so far:\n\n{partial_output}\n\nContinue from here."
        return (system, user)

    @staticmethod
    def cap_output(
        content: str,
        max_chars: int = MAX_OUTPUT_CHARS,
    ) -> str:
        """Enforce maximum output character limit."""
        if len(content) <= max_chars:
            return content
        return content[:max_chars]
