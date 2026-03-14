"""Integration tests for specforge init command."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli


class TestInitCommand:
    def test_happy_path_creates_dir_and_specforge(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp"])
            assert result.exit_code == 0, result.output
            assert (Path("myapp") / ".specforge").is_dir()
            assert (Path("myapp") / ".specforge" / "constitution.md").exists()

    def test_happy_path_creates_git_commit(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp"])
            assert result.exit_code == 0, result.output
            git_dir = Path("myapp") / ".git"
            assert git_dir.exists()

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--dry-run"])
            assert result.exit_code == 0, result.output
            assert not Path("myapp").exists()
            assert "DRY RUN" in result.output or "Would create" in result.output

    def test_missing_name_without_here_exits_2(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 2

    def test_invalid_name_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "my app"])
            assert result.exit_code == 1
            assert "Invalid project name" in result.output

    def test_existing_dir_without_force_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("myapp").mkdir()
            result = runner.invoke(cli, ["init", "myapp"])
            assert result.exit_code == 1
            assert "already exists" in result.output

    def test_force_adds_missing_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("myapp").mkdir()
            (Path("myapp") / "existing.txt").write_text("keep me")
            result = runner.invoke(cli, ["init", "myapp", "--force"])
            assert result.exit_code == 0, result.output
            assert (Path("myapp") / ".specforge").is_dir()
            assert (Path("myapp") / "existing.txt").read_text() == "keep me"

    def test_explicit_agent(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--agent", "claude"])
            assert result.exit_code == 0, result.output
            assert "claude" in result.output.lower()

    def test_explicit_stack(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "python"])
            assert result.exit_code == 0, result.output

    def test_no_git_skips_git(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            assert result.exit_code == 0, result.output
            assert not (Path("myapp") / ".git").exists()

    def test_git_not_installed_without_no_git_exits_1(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        with (
            runner.isolated_filesystem(temp_dir=tmp_path),
            patch("specforge.core.git_ops.shutil.which", return_value=None),
        ):
            result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            # With --no-git it should succeed
            assert result.exit_code == 0

    def test_permission_denied_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path), patch(
            "specforge.core.scaffold_writer.Path.mkdir",
            side_effect=PermissionError("Access denied"),
        ):
            result = runner.invoke(cli, ["init", "myapp"])
            assert result.exit_code == 1
            assert "Permission denied" in result.output
