"""Jinja2 template loader using importlib.resources.

Deprecated: Use template_renderer.py. Will be removed in Feature 003.
This module is preserved as a backward-compatible wrapper for existing callers.
"""

from __future__ import annotations

from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer

_renderer: TemplateRenderer | None = None


def _get_renderer() -> TemplateRenderer:
    """Lazy-init a module-level renderer."""
    global _renderer
    if _renderer is None:
        registry = TemplateRegistry()
        registry.discover()
        _renderer = TemplateRenderer(registry)
    return _renderer


def render_template(template_name: str, **context: object) -> str:
    """Render a Jinja2 template from the specforge.templates package.

    Deprecated: Use TemplateRenderer.render() or render_raw() instead.
    """
    renderer = _get_renderer()
    result = renderer.render_raw(template_name, dict(context))
    if result.ok:
        return result.value
    # Fallback: try with base/ prefix for old-style callers
    result = renderer.render_raw(f"base/{template_name}", dict(context))
    if result.ok:
        return result.value
    msg = f"Template not found: {template_name}"
    raise FileNotFoundError(msg)
