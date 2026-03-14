"""Snapshot tests for Jinja2 template rendering."""

from specforge.core.template_loader import render_template


class TestTemplateRendering:
    def test_constitution_template(self, snapshot: object) -> None:
        rendered = render_template(
            "constitution.md.j2",
            project_name="myapp",
            agent="claude",
            stack="python",
            date="2026-03-14",
            stack_hint="Python",
        )
        assert rendered == snapshot

    def test_constitution_agnostic_stack(self, snapshot: object) -> None:
        rendered = render_template(
            "constitution.md.j2",
            project_name="testproj",
            agent="agnostic",
            stack="agnostic",
            date="2026-03-14",
            stack_hint="Language-agnostic",
        )
        assert rendered == snapshot

    def test_gitignore_template(self, snapshot: object) -> None:
        rendered = render_template(
            "gitignore.j2",
            project_name="myapp",
        )
        assert rendered == snapshot
