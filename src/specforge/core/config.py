"""Constants, type literals, and configuration for SpecForge core."""

from __future__ import annotations

from typing import Literal

AgentName = Literal[
    "claude", "copilot", "gemini", "cursor", "windsurf", "codex", "agnostic"
]

StackName = Literal[
    "dotnet", "nodejs", "python", "go", "java", "agnostic"
]

AGENT_PRIORITY: list[str] = [
    "claude", "copilot", "gemini", "cursor", "windsurf", "codex",
]

SUPPORTED_STACKS: list[str] = [
    "dotnet", "nodejs", "python", "go", "java",
]

AGENT_EXECUTABLES: dict[str, list[str]] = {
    "claude": ["claude"],
    "copilot": ["copilot"],
    "gemini": ["gemini"],
    "cursor": ["cursor"],
    "windsurf": ["windsurf"],
    "codex": ["codex"],
}

PREREQUISITES: list[str] = ["git", "python", "uv"]

# Scaffold directory structure (relative to .specforge/)
SCAFFOLD_DIRS: list[str] = [
    ".specforge",
    ".specforge/memory",
    ".specforge/features",
    ".specforge/prompts",
    ".specforge/scripts",
    ".specforge/templates/features",
]

# Valid project name pattern
PROJECT_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"

# Default git commit message for scaffold
INIT_COMMIT_MESSAGE = "chore: init specforge scaffold"

# Stack hints for template rendering
STACK_HINTS: dict[str, str] = {
    "dotnet": "C#/.NET",
    "nodejs": "Node.js/TypeScript",
    "python": "Python",
    "go": "Go",
    "java": "Java",
    "agnostic": "Language-agnostic",
}

# Install hints for prerequisites
INSTALL_HINTS: dict[str, str] = {
    "git": "https://git-scm.com/downloads",
    "python": "https://python.org/downloads",
    "uv": "https://docs.astral.sh/uv/getting-started/installation/",
    "claude": "https://claude.ai/download",
    "copilot": "https://github.com/features/copilot",
    "gemini": "https://ai.google.dev/gemini-api/docs/downloads",
    "cursor": "https://cursor.com",
    "windsurf": "https://windsurf.com",
    "codex": "https://github.com/openai/codex",
}
