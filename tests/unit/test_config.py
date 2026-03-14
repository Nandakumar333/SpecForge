"""Unit tests for config constants and type literals."""

from specforge.core.config import (
    AGENT_EXECUTABLES,
    AGENT_PRIORITY,
    PREREQUISITES,
    SUPPORTED_STACKS,
)


class TestAgentPriority:
    def test_priority_order(self) -> None:
        expected = ["claude", "copilot", "gemini", "cursor", "windsurf", "codex"]
        assert AGENT_PRIORITY == expected

    def test_priority_has_six_agents(self) -> None:
        assert len(AGENT_PRIORITY) == 6

    def test_all_agents_have_executables(self) -> None:
        for agent in AGENT_PRIORITY:
            assert agent in AGENT_EXECUTABLES


class TestSupportedStacks:
    def test_stacks_membership(self) -> None:
        expected = {"dotnet", "nodejs", "python", "go", "java"}
        assert set(SUPPORTED_STACKS) == expected


class TestAgentExecutables:
    def test_keys_match_priority(self) -> None:
        assert set(AGENT_EXECUTABLES.keys()) == set(AGENT_PRIORITY)

    def test_each_entry_is_nonempty_list(self) -> None:
        for agent, execs in AGENT_EXECUTABLES.items():
            assert isinstance(execs, list), f"{agent} executables is not a list"
            assert len(execs) > 0, f"{agent} has no executables"

    def test_copilot_executable(self) -> None:
        assert AGENT_EXECUTABLES["copilot"] == ["copilot"]

    def test_claude_executable(self) -> None:
        assert AGENT_EXECUTABLES["claude"] == ["claude"]


class TestPrerequisites:
    def test_prerequisites_contains_git(self) -> None:
        assert "git" in PREREQUISITES

    def test_prerequisites_contains_python(self) -> None:
        assert "python" in PREREQUISITES

    def test_prerequisites_contains_uv(self) -> None:
        assert "uv" in PREREQUISITES
