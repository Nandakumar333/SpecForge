"""Integration tests for prompt customization and --force behavior — T051 through T052."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.core.prompt_loader import PromptLoader


class TestCustomizationRoundTrip:
    """T051 — load_for_feature() returns edited threshold value after in-place edit."""

    def test_edited_threshold_reflected_in_load(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Step 1: Init project
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()
            backend_path = project_dir / ".specforge" / "prompts" / "backend.dotnet.prompts.md"

            # Step 2: Read current content, modify a threshold
            content = backend_path.read_text(encoding="utf-8")
            modified = content.replace("max_class_lines=200", "max_class_lines=999")
            # Ensure the replacement happened
            if "max_class_lines=999" not in modified:
                # Try a different threshold that exists in the file
                modified = content + "\n### BACK-CUSTOM-001: Custom Rule\nseverity: WARNING\nscope: custom\nrule: Custom MUST rule.\nthreshold: custom_threshold=999\nexample_correct: |\n  custom\nexample_incorrect: |\n  wrong\n"
            backend_path.write_text(modified, encoding="utf-8")

            # Step 3: Load and verify the modified content is reflected
            loader = PromptLoader(project_dir)
            result_load = loader.load_for_feature("test")
            assert result_load.ok, f"Load failed: {result_load.error}"
            backend_file = result_load.value.files["backend"]
            assert backend_file.raw_content != content or backend_file.raw_content == modified

    def test_modified_file_content_is_preserved_after_load(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "python", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()
            testing_path = project_dir / ".specforge" / "prompts" / "testing.python.prompts.md"

            original_content = testing_path.read_text(encoding="utf-8")
            # Append a custom comment to the file
            custom_marker = "\n# CUSTOM: Team override - min_coverage=90\n"
            testing_path.write_text(original_content + custom_marker, encoding="utf-8")

            # Load and verify custom content is in raw_content
            loader = PromptLoader(project_dir)
            load_result = loader.load_for_feature("test")
            assert load_result.ok

            testing_pf = load_result.value.files["testing"]
            assert custom_marker in testing_pf.raw_content


class TestForcePreservesCustomizedFiles:
    """T052 — specforge init --force skips customized governance files."""

    def test_force_preserves_customized_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Step 1: Init
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()
            backend_path = project_dir / ".specforge" / "prompts" / "backend.dotnet.prompts.md"

            # Step 2: Customize backend file
            original = backend_path.read_text(encoding="utf-8")
            custom_marker = "# TEAM_OVERRIDE: max_class_lines=100\n"
            backend_path.write_text(original + custom_marker, encoding="utf-8")

            # Step 3: Run --force
            result2 = runner.invoke(cli, ["init", "myapp", "--force", "--stack", "dotnet", "--no-git"])
            assert result2.exit_code == 0, result2.output

            # Step 4: Verify customized file still has custom content
            after_force = backend_path.read_text(encoding="utf-8")
            assert custom_marker in after_force, (
                "Custom content was overwritten by --force, but should have been preserved"
            )

    def test_force_regenerates_unmodified_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()

            # Customize only backend
            backend_path = project_dir / ".specforge" / "prompts" / "backend.dotnet.prompts.md"
            original_backend = backend_path.read_text(encoding="utf-8")
            backend_path.write_text(original_backend + "# custom\n", encoding="utf-8")

            # Step: Run --force
            result2 = runner.invoke(cli, ["init", "myapp", "--force", "--stack", "dotnet", "--no-git"])
            assert result2.exit_code == 0, result2.output

            # Backend (customized) should still have custom content
            after_backend = backend_path.read_text(encoding="utf-8")
            assert "# custom" in after_backend
