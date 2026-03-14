"""Unit tests for scaffold plan builder."""

from pathlib import Path

from specforge.core.project import ProjectConfig, ScaffoldPlan
from specforge.core.scaffold_builder import build_scaffold_plan


class TestBuildScaffoldPlan:
    def _make_config(self, **overrides: object) -> ProjectConfig:
        defaults = {
            "name": "testproj",
            "target_dir": Path("/tmp/testproj"),
            "agent": "claude",
            "stack": "python",
        }
        defaults.update(overrides)
        result = ProjectConfig.create(**defaults)
        assert result.ok
        return result.value

    def test_returns_ok_result(self) -> None:
        config = self._make_config()
        result = build_scaffold_plan(config)
        assert result.ok is True

    def test_plan_has_expected_directories(self) -> None:
        config = self._make_config()
        plan = build_scaffold_plan(config).value
        dir_strs = [str(d) for d in plan.directories]
        assert ".specforge" in dir_strs
        assert str(Path(".specforge/memory")) in dir_strs
        assert str(Path(".specforge/prompts")) in dir_strs
        assert str(Path(".specforge/features")) in dir_strs
        assert str(Path(".specforge/scripts")) in dir_strs

    def test_plan_has_constitution_file(self) -> None:
        config = self._make_config()
        plan = build_scaffold_plan(config).value
        paths = [str(f.relative_path) for f in plan.files]
        assert str(Path(".specforge/constitution.md")) in paths

    def test_plan_has_prompt_files(self) -> None:
        config = self._make_config()
        plan = build_scaffold_plan(config).value
        prompt_files = [
            f for f in plan.files
            if str(f.relative_path).startswith(str(Path(".specforge/prompts")))
        ]
        assert len(prompt_files) == 7

    def test_plan_has_feature_templates(self) -> None:
        config = self._make_config()
        plan = build_scaffold_plan(config).value
        feature_files = [
            f for f in plan.files
            if str(f.relative_path).startswith(
                str(Path(".specforge/templates/features"))
            )
        ]
        assert len(feature_files) == 7

    def test_file_ordering_is_deterministic(self) -> None:
        config = self._make_config()
        plan1 = build_scaffold_plan(config).value
        plan2 = build_scaffold_plan(config).value
        paths1 = [str(f.relative_path) for f in plan1.files]
        paths2 = [str(f.relative_path) for f in plan2.files]
        assert paths1 == paths2

    def test_context_includes_project_name(self) -> None:
        config = self._make_config(name="myapp")
        plan = build_scaffold_plan(config).value
        for f in plan.files:
            assert "project_name" in f.context
            assert f.context["project_name"] == "myapp"
