"""Snapshot tests for Jinja2 template rendering."""

from pathlib import Path

from specforge.core.template_loader import render_template
from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer

_CTX = {
    "project_name": "myapp",
    "agent": "claude",
    "stack": "python",
    "date": "2026-03-14",
    "stack_hint": "Python",
}

_AGNOSTIC_CTX = {
    "project_name": "testproj",
    "agent": "agnostic",
    "stack": "agnostic",
    "date": "2026-03-14",
    "stack_hint": "Language-agnostic",
}

_FEATURE_CTX = {
    "project_name": "SpecForge",
    "feature_name": "test-feature",
    "date": "2026-01-01",
    "stack": "python",
    "stack_hint": "Python",
    "agent": "claude",
}


def _make_renderer() -> TemplateRenderer:
    """Create a renderer with discovered built-in templates."""
    registry = TemplateRegistry()
    registry.discover()
    return TemplateRenderer(registry)


class TestTemplateRendering:
    """Existing snapshot tests for Feature 001 templates (backward compat)."""

    def test_constitution_template(self, snapshot: object) -> None:
        rendered = render_template("constitution.md.j2", **_CTX)
        assert rendered == snapshot

    def test_constitution_agnostic_stack(self, snapshot: object) -> None:
        rendered = render_template("constitution.md.j2", **_AGNOSTIC_CTX)
        assert rendered == snapshot

    def test_gitignore_template(self, snapshot: object) -> None:
        rendered = render_template("gitignore.j2", project_name="myapp")
        assert rendered == snapshot

    def test_decisions_template(self, snapshot: object) -> None:
        rendered = render_template("decisions.md.j2", **_CTX)
        assert rendered == snapshot

    def test_app_analyzer_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/app-analyzer.md.j2", **_CTX)
        assert rendered == snapshot

    def test_feature_specifier_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/feature-specifier.md.j2", **_CTX)
        assert rendered == snapshot

    def test_implementation_planner_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/implementation-planner.md.j2", **_CTX)
        assert rendered == snapshot

    def test_task_decomposer_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/task-decomposer.md.j2", **_CTX)
        assert rendered == snapshot

    def test_code_reviewer_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/code-reviewer.md.j2", **_CTX)
        assert rendered == snapshot

    def test_test_writer_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/test-writer.md.j2", **_CTX)
        assert rendered == snapshot

    def test_debugger_prompt(self, snapshot: object) -> None:
        rendered = render_template("prompts/debugger.md.j2", **_CTX)
        assert rendered == snapshot

    def test_spec_template(self, snapshot: object) -> None:
        rendered = render_template("features/spec-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_plan_template(self, snapshot: object) -> None:
        rendered = render_template("features/plan-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_tasks_template(self, snapshot: object) -> None:
        rendered = render_template("features/tasks-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_research_template(self, snapshot: object) -> None:
        rendered = render_template("features/research-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_data_model_template(self, snapshot: object) -> None:
        rendered = render_template("features/data-model-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_quickstart_template(self, snapshot: object) -> None:
        rendered = render_template("features/quickstart-template.md.j2", **_CTX)
        assert rendered == snapshot

    def test_contracts_template(self, snapshot: object) -> None:
        rendered = render_template("features/contracts-template.md.j2", **_CTX)
        assert rendered == snapshot


class TestNewTemplateSnapshots:
    """Snapshot tests for Feature 002 templates via TemplateRenderer."""

    def test_base_constitution(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "constitution", TemplateType.constitution, _CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_backend_prompt(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "backend", TemplateType.prompt, _CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_frontend_prompt(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "frontend", TemplateType.prompt, _CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_testing_prompt(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "testing", TemplateType.prompt, _CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_spec(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "spec", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_research(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "research", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_datamodel(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "datamodel", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_plan(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "plan", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_checklist(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "checklist", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_edge_cases(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "edge-cases", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot

    def test_feature_tasks(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "tasks", TemplateType.feature, _FEATURE_CTX
        )
        assert result.ok
        assert result.value == snapshot


class TestStackVariantSnapshots:
    """Snapshot tests for stack-specific prompt variants (US3 — T026)."""

    def test_backend_dotnet(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "backend", TemplateType.prompt, _CTX, stack="dotnet"
        )
        assert result.ok
        assert result.value == snapshot

    def test_backend_nodejs(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "backend", TemplateType.prompt, _CTX, stack="nodejs"
        )
        assert result.ok
        assert result.value == snapshot

    def test_backend_python(self, snapshot: object) -> None:
        renderer = _make_renderer()
        result = renderer.render(
            "backend", TemplateType.prompt, _CTX, stack="python"
        )
        assert result.ok
        assert result.value == snapshot

    def test_variants_differ(self) -> None:
        """Stack variants must produce different content."""
        renderer = _make_renderer()
        dotnet = renderer.render(
            "backend", TemplateType.prompt, _CTX, stack="dotnet"
        )
        nodejs = renderer.render(
            "backend", TemplateType.prompt, _CTX, stack="nodejs"
        )
        generic = renderer.render(
            "backend", TemplateType.prompt, _CTX
        )
        assert dotnet.value != nodejs.value
        assert dotnet.value != generic.value
        assert nodejs.value != generic.value


class TestUserOverrideSnapshots:
    """Snapshot test for user override vs built-in (US2 — T021)."""

    def test_override_differs_from_built_in(
        self, tmp_path: Path, snapshot: object
    ) -> None:
        user_dir = tmp_path / ".specforge" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "constitution.md.j2").write_text(
            "# Custom {{ project_name }} Constitution\n\n"
            "This is a custom constitution for **{{ project_name }}**.\n",
            encoding="utf-8",
        )
        registry = TemplateRegistry(tmp_path)
        registry.discover()
        renderer = TemplateRenderer(registry)
        result = renderer.render(
            "constitution", TemplateType.constitution, _CTX
        )
        assert result.ok
        assert result.value == snapshot
        # Verify it differs from built-in
        builtin_reg = TemplateRegistry()
        builtin_reg.discover()
        builtin_renderer = TemplateRenderer(builtin_reg)
        builtin_result = builtin_renderer.render(
            "constitution", TemplateType.constitution, _CTX
        )
        assert result.value != builtin_result.value
