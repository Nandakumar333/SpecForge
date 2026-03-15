"""Unit tests for StackAdapter."""

from __future__ import annotations

from specforge.core.stack_adapter import StackAdapter


class TestStackAdapter:
    def test_dotnet_context(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("dotnet")
        assert profile.stack_name == "dotnet"
        assert profile.stack_hint == "C#/.NET"
        assert "C#" in profile.conventions

    def test_python_context(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("python")
        assert profile.stack_name == "python"
        assert "pytest" in profile.testing_hint

    def test_nodejs_context(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("nodejs")
        assert profile.stack_name == "nodejs"
        assert "Node" in profile.stack_hint

    def test_unknown_stack_returns_agnostic(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("unknown_stack")
        assert profile.stack_name == "agnostic"
        assert profile.stack_hint == "Language-agnostic"

    def test_supported_stacks_count(self) -> None:
        adapter = StackAdapter()
        stacks = adapter.supported_stacks()
        assert len(stacks) == 5
        assert "dotnet" in stacks
        assert "nodejs" in stacks
        assert "python" in stacks
        assert "go" in stacks
        assert "java" in stacks

    def test_go_context(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("go")
        assert profile.stack_name == "go"

    def test_java_context(self) -> None:
        adapter = StackAdapter()
        profile = adapter.get_context("java")
        assert profile.stack_name == "java"
