"""Unit tests for PromptLoader — T015 through T027."""

from __future__ import annotations

import json
import time
from pathlib import Path

from specforge.core.config import GOVERNANCE_DOMAINS, PRECEDENCE_ORDER
from specforge.core.prompt_models import PromptFile, PromptSet
from tests.unit.conftest import make_governance_fixtures


class TestPromptLoaderHappyPath:
    """T015 — PromptLoader returns Ok(PromptSet) with all 7 domain entries."""

    def test_returns_ok_with_all_7_domains(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert result.ok, f"Expected Ok but got Err: {result}"
        prompt_set: PromptSet = result.value
        assert set(prompt_set.files.keys()) == set(GOVERNANCE_DOMAINS)

    def test_precedence_order_matches_config(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert result.ok
        assert result.value.precedence == PRECEDENCE_ORDER

    def test_feature_id_stored_in_prompt_set(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("my-feature-42")

        assert result.ok
        assert result.value.feature_id == "my-feature-42"

    def test_each_file_is_prompt_file_instance(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert result.ok
        for domain, pf in result.value.files.items():
            assert isinstance(pf, PromptFile), f"Expected PromptFile for {domain}"


class TestPromptLoaderMissingFiles:
    """T016 — PromptLoader returns Err listing ALL missing files."""

    def test_err_when_single_file_missing(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        # Remove one file
        prompts_dir = tmp_path / ".specforge" / "prompts"
        (prompts_dir / "security.prompts.md").unlink()

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert not result.ok
        assert "security" in result.error

    def test_err_lists_all_missing_files(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        # Only write 4 domains, leaving 3 missing
        make_governance_fixtures(
            tmp_path, stack="dotnet", domains=["security", "architecture", "backend", "frontend"]
        )

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert not result.ok
        # All 3 missing domains should appear in the error
        assert "database" in result.error
        assert "testing" in result.error
        assert "cicd" in result.error

    def test_err_includes_file_path_hint(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(
            tmp_path, stack="dotnet", domains=["security", "architecture"]
        )

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat-001")

        assert not result.ok
        # Error should mention prompts directory or file paths
        assert "prompts" in result.error or ".specforge" in result.error


class TestPromptLoaderMetaParsing:
    """T017 — PromptLoader correctly parses ## Meta section."""

    def test_parses_domain(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        assert result.value.files["security"].meta.domain == "security"

    def test_parses_stack(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        # Non-agnostic domain with dotnet stack
        assert result.value.files["backend"].meta.stack == "dotnet"

    def test_parses_version(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        assert result.value.files["architecture"].meta.version == "1.0"

    def test_parses_precedence_as_int(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        meta = result.value.files["security"].meta
        assert isinstance(meta.precedence, int)
        assert meta.precedence == 1

    def test_parses_checksum(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        assert result.value.files["security"].meta.checksum == "abc123def456"


class TestPromptLoaderRulesParsing:
    """T018 — PromptLoader correctly parses ## Rules section."""

    def test_parses_rule_id(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rules = result.value.files["security"].rules
        assert len(rules) > 0
        assert rules[0].rule_id == "SECU-001"

    def test_parses_severity(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        assert rule.severity == "ERROR"

    def test_parses_scope(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        assert rule.scope == "all files"

    def test_parses_thresholds(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        threshold_keys = {t.key for t in rule.thresholds}
        assert "max_lines" in threshold_keys
        assert "min_coverage" in threshold_keys

    def test_threshold_values_parsed(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        threshold_map = {t.key: t.value for t in rule.thresholds}
        assert threshold_map["max_lines"] == "100"
        assert threshold_map["min_coverage"] == "80"

    def test_parses_example_correct(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        assert "correct example for security" in rule.example_correct

    def test_parses_example_incorrect(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        assert "incorrect example for security" in rule.example_incorrect

    def test_thresholds_are_tuple(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="agnostic")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        rule = result.value.files["security"].rules[0]
        assert isinstance(rule.thresholds, tuple)


class TestPromptLoaderFileResolution:
    """T019 — PromptLoader performs 2-step file resolution."""

    def test_prefers_stack_specific_over_agnostic(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        # Write both agnostic and stack-specific backend files
        prompts_dir = tmp_path / ".specforge" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Stack-specific
        (prompts_dir / "backend.dotnet.prompts.md").write_text(
            _make_fixture_content("backend", "dotnet", "BACK-001"), encoding="utf-8"
        )
        # Agnostic fallback
        (prompts_dir / "backend.prompts.md").write_text(
            _make_fixture_content("backend", "agnostic", "BACK-001"), encoding="utf-8"
        )
        # Write the rest as agnostic
        for domain in GOVERNANCE_DOMAINS:
            if domain == "backend":
                continue
            fname = f"{domain}.prompts.md"
            (prompts_dir / fname).write_text(
                _make_fixture_content(domain, "agnostic", f"{domain[:4].upper()}-001"),
                encoding="utf-8",
            )

        _write_config(tmp_path, "dotnet")

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        # The backend file should be the stack-specific one (stack=dotnet)
        assert result.value.files["backend"].meta.stack == "dotnet"

    def test_falls_back_to_agnostic_when_stack_specific_absent(
        self, tmp_path: Path
    ) -> None:
        from specforge.core.prompt_loader import PromptLoader

        prompts_dir = tmp_path / ".specforge" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Only write agnostic backend (no backend.dotnet.prompts.md)
        for domain in GOVERNANCE_DOMAINS:
            fname = f"{domain}.prompts.md"
            (prompts_dir / fname).write_text(
                _make_fixture_content(domain, "agnostic", f"{domain[:4].upper()}-001"),
                encoding="utf-8",
            )

        _write_config(tmp_path, "dotnet")

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        # Fallback: agnostic file used; meta.stack = "agnostic"
        assert result.value.files["backend"].meta.stack == "agnostic"

    def test_agnostic_domains_always_use_flat_filename(
        self, tmp_path: Path
    ) -> None:
        from specforge.core.prompt_loader import PromptLoader

        # Agnostic domains (architecture, security) use flat filename
        # even on a stack-specific project
        make_governance_fixtures(tmp_path, stack="dotnet")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        # architecture and security use agnostic filenames per AGNOSTIC_GOVERNANCE_DOMAINS
        # their file on disk is architecture.prompts.md (not architecture.dotnet.prompts.md)
        arch_path = result.value.files["architecture"].path
        assert "dotnet" not in arch_path.name


class TestPromptLoaderConfigHandling:
    """T020 — PromptLoader reads config.json; returns Err when missing/malformed."""

    def test_err_when_config_missing(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        # No .specforge/config.json at all
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert not result.ok
        assert "config" in result.error.lower() or "config.json" in result.error

    def test_err_when_config_malformed_json(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        config_dir = tmp_path / ".specforge"
        config_dir.mkdir()
        (config_dir / "config.json").write_text("not-valid-json{{{", encoding="utf-8")

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert not result.ok

    def test_err_when_config_missing_stack_key(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        config_dir = tmp_path / ".specforge"
        config_dir.mkdir()
        # Valid JSON but missing 'stack' key
        (config_dir / "config.json").write_text(
            json.dumps({"project_name": "test"}), encoding="utf-8"
        )

        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert not result.ok
        assert "stack" in result.error

    def test_reads_stack_from_config(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        make_governance_fixtures(tmp_path, stack="nodejs")
        loader = PromptLoader(tmp_path)
        result = loader.load_for_feature("feat")

        assert result.ok
        assert result.value.files["backend"].meta.stack == "nodejs"


class TestPromptLoaderPerformance:
    """T027 — Performance: load_for_feature() completes in ≤500 ms on 7 files of ~300 lines."""

    def test_load_completes_within_500ms(self, tmp_path: Path) -> None:
        from specforge.core.prompt_loader import PromptLoader

        # Write 7 large-ish fixture files (~300 lines each)
        prompts_dir = tmp_path / ".specforge" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        for domain in GOVERNANCE_DOMAINS:
            fname = f"{domain}.prompts.md"
            content = _make_large_fixture_content(domain, "agnostic", lines=300)
            (prompts_dir / fname).write_text(content, encoding="utf-8")

        _write_config(tmp_path, "agnostic")

        loader = PromptLoader(tmp_path)

        start = time.perf_counter()
        result = loader.load_for_feature("perf-test")
        elapsed = time.perf_counter() - start

        assert result.ok, f"Load failed: {result}"
        assert elapsed < 0.5, f"Load took {elapsed:.3f}s, expected < 0.5s"


# ── helpers ────────────────────────────────────────────────────────────


def _make_fixture_content(domain: str, stack: str, rule_id: str) -> str:
    precedence_map = {
        "security": 1, "architecture": 2, "backend": 3,
        "frontend": 3, "database": 3, "testing": 4, "cicd": 5,
    }
    precedence = precedence_map.get(domain, 3)
    return f"""\
<!-- Generated by SpecForge - do not edit manually above the Rules section -->

# {domain.title()} Governance Prompt

## Meta
domain: {domain}
stack: {stack}
version: 1.0
precedence: {precedence}
checksum: abc123def456

## Precedence
This file occupies position {precedence} in the conflict-resolution hierarchy:
`security (1) > architecture (2) > backend/frontend/database (3) > testing (4) > cicd (5)`

## Rules

### {rule_id}: Test Rule
severity: ERROR
scope: all files
rule: All code MUST follow the governance rules for {domain}.
threshold: max_lines=100, min_coverage=80
example_correct: |
  # correct example for {domain}
example_incorrect: |
  # incorrect example for {domain}
"""


def _make_large_fixture_content(domain: str, stack: str, lines: int = 300) -> str:
    """Generate fixture content with approximately `lines` lines."""
    base = _make_fixture_content(domain, stack, f"{domain[:4].upper()}-001")
    # Pad with additional rules to reach approximate line count
    extra_rules = []
    rule_num = 2
    while len(base.splitlines()) + len("\n".join(extra_rules).splitlines()) < lines:
        rule_id = f"{domain[:4].upper()}-{rule_num:03d}"
        extra_rules.append(f"""
### {rule_id}: Extra Rule {rule_num}
severity: WARNING
scope: all {domain} code
rule: Code MUST follow additional governance rule {rule_num} for {domain}.
threshold: extra_threshold_{rule_num}=50
example_correct: |
  # extra correct example {rule_num}
example_incorrect: |
  # extra incorrect example {rule_num}
""")
        rule_num += 1
    return base + "\n".join(extra_rules)


def _write_config(tmp_path: Path, stack: str) -> None:
    config_dir = tmp_path / ".specforge"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "project_name": "test-project",
        "stack": stack,
        "version": "1.0",
        "created_at": "2026-03-15",
    }
    (config_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
