"""Unit tests for agent detection from PATH."""

from unittest.mock import patch

from specforge.core.agent_detector import detect_agent


class TestDetectAgent:
    def test_single_agent_detected(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/usr/bin/claude" if name == "claude" else None

        with patch("specforge.core.agent_detector.shutil.which", fake_which):
            result = detect_agent()
        assert result.agent == "claude"
        assert result.source == "auto-detected"
        assert result.executable == "claude"

    def test_no_agents_returns_agnostic(self) -> None:
        with patch("specforge.core.agent_detector.shutil.which", return_value=None):
            result = detect_agent()
        assert result.agent == "agnostic"
        assert result.source == "agnostic"
        assert result.executable is None

    def test_multiple_agents_returns_first_in_priority(self) -> None:
        available = {"copilot", "cursor"}

        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name in available else None

        with patch("specforge.core.agent_detector.shutil.which", fake_which):
            result = detect_agent()
        assert result.agent == "copilot"
        assert result.source == "auto-detected"

    def test_explicit_override_skips_detection(self) -> None:
        with patch("specforge.core.agent_detector.shutil.which") as mock_which:
            result = detect_agent(explicit="gemini")
        mock_which.assert_not_called()
        assert result.agent == "gemini"
        assert result.source == "explicit"

    def test_windsurf_detected_when_only_available(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/usr/bin/windsurf" if name == "windsurf" else None

        with patch("specforge.core.agent_detector.shutil.which", fake_which):
            result = detect_agent()
        assert result.agent == "windsurf"
        assert result.source == "auto-detected"
