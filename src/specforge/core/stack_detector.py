"""StackDetector — identifies project stack from marker files."""

from __future__ import annotations

from pathlib import Path

from specforge.core.config import SUPPORTED_STACKS

# Mapping from marker filename pattern to stack name.
# For glob patterns, keys starting with "*" are treated as glob; others as exact match.
_STACK_MARKERS: list[tuple[str, str]] = [
    ("*.csproj", "dotnet"),
    ("package.json", "nodejs"),
    ("pyproject.toml", "python"),
    ("go.mod", "go"),
    ("pom.xml", "java"),
]


class StackDetector:
    """Detects the technology stack of a project by scanning root-level marker files."""

    @staticmethod
    def detect(project_root: Path) -> str:
        """Scan project_root for stack marker files and return the detected stack.

        Resolution order follows SUPPORTED_STACKS to ensure deterministic results
        when multiple markers are present. Returns "agnostic" if no marker is found.
        """
        if not project_root.is_dir():
            return "agnostic"

        found: dict[str, bool] = {}
        for pattern, stack in _STACK_MARKERS:
            if pattern.startswith("*"):
                matches = list(project_root.glob(pattern))
                found[stack] = len(matches) > 0
            else:
                found[stack] = (project_root / pattern).exists()

        for stack in SUPPORTED_STACKS:
            if found.get(stack, False):
                return stack

        return "agnostic"
