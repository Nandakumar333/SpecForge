"""Snapshot tests for Jinja2 template rendering."""

from specforge.core.template_loader import render_template

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


class TestTemplateRendering:
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
