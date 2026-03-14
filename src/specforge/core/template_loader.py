"""Jinja2 template loader using importlib.resources."""

from __future__ import annotations

from importlib.resources import files

from jinja2 import BaseLoader, Environment, TemplateNotFound


class _PackageLoader(BaseLoader):
    """Load templates from the specforge.templates package."""

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str | None, None]:
        parts = template.split("/")
        resource = files("specforge.templates")
        for part in parts:
            resource = resource.joinpath(part)
        try:
            source = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError) as exc:
            raise TemplateNotFound(template) from exc
        return source, template, None


_env = Environment(
    loader=_PackageLoader(),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template(template_name: str, **context: object) -> str:
    """Render a Jinja2 template from the specforge.templates package."""
    tmpl = _env.get_template(template_name)
    return tmpl.render(**context)
