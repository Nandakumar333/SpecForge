"""Unit tests for scaffold file writer."""

from pathlib import Path

from specforge.core.project import ProjectConfig, ScaffoldFile, ScaffoldPlan
from specforge.core.scaffold_writer import write_scaffold


def _make_plan(
    tmp_path: Path,
    force: bool = False,
    dry_run: bool = False,
) -> ScaffoldPlan:
    config_result = ProjectConfig.create(
        name="testproj",
        target_dir=tmp_path,
        force=force,
        dry_run=dry_run,
    )
    assert config_result.ok
    config = config_result.value
    return ScaffoldPlan(
        config=config,
        directories=[Path(".specforge"), Path(".specforge/memory")],
        files=[
            ScaffoldFile(
                relative_path=Path(".specforge/constitution.md"),
                template_name="constitution.md.j2",
                context={
                    "project_name": "testproj",
                    "agent": "agnostic",
                    "stack": "agnostic",
                    "date": "2026-03-14",
                    "stack_hint": "Language-agnostic",
                },
            ),
        ],
    )


class TestWriteScaffold:
    def test_files_written_to_correct_paths(self, tmp_path: Path) -> None:
        plan = _make_plan(tmp_path)
        result = write_scaffold(plan)
        assert result.ok is True
        written = result.value.written
        expected = tmp_path / ".specforge" / "constitution.md"
        assert expected in written
        assert expected.exists()

    def test_directories_created(self, tmp_path: Path) -> None:
        plan = _make_plan(tmp_path)
        write_scaffold(plan)
        assert (tmp_path / ".specforge").is_dir()
        assert (tmp_path / ".specforge" / "memory").is_dir()

    def test_existing_file_skipped_with_force(self, tmp_path: Path) -> None:
        plan = _make_plan(tmp_path, force=True)
        (tmp_path / ".specforge").mkdir(parents=True)
        existing = tmp_path / ".specforge" / "constitution.md"
        existing.write_text("existing content")
        result = write_scaffold(plan)
        assert result.ok is True
        assert existing in result.value.skipped
        assert existing.read_text() == "existing content"

    def test_no_writes_on_dry_run(self, tmp_path: Path) -> None:
        plan = _make_plan(tmp_path, dry_run=True)
        result = write_scaffold(plan)
        assert result.ok is True
        assert len(result.value.written) == 0
        assert not (tmp_path / ".specforge").exists()
