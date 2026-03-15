"""Data model entities for the template rendering engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TemplateType(Enum):
    """Classification of template purpose."""

    constitution = "constitution"
    prompt = "prompt"
    feature = "feature"
    partial = "partial"
    governance = "governance"


class TemplateSource(Enum):
    """Where a template was discovered from."""

    built_in = "built_in"
    user_override = "user_override"


@dataclass(frozen=True)
class TemplateInfo:
    """Metadata for a single discovered template."""

    logical_name: str
    template_type: TemplateType
    source: TemplateSource
    template_path: str
    stack: str | None = None
    is_base: bool = False

    @property
    def identity(self) -> tuple[str, TemplateType, str | None, TemplateSource]:
        """Unique identity tuple for catalog deduplication."""
        return (self.logical_name, self.template_type, self.stack, self.source)


@dataclass(frozen=True)
class TemplateVarSchema:
    """Variable contract for a template type."""

    required: dict[str, type] = field(default_factory=dict)
    optional: dict[str, tuple[type, Any]] = field(default_factory=dict)

    def validate(self, context: dict[str, Any]) -> list[str]:
        """Return list of validation errors for a context dict."""
        errors: list[str] = []
        for name, expected_type in self.required.items():
            if name not in context:
                errors.append(f"Missing required variable: '{name}'")
            elif not isinstance(context[name], expected_type):
                actual = type(context[name]).__name__
                errors.append(
                    f"Type mismatch for '{name}': "
                    f"expected {expected_type.__name__}, got {actual}"
                )
        for name, (expected_type, _default) in self.optional.items():
            if name in context and not isinstance(context[name], expected_type):
                actual = type(context[name]).__name__
                errors.append(
                    f"Type mismatch for '{name}': "
                    f"expected {expected_type.__name__}, got {actual}"
                )
        return errors


@dataclass(frozen=True)
class ValidationIssue:
    """A single problem found during output validation."""

    line: int
    issue_type: str
    message: str
    placeholder_name: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    """Complete validation result for a rendered template."""

    template_name: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no issues were found."""
        return len(self.issues) == 0


@dataclass(frozen=True)
class StackProfile:
    """Stack-specific context variables for template rendering."""

    stack_name: str
    stack_hint: str
    conventions: str
    patterns: str
    testing_hint: str
