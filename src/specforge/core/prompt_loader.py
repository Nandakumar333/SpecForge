"""PromptLoader — loads governance prompt files into a PromptSet."""

from __future__ import annotations

import json
import re
from pathlib import Path

from specforge.core.config import (
    AGNOSTIC_GOVERNANCE_DOMAINS,
    GOVERNANCE_AGNOSTIC_FILE_PATTERN,
    GOVERNANCE_DOMAINS,
    GOVERNANCE_FILE_PATTERN,
    PRECEDENCE_ORDER,
)
from specforge.core.prompt_models import (
    ProjectMeta,
    PromptFile,
    PromptFileMeta,
    PromptRule,
    PromptSet,
    PromptThreshold,
)
from specforge.core.result import Err, Ok, Result


class PromptLoader:
    """Loads and parses all 7 governance prompt files from a project directory."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._prompts_dir = project_root / ".specforge" / "prompts"
        self._config_path = project_root / ".specforge" / "config.json"

    # ── Public API ──────────────────────────────────────────────────────

    def load_for_feature(self, feature_id: str) -> Result[PromptSet, str]:
        """Full pipeline: read config → resolve 7 paths → parse each → assemble PromptSet."""
        meta_result = self._read_project_meta()
        if not meta_result.ok:
            return Err(meta_result.error)

        meta = meta_result.value
        stack = meta.stack

        # Resolve and collect paths, accumulating missing file errors
        missing: list[str] = []
        files: dict[str, PromptFile] = {}

        for domain in GOVERNANCE_DOMAINS:
            path = self._resolve_file_path(domain, stack)
            if path is None:
                if domain in AGNOSTIC_GOVERNANCE_DOMAINS:
                    expected = GOVERNANCE_AGNOSTIC_FILE_PATTERN.format(domain=domain)
                elif stack == "agnostic":
                    expected = GOVERNANCE_AGNOSTIC_FILE_PATTERN.format(domain=domain)
                else:
                    expected = GOVERNANCE_FILE_PATTERN.format(domain=domain, stack=stack)
                missing.append(
                    f"  {domain}: {self._prompts_dir / expected}"
                )
                continue

            content = path.read_text(encoding="utf-8")
            parse_result = self._parse_prompt_file(path, content)
            if not parse_result.ok:
                return Err(f"Failed to parse {path}: {parse_result.error}")
            files[domain] = parse_result.value

        if missing:
            lines = "\n".join(missing)
            return Err(
                f"Missing governance files in {self._prompts_dir}:\n{lines}"
            )

        return Ok(
            PromptSet(
                files=files,
                precedence=list(PRECEDENCE_ORDER),
                feature_id=feature_id,
            )
        )

    # ── Internal helpers ────────────────────────────────────────────────

    def _read_project_meta(self) -> Result[ProjectMeta, str]:
        """Read and validate .specforge/config.json."""
        if not self._config_path.exists():
            return Err(
                f"config.json not found at {self._config_path}. "
                "Run 'specforge init' to initialize the project."
            )

        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return Err(f"Malformed config.json: {exc}")

        if "stack" not in data:
            return Err(
                "config.json is missing required 'stack' key. "
                "Expected keys: project_name, stack, version, created_at."
            )

        return Ok(
            ProjectMeta(
                project_name=data.get("project_name", ""),
                stack=data["stack"],
                version=data.get("version", "1.0"),
                created_at=data.get("created_at", ""),
            )
        )

    def _resolve_file_path(self, domain: str, stack: str) -> Path | None:
        """2-step resolution: stack-specific first, then agnostic fallback."""
        if domain in AGNOSTIC_GOVERNANCE_DOMAINS:
            # Agnostic domains always use flat filename
            path = self._prompts_dir / GOVERNANCE_AGNOSTIC_FILE_PATTERN.format(
                domain=domain
            )
            return path if path.exists() else None

        if stack and stack != "agnostic":
            # Step 1: try stack-specific file
            stack_path = self._prompts_dir / GOVERNANCE_FILE_PATTERN.format(
                domain=domain, stack=stack
            )
            if stack_path.exists():
                return stack_path

        # Step 2: try agnostic fallback
        fallback = self._prompts_dir / GOVERNANCE_AGNOSTIC_FILE_PATTERN.format(
            domain=domain
        )
        return fallback if fallback.exists() else None

    def _parse_meta_section(self, meta_text: str) -> Result[PromptFileMeta, str]:
        """Regex-based key-value extraction from ## Meta section text."""
        def _get(key: str) -> str | None:
            match = re.search(rf"^{key}:\s*(.+)$", meta_text, re.MULTILINE)
            return match.group(1).strip() if match else None

        domain = _get("domain")
        stack = _get("stack")
        version = _get("version")
        prec_str = _get("precedence")
        checksum = _get("checksum")

        missing = [k for k, v in [
            ("domain", domain), ("stack", stack), ("version", version),
            ("precedence", prec_str), ("checksum", checksum),
        ] if v is None]

        if missing:
            return Err(f"## Meta section missing keys: {', '.join(missing)}")

        try:
            precedence = int(prec_str)  # type: ignore[arg-type]
        except ValueError:
            return Err(f"## Meta 'precedence' must be an integer, got: {prec_str!r}")

        return Ok(
            PromptFileMeta(
                domain=domain,  # type: ignore[arg-type]
                stack=stack,  # type: ignore[arg-type]
                version=version,  # type: ignore[arg-type]
                precedence=precedence,
                checksum=checksum,  # type: ignore[arg-type]
            )
        )

    def _parse_rules_section(
        self, rules_text: str
    ) -> Result[tuple[PromptRule, ...], str]:
        """Split on `\\n### `, parse each rule block."""
        # Split into individual rule blocks
        raw_blocks = re.split(r"\n###\s+", rules_text)
        # First element may be empty preamble
        rule_blocks = [b for b in raw_blocks if b.strip()]

        rules: list[PromptRule] = []
        for block in rule_blocks:
            result = self._parse_rule_block(block)
            if not result.ok:
                return Err(result.error)
            rules.append(result.value)

        return Ok(tuple(rules))

    def _parse_rule_block(self, block: str) -> Result[PromptRule, str]:
        """Parse a single rule block (text after `### `)."""
        lines = block.splitlines()
        if not lines:
            return Err("Empty rule block")

        # First line: "RULE-ID: Title"
        header = lines[0].strip()
        header_match = re.match(r"^([\w-]+):\s*(.+)$", header)
        if not header_match:
            return Err(f"Invalid rule header: {header!r}")

        rule_id = header_match.group(1).strip()
        title = header_match.group(2).strip()

        # Remaining content as key:value pairs and multi-line blocks
        body = "\n".join(lines[1:])

        def _get(key: str) -> str:
            m = re.search(rf"^{key}:\s*(.+)$", body, re.MULTILINE)
            return m.group(1).strip() if m else ""

        severity = _get("severity")
        scope = _get("scope")
        description = _get("rule")

        # Parse threshold: key=value, key=value
        threshold_raw = _get("threshold")
        thresholds = _parse_thresholds(threshold_raw)

        # Parse multi-line example blocks (value starts on next line after `|`)
        example_correct = _extract_block_value(body, "example_correct")
        example_incorrect = _extract_block_value(body, "example_incorrect")

        return Ok(
            PromptRule(
                rule_id=rule_id,
                title=title,
                severity=severity,
                scope=scope,
                description=description,
                thresholds=thresholds,
                example_correct=example_correct,
                example_incorrect=example_incorrect,
            )
        )

    def _parse_prompt_file(
        self, path: Path, content: str
    ) -> Result[PromptFile, str]:
        """Orchestrate meta + rules parsing."""
        # Split on `\n## ` headings to extract sections
        sections = re.split(r"\n##\s+", "\n" + content)
        section_map: dict[str, str] = {}
        for section in sections:
            if not section.strip():
                continue
            first_line, _, rest = section.partition("\n")
            section_map[first_line.strip()] = rest

        if "Meta" not in section_map:
            return Err(f"No '## Meta' section found in {path}")
        if "Rules" not in section_map:
            return Err(f"No '## Rules' section found in {path}")

        meta_result = self._parse_meta_section(section_map["Meta"])
        if not meta_result.ok:
            return Err(f"{path}: {meta_result.error}")

        rules_result = self._parse_rules_section(section_map["Rules"])
        if not rules_result.ok:
            return Err(f"{path}: {rules_result.error}")

        return Ok(
            PromptFile(
                path=path,
                meta=meta_result.value,
                rules=rules_result.value,
                raw_content=content,
            )
        )


# ── Module-level helpers ────────────────────────────────────────────────


def _parse_thresholds(raw: str) -> tuple[PromptThreshold, ...]:
    """Parse 'key1=val1, key2=val2' into a tuple of PromptThreshold."""
    if not raw:
        return ()
    thresholds: list[PromptThreshold] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            key, _, value = pair.partition("=")
            thresholds.append(PromptThreshold(key=key.strip(), value=value.strip()))
    return tuple(thresholds)


def _extract_block_value(body: str, key: str) -> str:
    """Extract a block value started by `key: |` and indented lines following it."""
    pattern = rf"^{key}:\s*\|\s*\n((?:[ \t]+.*\n?)*)"
    match = re.search(pattern, body, re.MULTILINE)
    if not match:
        # Try inline value
        inline = re.search(rf"^{key}:\s*(.+)$", body, re.MULTILINE)
        return inline.group(1).strip() if inline else ""
    # Dedent the block
    block = match.group(1)
    lines = block.splitlines()
    if not lines:
        return ""
    # Find common indent
    indent_lengths = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    min_indent = min(indent_lengths) if indent_lengths else 0
    return "\n".join(ln[min_indent:] for ln in lines).strip()
