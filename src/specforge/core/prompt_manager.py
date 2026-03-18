"""PromptFileManager — generates governance prompt files from templates."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specforge.plugins.stack_plugin_base import PluginRule

from specforge.core.config import (
    AGNOSTIC_GOVERNANCE_DOMAINS,
    GOVERNANCE_AGNOSTIC_FILE_PATTERN,
    GOVERNANCE_DOMAINS,
    GOVERNANCE_FILE_PATTERN,
    SPECFORGE_CONFIG_FILE,
    STACK_HINTS,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer

# Domain → precedence value
_DOMAIN_PRECEDENCE: dict[str, int] = {
    "security": 1,
    "architecture": 2,
    "backend": 3,
    "frontend": 3,
    "database": 3,
    "testing": 4,
    "cicd": 5,
}


class PromptFileManager:
    """Generates, writes, and inspects governance prompt files."""

    def __init__(self, project_root: Path, registry: TemplateRegistry) -> None:
        self._root = project_root
        self._registry = registry
        self._renderer = TemplateRenderer(registry)
        self._prompts_dir = project_root / ".specforge" / "prompts"

    # ── Public API ──────────────────────────────────────────────────────

    def resolve_path(self, domain: str, stack: str) -> Path:
        """Return the output file path for a domain + stack combination."""
        if domain in AGNOSTIC_GOVERNANCE_DOMAINS or stack == "agnostic":
            filename = GOVERNANCE_AGNOSTIC_FILE_PATTERN.format(domain=domain)
        else:
            filename = GOVERNANCE_FILE_PATTERN.format(domain=domain, stack=stack)
        return self._prompts_dir / filename

    def generate_one(
        self,
        domain: str,
        project_name: str,
        stack: str,
        extra_rules: list[PluginRule] | None = None,
    ) -> Result[Path, str]:
        """Render one governance template and write it to disk."""
        output_path = self.resolve_path(domain, stack)

        context = self._build_context(domain, project_name, stack)
        # Step 1: render with empty checksum placeholder
        context["checksum"] = ""
        render_result = self._renderer.render(
            domain,
            TemplateType.governance,
            context,
            stack=stack if domain not in AGNOSTIC_GOVERNANCE_DOMAINS else "agnostic",
        )
        if not render_result.ok:
            return Err(
                f"Failed to render governance template for '{domain}': "
                f"{render_result.error}"
            )

        rendered = render_result.value

        # Append plugin rules if provided
        if extra_rules:
            from specforge.plugins.rule_formatter import format_plugin_rules

            rendered += "\n" + format_plugin_rules(extra_rules)

        # Step 2: compute SHA-256 of the rendered content
        checksum = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        # Step 3: inject checksum back into ## Meta section
        rendered = re.sub(
            r"^(checksum:)\s*$",
            f"\\1 {checksum}",
            rendered,
            flags=re.MULTILINE,
        )

        # Write to disk with Unix line endings to ensure consistent hashing
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8", newline="\n")

        return Ok(output_path)

    def generate(
        self,
        project_name: str,
        stack: str,
        extra_rules_by_domain: dict[str, list[PluginRule]] | None = None,
    ) -> Result[list[Path], str]:
        """Generate all 7 governance files and write config.json."""
        paths: list[Path] = []
        for domain in GOVERNANCE_DOMAINS:
            domain_rules = (extra_rules_by_domain or {}).get(domain)
            result = self.generate_one(
                domain, project_name, stack, extra_rules=domain_rules
            )
            if not result.ok:
                return Err(result.error)
            paths.append(result.value)

        # Write config.json
        config_result = self._write_config(project_name, stack)
        if not config_result.ok:
            return Err(config_result.error)

        return Ok(paths)

    def is_customized(self, file_path: Path, stack: str) -> Result[bool, str]:
        """Return True if file_path has been modified from its generated content.

        Strategy: re-render the template, inject the expected checksum, and compare
        the sha256 of the fully-assembled expected file against the sha256 of the
        actual file on disk. Any byte difference (including appended content,
        changed rules, etc.) is detected as customization.
        """
        if not file_path.exists():
            return Err(f"File not found: {file_path}")

        # Determine domain from filename
        domain = _domain_from_filename(file_path.name)
        if domain is None:
            return Err(f"Cannot determine domain from filename: {file_path.name}")

        # Read project_name from config.json to reproduce identical context
        project_name = self._read_project_name()

        # Re-render with empty checksum (same as at generation time)
        context = self._build_context(domain, project_name, stack)
        context["checksum"] = ""
        if domain not in AGNOSTIC_GOVERNANCE_DOMAINS:
            render_stack = stack
        else:
            render_stack = "agnostic"
        render_result = self._renderer.render(
            domain,
            TemplateType.governance,
            context,
            stack=render_stack,
        )
        if not render_result.ok:
            return Err(
                f"Cannot re-render template for comparison: {render_result.error}"
            )

        fresh_rendered = render_result.value

        # Inject expected checksum to produce the canonical file content
        expected_checksum = hashlib.sha256(fresh_rendered.encode("utf-8")).hexdigest()
        canonical = re.sub(
            r"^(checksum:)\s*$",
            f"\\1 {expected_checksum}",
            fresh_rendered,
            flags=re.MULTILINE,
        )

        # Compare actual file hash against canonical hash.
        # Read actual bytes normalizing line endings to Unix (\n) for cross-platform
        # consistency — files are written with newline="\n" so this is a no-op on Unix
        # and handles CRLF on Windows if files were edited by external tools.
        actual_bytes = file_path.read_bytes().replace(b"\r\n", b"\n")
        actual_hash = hashlib.sha256(actual_bytes).hexdigest()
        canonical_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return Ok(actual_hash != canonical_hash)

    def _read_project_name(self) -> str:
        """Read project_name from config.json, falling back to empty string."""
        config_path = self._root / SPECFORGE_CONFIG_FILE
        if not config_path.exists():
            return ""
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data.get("project_name", "")
        except (json.JSONDecodeError, OSError):
            return ""

    # ── Internal helpers ────────────────────────────────────────────────

    def _build_context(
        self, domain: str, project_name: str, stack: str
    ) -> dict[str, Any]:
        """Build Jinja2 context for a governance template."""
        return {
            "project_name": project_name,
            "domain": domain,
            "stack": stack if domain not in AGNOSTIC_GOVERNANCE_DOMAINS else "agnostic",
            "stack_hint": STACK_HINTS.get(stack, "Language-agnostic"),
            "precedence": _DOMAIN_PRECEDENCE.get(domain, 3),
            "date": date.today().isoformat(),
            "agent": "agnostic",
            "checksum": "",
        }

    def _write_config(
        self,
        project_name: str,
        stack: str,
    ) -> Result[Path, str]:
        """Write .specforge/config.json."""
        config_path = self._root / SPECFORGE_CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "project_name": project_name,
            "stack": stack,
            "version": "1.0",
            "created_at": date.today().isoformat(),
        }
        try:
            config_path.write_text(
                json.dumps(config, indent=2), encoding="utf-8"
            )
            return Ok(config_path)
        except OSError as exc:
            return Err(f"Failed to write config.json: {exc}")


# ── Module-level helpers ────────────────────────────────────────────────


def _write_config_json(
    project_root: Path, project_name: str, stack: str
) -> Result[Path, str]:
    """Write .specforge/config.json as a standalone function."""
    config_path = project_root / SPECFORGE_CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "project_name": project_name,
        "stack": stack,
        "version": "1.0",
        "created_at": date.today().isoformat(),
    }
    try:
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return Ok(config_path)
    except OSError as exc:
        return Err(f"Failed to write config.json: {exc}")


def _extract_checksum(content: str) -> str:
    """Extract the checksum value from ## Meta section."""
    match = re.search(r"^checksum:\s*(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _domain_from_filename(filename: str) -> str | None:
    """Extract domain from governance filename like 'backend.dotnet.prompts.md'."""
    # Remove .prompts.md suffix
    stem = filename
    if stem.endswith(".prompts.md"):
        stem = stem[: -len(".prompts.md")]
    else:
        return None
    # First part before '.' is the domain
    parts = stem.split(".")
    return parts[0] if parts else None
