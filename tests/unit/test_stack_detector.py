"""Unit tests for StackDetector."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.stack_detector import StackDetector


class TestStackDetectorMarkers:
    def test_detects_dotnet_csproj(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.csproj").write_text("<Project />")
        assert StackDetector.detect(tmp_path) == "dotnet"

    def test_detects_nodejs_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "app"}')
        assert StackDetector.detect(tmp_path) == "nodejs"

    def test_detects_python_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        assert StackDetector.detect(tmp_path) == "python"

    def test_detects_go_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/app\n\ngo 1.21")
        assert StackDetector.detect(tmp_path) == "go"

    def test_detects_java_pom_xml(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project />")
        assert StackDetector.detect(tmp_path) == "java"

    def test_returns_agnostic_when_no_markers(self, tmp_path: Path) -> None:
        # Empty directory — no markers
        assert StackDetector.detect(tmp_path) == "agnostic"

    def test_returns_agnostic_for_unrecognized_files_only(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "README.md").write_text("# My project")
        (tmp_path / "Makefile").write_text("build:\n\t@echo done")
        assert StackDetector.detect(tmp_path) == "agnostic"


class TestStackDetectorAmbiguity:
    def test_dotnet_wins_over_nodejs_by_precedence(self, tmp_path: Path) -> None:
        # dotnet appears first in SUPPORTED_STACKS order
        # SUPPORTED_STACKS = ["dotnet", "nodejs", "python", "go", "java"]
        (tmp_path / "MyApp.csproj").write_text("<Project />")
        (tmp_path / "package.json").write_text('{"name": "app"}')
        assert StackDetector.detect(tmp_path) == "dotnet"

    def test_nodejs_wins_over_python_by_precedence(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "app"}')
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        assert StackDetector.detect(tmp_path) == "nodejs"

    def test_python_wins_over_go_by_precedence(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        (tmp_path / "go.mod").write_text("module app\n")
        assert StackDetector.detect(tmp_path) == "python"

    def test_go_wins_over_java_by_precedence(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module app\n")
        (tmp_path / "pom.xml").write_text("<project />")
        assert StackDetector.detect(tmp_path) == "go"

    def test_all_five_present_returns_first_in_order(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.csproj").write_text("<Project />")
        (tmp_path / "package.json").write_text('{"name": "app"}')
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        (tmp_path / "go.mod").write_text("module app\n")
        (tmp_path / "pom.xml").write_text("<project />")
        assert StackDetector.detect(tmp_path) == "dotnet"


class TestStackDetectorEdgeCases:
    def test_glob_csproj_extension_match(self, tmp_path: Path) -> None:
        # Any .csproj file name should match
        (tmp_path / "SomeOtherName.csproj").write_text("<Project />")
        assert StackDetector.detect(tmp_path) == "dotnet"

    def test_file_in_subdirectory_not_detected(self, tmp_path: Path) -> None:
        # Markers must be at project root, not in subdirectory
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "package.json").write_text('{"name": "app"}')
        assert StackDetector.detect(tmp_path) == "agnostic"

    def test_nonexistent_directory_returns_agnostic(self) -> None:
        result = StackDetector.detect(Path("/nonexistent/path/xyz"))
        assert result == "agnostic"
