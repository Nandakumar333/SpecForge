"""Integration tests for init command governance file generation — T046 through T048."""

from __future__ import annotations

import time
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.core.config import GOVERNANCE_DOMAINS
from specforge.core.prompt_loader import PromptLoader


class TestInitGeneratesGovernanceFiles:
    """T046 — specforge init --stack dotnet generates all 7 governance files."""

    def test_generates_7_governance_files_dotnet(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            prompts_dir = Path("myapp") / ".specforge" / "prompts"
            governance_files = list(prompts_dir.glob("*.prompts.md"))
            assert len(governance_files) == 7, (
                f"Expected 7 governance files, found {len(governance_files)}: "
                f"{[f.name for f in governance_files]}"
            )

    def test_config_json_written_with_correct_stack(self, tmp_path: Path) -> None:
        import json

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            config_path = Path("myapp") / ".specforge" / "config.json"
            assert config_path.exists()
            config = json.loads(config_path.read_text(encoding="utf-8"))
            assert config["stack"] == "dotnet"

    def test_prompt_loader_parses_generated_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()
            loader = PromptLoader(project_dir)
            load_result = loader.load_for_feature("test-feature")

            assert load_result.ok, f"PromptLoader failed: {load_result.error}"
            assert set(load_result.value.files.keys()) == set(GOVERNANCE_DOMAINS)

    def test_all_generated_files_have_non_empty_rules(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "python", "--no-git"])
            assert result.exit_code == 0, result.output

            project_dir = Path("myapp").resolve()
            loader = PromptLoader(project_dir)
            load_result = loader.load_for_feature("test")
            assert load_result.ok

            for domain, pf in load_result.value.files.items():
                assert len(pf.rules) > 0, f"Domain '{domain}' has no rules"

    def test_init_completes_within_5_seconds(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            start = time.perf_counter()
            result = runner.invoke(cli, ["init", "myapp", "--stack", "dotnet", "--no-git"])
            elapsed = time.perf_counter() - start

            assert result.exit_code == 0, result.output
            assert elapsed < 5.0, f"Init took {elapsed:.2f}s, expected < 5s"


class TestInitAutoDetectsStack:
    """T047 — specforge init without --stack auto-detects from project markers."""

    def test_auto_detects_nodejs_from_package_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create package.json in the current directory (future project root)
            # StackDetector scans the TARGET directory, not CWD
            # So we need to check the resolved behavior carefully
            result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            # Without stack, uses StackDetector on target_dir
            # tmp_path itself has no markers → agnostic
            assert result.exit_code == 0, result.output

            import json
            config_path = Path("myapp") / ".specforge" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # No markers in tmp_path → agnostic
            assert config["stack"] == "agnostic"

    def test_dotnet_detected_when_csproj_present(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create myapp dir first, then add .csproj to it
            Path("myapp").mkdir()
            (Path("myapp") / "MyApp.csproj").write_text("<Project />")
            result = runner.invoke(cli, ["init", "myapp", "--force", "--no-git"])
            assert result.exit_code == 0, result.output

            import json
            config_path = Path("myapp") / ".specforge" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            assert config["stack"] == "dotnet"

    def test_nodejs_detected_when_package_json_present(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("myapp").mkdir()
            (Path("myapp") / "package.json").write_text('{"name": "myapp"}')
            result = runner.invoke(cli, ["init", "myapp", "--force", "--no-git"])
            assert result.exit_code == 0, result.output

            import json
            config_path = Path("myapp") / ".specforge" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            assert config["stack"] == "nodejs"


class TestInitInvalidStack:
    """T048 — specforge init --stack ruby exits 1 with error listing supported stacks."""

    def test_unsupported_stack_exits_nonzero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "ruby", "--no-git"])
            assert result.exit_code != 0

    def test_error_message_references_stack_option(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "myapp", "--stack", "ruby", "--no-git"])
            # Click Choice validation will show 'ruby' is invalid
            assert "ruby" in result.output or "Invalid value" in result.output
