"""Unit tests for PromptFileManager — T038 through T041, T049."""

from __future__ import annotations

import json
from pathlib import Path

from specforge.core.config import GOVERNANCE_DOMAINS
from specforge.core.prompt_loader import PromptLoader


class TestPromptFileManagerResolvePath:
    """T038 — resolve_path() returns correct filenames."""

    def test_dotnet_backend_is_stack_specific(self) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=Path("/tmp"), registry=registry)

        path = mgr.resolve_path("backend", "dotnet")
        assert path.name == "backend.dotnet.prompts.md"

    def test_architecture_is_agnostic_regardless_of_stack(self) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=Path("/tmp"), registry=registry)

        path = mgr.resolve_path("architecture", "dotnet")
        assert path.name == "architecture.prompts.md"

    def test_security_is_agnostic_regardless_of_stack(self) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=Path("/tmp"), registry=registry)

        path = mgr.resolve_path("security", "nodejs")
        assert path.name == "security.prompts.md"

    def test_backend_agnostic_stack_is_flat(self) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=Path("/tmp"), registry=registry)

        path = mgr.resolve_path("backend", "agnostic")
        assert path.name == "backend.prompts.md"

    def test_all_stacks_produce_expected_backend_filenames(self) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=Path("/tmp"), registry=registry)

        expected = {
            "dotnet": "backend.dotnet.prompts.md",
            "nodejs": "backend.nodejs.prompts.md",
            "python": "backend.python.prompts.md",
            "go": "backend.go.prompts.md",
            "java": "backend.java.prompts.md",
            "agnostic": "backend.prompts.md",
        }
        for stack, expected_name in expected.items():
            path = mgr.resolve_path("backend", stack)
            assert path.name == expected_name, f"Stack {stack!r}: expected {expected_name!r}, got {path.name!r}"


class TestPromptFileManagerGenerate:
    """T039 — generate() writes exactly 7 files to .specforge/prompts/ and config.json."""

    def test_generates_exactly_7_files(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        result = mgr.generate(project_name="myapp", stack="dotnet")

        assert result.ok, f"generate() failed: {result}"
        paths = result.value
        assert len(paths) == 7

    def test_generated_files_exist_on_disk(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        result = mgr.generate(project_name="myapp", stack="dotnet")
        assert result.ok

        for path in result.value:
            assert path.exists(), f"Expected file at {path} but it does not exist"

    def test_all_governance_domains_have_files(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        result = mgr.generate(project_name="myapp", stack="dotnet")
        assert result.ok

        prompts_dir = tmp_path / ".specforge" / "prompts"
        written_stems = {p.stem for p in result.value}
        for domain in GOVERNANCE_DOMAINS:
            # At least one file for each domain
            assert any(domain in name for name in written_stems), (
                f"No governance file found for domain '{domain}'"
            )

    def test_writes_config_json(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        result = mgr.generate(project_name="myapp", stack="dotnet")
        assert result.ok

        config_path = tmp_path / ".specforge" / "config.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert config["stack"] == "dotnet"
        assert config["project_name"] == "myapp"

    def test_generate_agnostic_stack(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        result = mgr.generate(project_name="myapp", stack="agnostic")
        assert result.ok
        assert len(result.value) == 7


class TestPromptFileManagerGenerateParseable:
    """T040 — each generated file is immediately parseable by PromptLoader."""

    def test_generated_files_parseable_dotnet(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        gen_result = mgr.generate(project_name="myapp", stack="dotnet")
        assert gen_result.ok

        loader = PromptLoader(tmp_path)
        for path in gen_result.value:
            content = path.read_text(encoding="utf-8")
            parse_result = loader._parse_prompt_file(path, content)
            assert parse_result.ok, (
                f"Failed to parse {path.name}: {parse_result.error}"
            )

    def test_load_for_feature_succeeds_after_generate(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        gen_result = mgr.generate(project_name="myapp", stack="nodejs")
        assert gen_result.ok

        loader = PromptLoader(tmp_path)
        load_result = loader.load_for_feature("feat-001")
        assert load_result.ok, f"load_for_feature failed: {load_result.error}"
        assert set(load_result.value.files.keys()) == set(GOVERNANCE_DOMAINS)

    def test_generated_files_have_non_empty_rules(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        gen_result = mgr.generate(project_name="myapp", stack="python")
        assert gen_result.ok

        loader = PromptLoader(tmp_path)
        load_result = loader.load_for_feature("feat-001")
        assert load_result.ok

        for domain, pf in load_result.value.files.items():
            assert len(pf.rules) > 0, f"Domain '{domain}' has no parsed rules"


class TestPromptFileManagerCustomization:
    """T049 — is_customized() returns False for fresh files and True after edit."""

    def test_freshly_generated_file_is_not_customized(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        mgr.generate(project_name="myapp", stack="dotnet")

        backend_path = tmp_path / ".specforge" / "prompts" / "backend.dotnet.prompts.md"
        result = mgr.is_customized(backend_path, "dotnet")
        assert result.ok
        assert result.value is False

    def test_edited_file_is_customized(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        mgr.generate(project_name="myapp", stack="dotnet")

        backend_path = tmp_path / ".specforge" / "prompts" / "backend.dotnet.prompts.md"
        # Edit file
        original = backend_path.read_text(encoding="utf-8")
        backend_path.write_text(
            original + "\n# Custom addition\n", encoding="utf-8"
        )

        result = mgr.is_customized(backend_path, "dotnet")
        assert result.ok
        assert result.value is True

    def test_architecture_file_not_customized_when_fresh(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)
        mgr.generate(project_name="myapp", stack="dotnet")

        arch_path = tmp_path / ".specforge" / "prompts" / "architecture.prompts.md"
        result = mgr.is_customized(arch_path, "dotnet")
        assert result.ok
        assert result.value is False

    def test_missing_file_returns_err(self, tmp_path: Path) -> None:
        from specforge.core.prompt_manager import PromptFileManager
        from specforge.core.template_registry import TemplateRegistry

        registry = TemplateRegistry()
        registry.discover()
        mgr = PromptFileManager(project_root=tmp_path, registry=registry)

        nonexistent = tmp_path / ".specforge" / "prompts" / "nonexistent.prompts.md"
        result = mgr.is_customized(nonexistent, "dotnet")
        assert not result.ok
