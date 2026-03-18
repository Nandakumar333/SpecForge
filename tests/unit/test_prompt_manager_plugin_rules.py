"""Unit tests for PromptFileManager plugin rule integration."""

from __future__ import annotations

import hashlib
from pathlib import Path

from specforge.core.prompt_manager import PromptFileManager
from specforge.core.template_registry import TemplateRegistry
from specforge.plugins.stack_plugin_base import PluginRule


def _make_rule(
    rule_id: str = "BACK-001",
    title: str = "Test Rule",
    severity: str = "ERROR",
    scope: str = "all files",
    description: str = "All code MUST follow this rule.",
    thresholds: dict[str, str] | None = None,
    example_correct: str = "# correct",
    example_incorrect: str = "# incorrect",
) -> PluginRule:
    return PluginRule(
        rule_id=rule_id,
        title=title,
        severity=severity,
        scope=scope,
        description=description,
        thresholds=thresholds or {},
        example_correct=example_correct,
        example_incorrect=example_incorrect,
    )


def _make_manager(tmp_path: Path) -> PromptFileManager:
    registry = TemplateRegistry()
    registry.discover()
    return PromptFileManager(project_root=tmp_path, registry=registry)


class TestGenerateOneWithoutRules:
    """generate_one() with extra_rules=None — backward compatibility."""

    def test_none_rules_generates_normally(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        result = mgr.generate_one("backend", "dotnet", "test-project", extra_rules=None)
        assert result.ok

    def test_none_rules_identical_to_default(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        # Generate without extra_rules
        r1 = mgr.generate_one("backend", "dotnet", "test-project")
        assert r1.ok
        content1 = r1.value.read_text(encoding="utf-8")

        # Generate again explicitly with None
        mgr2 = _make_manager(tmp_path)
        r2 = mgr2.generate_one("backend", "dotnet", "test-project", extra_rules=None)
        assert r2.ok
        content2 = r2.value.read_text(encoding="utf-8")
        assert content1 == content2


class TestGenerateOneWithRules:
    """generate_one() with extra_rules appends formatted content."""

    def test_rules_appended_to_output(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        rule = _make_rule(rule_id="BACK-DOTNET-001", title="Custom Rule")
        result = mgr.generate_one(
            "backend", "dotnet", "test-project", extra_rules=[rule]
        )
        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "### BACK-DOTNET-001: Custom Rule" in content

    def test_checksum_changes_with_rules(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)

        # Without rules
        r1 = mgr.generate_one("backend", "dotnet", "test-project")
        assert r1.ok
        content1 = r1.value.read_text(encoding="utf-8")

        # With rules — use a new tmp_path subdirectory for isolation
        sub = tmp_path / "with_rules"
        sub.mkdir()
        mgr2 = _make_manager(sub)
        rule = _make_rule(rule_id="BACK-001", title="Extra")
        r2 = mgr2.generate_one(
            "backend", "dotnet", "test-project", extra_rules=[rule]
        )
        assert r2.ok
        content2 = r2.value.read_text(encoding="utf-8")

        # Checksums should differ
        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()
        assert hash1 != hash2

    def test_severity_in_appended_content(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        rule = _make_rule(severity="WARNING")
        result = mgr.generate_one(
            "backend", "dotnet", "test-project", extra_rules=[rule]
        )
        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "severity: WARNING" in content


class TestGenerateWithRulesByDomain:
    """generate() passes domain-specific rules."""

    def test_rules_applied_to_matching_domain(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        rule = _make_rule(rule_id="BACK-EXTRA-001", title="Backend Only")
        result = mgr.generate(
            "test-project",
            "dotnet",
            extra_rules_by_domain={"backend": [rule]},
        )
        assert result.ok

        # Find the backend file
        backend_file = [p for p in result.value if "backend" in p.name][0]
        content = backend_file.read_text(encoding="utf-8")
        assert "### BACK-EXTRA-001: Backend Only" in content

    def test_rules_not_applied_to_other_domains(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        rule = _make_rule(rule_id="BACK-EXTRA-001", title="Backend Only")
        result = mgr.generate(
            "test-project",
            "dotnet",
            extra_rules_by_domain={"backend": [rule]},
        )
        assert result.ok

        # Non-backend files should NOT contain the rule
        non_backend = [p for p in result.value if "backend" not in p.name]
        for path in non_backend:
            content = path.read_text(encoding="utf-8")
            assert "BACK-EXTRA-001" not in content

    def test_none_extra_rules_generates_normally(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        result = mgr.generate(
            "test-project",
            "dotnet",
            extra_rules_by_domain=None,
        )
        assert result.ok
        assert len(result.value) == 7

    def test_empty_dict_generates_normally(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        result = mgr.generate(
            "test-project",
            "dotnet",
            extra_rules_by_domain={},
        )
        assert result.ok
        assert len(result.value) == 7
