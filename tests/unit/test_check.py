"""Unit tests for prerequisite checker."""

from unittest.mock import MagicMock, patch

from specforge.core.checker import check_prerequisites


class TestCheckPrerequisites:
    def test_all_present(self) -> None:
        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}"

        with (
            patch("specforge.core.checker.shutil.which", fake_which),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            results = check_prerequisites()
        assert all(r.found for r in results)

    def test_one_missing(self) -> None:
        def fake_which(name: str) -> str | None:
            return None if name == "uv" else f"/usr/bin/{name}"

        with (
            patch("specforge.core.checker.shutil.which", fake_which),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            results = check_prerequisites()
        uv_result = next(r for r in results if r.tool == "uv")
        assert uv_result.found is False
        assert uv_result.install_hint != ""

    def test_agent_added_when_specified(self) -> None:
        with (
            patch("specforge.core.checker.shutil.which", return_value="/usr/bin/x"),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            results = check_prerequisites(agent="claude")
        tool_names = [r.tool for r in results]
        assert "claude" in tool_names

    def test_without_agent_no_agent_in_list(self) -> None:
        with (
            patch("specforge.core.checker.shutil.which", return_value="/usr/bin/x"),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            results = check_prerequisites()
        tool_names = [r.tool for r in results]
        assert "claude" not in tool_names

    def test_version_detection_returns_string(self) -> None:
        with (
            patch("specforge.core.checker.shutil.which", return_value="/usr/bin/git"),
            patch("specforge.core.checker._get_version", return_value="2.43.0"),
        ):
            results = check_prerequisites()
        git_result = next(r for r in results if r.tool == "git")
        assert git_result.version == "2.43.0"
