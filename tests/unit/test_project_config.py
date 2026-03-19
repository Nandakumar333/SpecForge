"""Unit tests for ProjectConfig validation."""

from pathlib import Path

from specforge.core.project import ProjectConfig


class TestProjectConfigValidation:
    def test_valid_simple_name(self) -> None:
        config = ProjectConfig.create(name="myapp", target_dir=Path("/tmp/myapp"))
        assert config.ok is True
        assert config.value.name == "myapp"

    def test_valid_name_with_hyphens(self) -> None:
        config = ProjectConfig.create(name="my-app", target_dir=Path("/tmp/my-app"))
        assert config.ok is True

    def test_valid_name_with_underscores(self) -> None:
        config = ProjectConfig.create(name="my_app", target_dir=Path("/tmp/my_app"))
        assert config.ok is True

    def test_valid_name_with_numbers(self) -> None:
        config = ProjectConfig.create(name="app123", target_dir=Path("/tmp/app123"))
        assert config.ok is True

    def test_invalid_name_with_spaces(self) -> None:
        config = ProjectConfig.create(name="my app", target_dir=Path("/tmp/my app"))
        assert config.ok is False
        assert "Invalid project name" in config.error

    def test_invalid_name_with_special_chars(self) -> None:
        config = ProjectConfig.create(name="my@app!", target_dir=Path("/tmp/bad"))
        assert config.ok is False

    def test_empty_name_rejected(self) -> None:
        config = ProjectConfig.create(name="", target_dir=Path("/tmp/empty"))
        assert config.ok is False

    def test_mutual_exclusion_name_and_here(self) -> None:
        """When here=True, name should be derived from directory, not provided."""
        config = ProjectConfig.create(
            name="myapp", target_dir=Path("/tmp/myapp"), here=True
        )
        assert config.ok is False
        assert "Cannot specify both" in config.error

    def test_here_mode_derives_name(self) -> None:
        config = ProjectConfig.create(
            name="", target_dir=Path("/tmp/myproject"), here=True
        )
        assert config.ok is True
        assert config.value.name == "myproject"
        assert config.value.here is True

    def test_default_values(self) -> None:
        config = ProjectConfig.create(name="test", target_dir=Path("/tmp/test"))
        assert config.ok is True
        val = config.value
        assert val.agent == "generic"
        assert val.stack == "agnostic"
        assert val.no_git is False
        assert val.force is False
        assert val.dry_run is False
        assert val.here is False
