"""Base classes and data models for the stack plugin system."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from specforge.core.config import PLUGIN_SEVERITIES

# ── Rule ID validation pattern ───────────────────────────────────────

_RULE_ID_RE = re.compile(r"^[A-Z]+-[A-Z0-9-]+$")


# ── Data Models ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class PluginRule:
    """A single governance rule contributed by a stack plugin."""

    rule_id: str
    title: str
    severity: str
    scope: str
    description: str
    thresholds: dict[str, str]
    example_correct: str
    example_incorrect: str

    def __post_init__(self) -> None:
        _validate_plugin_rule(self)


@dataclass(frozen=True)
class DockerConfig:
    """Docker build configuration for a stack plugin."""

    base_image: str
    build_stages: tuple[str, ...]
    exposed_ports: tuple[int, ...]
    health_check_path: str = "/health"


# ── Validation helper ────────────────────────────────────────────────


def _validate_plugin_rule(rule: PluginRule) -> None:
    """Validate PluginRule fields; raise ValueError on problems."""
    if not rule.rule_id or not _RULE_ID_RE.match(rule.rule_id):
        msg = (
            f"rule_id must match pattern [A-Z]+-[A-Z0-9-]+, "
            f"got {rule.rule_id!r}"
        )
        raise ValueError(msg)
    if rule.severity not in PLUGIN_SEVERITIES:
        msg = (
            f"severity must be one of {sorted(PLUGIN_SEVERITIES)}, "
            f"got {rule.severity!r}"
        )
        raise ValueError(msg)
    for field_name in ("title", "scope", "description"):
        value = getattr(rule, field_name)
        if not value or not value.strip():
            msg = f"{field_name} must be a non-empty string"
            raise ValueError(msg)


# ── StackPlugin ABC ──────────────────────────────────────────────────


class StackPlugin(ABC):
    """Abstract base class for stack-specific plugins."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique plugin identifier (e.g., 'dotnet')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the stack plugin."""

    @property
    @abstractmethod
    def supported_architectures(self) -> list[str]:
        """Architecture types this plugin supports."""

    @abstractmethod
    def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
        """Return governance rules keyed by domain."""

    @abstractmethod
    def get_build_commands(self, arch: str) -> list[str]:
        """Return build commands for the given architecture."""

    @abstractmethod
    def get_docker_config(self, arch: str) -> DockerConfig | None:
        """Return Docker configuration, or None if not applicable."""

    @abstractmethod
    def get_test_commands(self) -> list[str]:
        """Return test execution commands."""

    @abstractmethod
    def get_folder_structure(self, arch: str) -> dict[str, str]:
        """Return folder-to-description mapping for the architecture."""
