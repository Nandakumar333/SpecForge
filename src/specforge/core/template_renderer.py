"""Template renderer — Jinja2 environment with custom filters."""

from __future__ import annotations

import re
from typing import Any

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    TemplateNotFound,
)

from specforge.core.config import (
    get_constitution_vars,
    get_feature_vars,
    get_prompt_vars,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import TemplateType, TemplateVarSchema
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_validator import validate_context


class _PackageLoader(BaseLoader):
    """Load templates from the specforge.templates package."""

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str | None, None]:
        from importlib.resources import files

        parts = template.split("/")
        resource = files("specforge.templates")
        for part in parts:
            resource = resource.joinpath(part)
        try:
            source = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError) as exc:
            raise TemplateNotFound(template) from exc
        return source, template, None


# ── Custom Jinja2 Filters ───────────────────────────────────────────

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _snake_case(value: str) -> str:
    """Convert CamelCase or spaced text to snake_case."""
    if not value:
        return ""
    result = _CAMEL_RE.sub("_", value)
    result = re.sub(r"[\s\-]+", "_", result)
    return result.lower()


def _uppercase(value: str) -> str:
    """Convert text to UPPERCASE."""
    return value.upper()


def _pluralize(value: str) -> str:
    """Naive English pluralization."""
    if not value:
        return ""
    if value.endswith("sis"):
        return value[:-3] + "ses"
    if value.endswith("y") and value[-2:] not in ("ay", "ey", "oy", "uy"):
        return value[:-1] + "ies"
    if value.endswith(("s", "x", "z", "ch", "sh")):
        return value + "es"
    return value + "s"


def _kebab_case(value: str) -> str:
    """Convert CamelCase or spaced text to kebab-case."""
    if not value:
        return ""
    result = _CAMEL_RE.sub("-", value)
    result = re.sub(r"[\s_]+", "-", result)
    return result.lower()


# ── Schema lookup ────────────────────────────────────────────────────

_SCHEMA_MAP: dict[TemplateType, Any] = {
    TemplateType.constitution: get_constitution_vars,
    TemplateType.prompt: get_prompt_vars,
    TemplateType.feature: get_feature_vars,
}


def _get_schema(template_type: TemplateType) -> TemplateVarSchema | None:
    """Get the variable schema for a template type."""
    factory = _SCHEMA_MAP.get(template_type)
    return factory() if factory else None


# ── Renderer ─────────────────────────────────────────────────────────


class TemplateRenderer:
    """Wraps Jinja2 Environment with registry resolution and filters."""

    def __init__(self, registry: TemplateRegistry) -> None:
        self._registry = registry
        self._env = self._create_environment()

    def render(
        self,
        template_name: str,
        template_type: TemplateType,
        context: dict[str, Any],
        stack: str = "agnostic",
    ) -> Result:
        """Full pipeline: validate → resolve → render → inject header."""
        schema = _get_schema(template_type)
        if schema is not None:
            ctx_result = validate_context(context, schema)
            if not ctx_result.ok:
                return Err(
                    f"Context validation failed for '{template_name}': "
                    + "; ".join(ctx_result.error)
                )
            context = ctx_result.value

        resolve_result = self._registry.get(template_name, template_type, stack)
        if not resolve_result.ok:
            return Err(resolve_result.error)

        template_path = resolve_result.value.template_path
        return self._render_path(template_path, context)

    def render_raw(
        self,
        template_path: str,
        context: dict[str, Any],
    ) -> Result:
        """Low-level: render a specific path without registry resolution."""
        return self._render_path(template_path, context)

    def _render_path(
        self,
        template_path: str,
        context: dict[str, Any],
    ) -> Result:
        """Render a template by its loader path."""
        try:
            tmpl = self._env.get_template(template_path)
            rendered = tmpl.render(**context)
            return Ok(rendered)
        except TemplateNotFound:
            return Err(
                f"Template file not found: '{template_path}'. "
                "Check that the template exists in templates/base/ "
                "or .specforge/templates/."
            )
        except Exception as exc:
            return Err(f"Render error for '{template_path}': {exc}")

    def _create_environment(self) -> Environment:
        """Build a Jinja2 Environment with custom loaders and filters."""
        loaders: list[BaseLoader] = []
        if self._registry._project_root is not None:
            user_dir = self._registry._project_root / ".specforge" / "templates"
            if user_dir.is_dir():
                loaders.append(FileSystemLoader(str(user_dir)))
        loaders.append(_PackageLoader())

        env = Environment(
            loader=ChoiceLoader(loaders),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["snake_case"] = _snake_case
        env.filters["uppercase"] = _uppercase
        env.filters["pluralize"] = _pluralize
        env.filters["kebab_case"] = _kebab_case
        return env
