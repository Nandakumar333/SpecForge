"""Integration tests for specforge init --here workflow."""

from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


class TestInitHereCommand:
    def test_here_in_empty_dir_creates_specforge(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli, ["init", "--here"])
            assert result.exit_code == 0, result.output
            assert (Path(td) / ".specforge").is_dir()
            assert (Path(td) / ".specforge" / "constitution.md").exists()

    def test_here_preserves_existing_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            existing = Path(td) / "myfile.txt"
            existing.write_text("important data")
            result = runner.invoke(cli, ["init", "--here"])
            assert result.exit_code == 0, result.output
            assert existing.read_text() == "important data"

    def test_here_existing_specforge_without_force_exits_1(
        self,
        tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            (Path(td) / ".specforge").mkdir()
            result = runner.invoke(cli, ["init", "--here"])
            assert result.exit_code == 1
            assert "already exists" in result.output

    def test_here_force_adds_missing_preserves_existing(
        self,
        tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            specforge_dir = Path(td) / ".specforge"
            specforge_dir.mkdir()
            existing = specforge_dir / "constitution.md"
            existing.write_text("custom constitution")
            result = runner.invoke(cli, ["init", "--here", "--force"])
            assert result.exit_code == 0, result.output
            # Existing file preserved
            assert existing.read_text() == "custom constitution"
            # Missing files were added
            assert (specforge_dir / "memory").is_dir()
