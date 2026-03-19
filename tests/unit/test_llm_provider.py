"""Unit tests for LLMProvider protocol, SubprocessProvider, and ProviderFactory."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from specforge.core.llm_provider import (
    LLMProvider,
    ProviderFactory,
    SubprocessProvider,
)
from specforge.core.result import Err, Ok


# ── SubprocessProvider.call() ────────────────────────────────────────


class TestSubprocessProviderCall:
    def test_call_returns_ok_on_successful_stdout(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=0,
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "# Generated Spec\nContent here"
        mock_proc.stderr = ""

        with patch("specforge.core.llm_provider.subprocess.run", return_value=mock_proc):
            result = provider.call("system instructions", "user prompt")

        assert result.ok is True
        assert "Generated Spec" in result.value

    def test_call_returns_err_on_timeout(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            timeout=5,
            max_retries=0,
        )
        with patch(
            "specforge.core.llm_provider.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=5),
        ):
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "timed out" in result.error

    def test_call_returns_err_on_nonzero_exit(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=0,
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "authentication failed"
        mock_proc.stdout = ""

        with patch("specforge.core.llm_provider.subprocess.run", return_value=mock_proc):
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "authentication failed" in result.error

    def test_call_returns_err_on_empty_output(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=0,
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        with patch("specforge.core.llm_provider.subprocess.run", return_value=mock_proc):
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "empty output" in result.error

    def test_call_returns_err_on_os_error(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=0,
        )
        with patch(
            "specforge.core.llm_provider.subprocess.run",
            side_effect=OSError("No such file or directory"),
        ):
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "Failed to invoke" in result.error


# ── SubprocessProvider._classify_error() ─────────────────────────────


class TestClassifyError:
    def test_rate_limit_is_transient(self) -> None:
        assert SubprocessProvider._classify_error("rate limit exceeded") == "transient"

    def test_429_is_transient(self) -> None:
        assert SubprocessProvider._classify_error("HTTP 429 Too Many Requests") == "transient"

    def test_connection_error_is_transient(self) -> None:
        assert SubprocessProvider._classify_error("connection refused") == "transient"

    def test_overloaded_is_transient(self) -> None:
        assert SubprocessProvider._classify_error("server overloaded") == "transient"

    def test_timeout_is_transient(self) -> None:
        assert SubprocessProvider._classify_error("timeout reached") == "transient"

    def test_auth_error_is_permanent(self) -> None:
        assert SubprocessProvider._classify_error("authentication required") == "permanent"

    def test_not_found_is_permanent(self) -> None:
        assert SubprocessProvider._classify_error("command not found") == "permanent"

    def test_invalid_model_is_permanent(self) -> None:
        assert SubprocessProvider._classify_error("invalid model name") == "permanent"

    def test_permission_denied_is_permanent(self) -> None:
        assert SubprocessProvider._classify_error("permission denied") == "permanent"

    def test_unauthorized_is_permanent(self) -> None:
        assert SubprocessProvider._classify_error("401 Unauthorized") == "permanent"

    def test_unknown_error_classified_as_unknown(self) -> None:
        assert SubprocessProvider._classify_error("something went wrong") == "unknown"


# ── SubprocessProvider.is_available() ────────────────────────────────


class TestSubprocessProviderIsAvailable:
    def test_available_when_executable_found(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
        )
        with patch("specforge.core.llm_provider.shutil.which", return_value="/usr/bin/claude"):
            result = provider.is_available()

        assert result.ok is True

    def test_not_available_when_executable_missing(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
        )
        with patch("specforge.core.llm_provider.shutil.which", return_value=None):
            result = provider.is_available()

        assert result.ok is False
        assert "not found on PATH" in result.error

    def test_copilot_checks_gh_executable(self) -> None:
        provider = SubprocessProvider(
            agent_name="copilot",
            command_template="gh copilot suggest -t text",
        )
        calls: list[str] = []

        def mock_which(name: str) -> str | None:
            calls.append(name)
            return "/usr/bin/gh" if name == "gh" else None

        with patch("specforge.core.llm_provider.shutil.which", side_effect=mock_which):
            result = provider.is_available()

        assert result.ok is True
        assert "gh" in calls


# ── Retry behavior ───────────────────────────────────────────────────


class TestSubprocessProviderRetry:
    def test_retry_on_transient_error_succeeds_second_attempt(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=2,
            backoff_base=0.0,
        )
        fail_proc = MagicMock()
        fail_proc.returncode = 1
        fail_proc.stderr = "rate limit exceeded"
        fail_proc.stdout = ""

        ok_proc = MagicMock()
        ok_proc.returncode = 0
        ok_proc.stdout = "# Result"
        ok_proc.stderr = ""

        with patch(
            "specforge.core.llm_provider.subprocess.run",
            side_effect=[fail_proc, ok_proc],
        ):
            result = provider.call("sys", "usr")

        assert result.ok is True
        assert "Result" in result.value

    def test_no_retry_on_permanent_error(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=3,
            backoff_base=0.0,
        )
        fail_proc = MagicMock()
        fail_proc.returncode = 1
        fail_proc.stderr = "authentication required"
        fail_proc.stdout = ""

        with patch(
            "specforge.core.llm_provider.subprocess.run",
            return_value=fail_proc,
        ) as mock_run:
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "authentication" in result.error
        # Should be called exactly once — no retry for permanent errors
        assert mock_run.call_count == 1

    def test_max_retries_exceeded(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
            max_retries=2,
            backoff_base=0.0,
        )
        fail_proc = MagicMock()
        fail_proc.returncode = 1
        fail_proc.stderr = "rate limit exceeded"
        fail_proc.stdout = ""

        with patch(
            "specforge.core.llm_provider.subprocess.run",
            return_value=fail_proc,
        ):
            result = provider.call("sys", "usr")

        assert result.ok is False
        assert "Max retries" in result.error


# ── LLMProvider protocol ─────────────────────────────────────────────


class TestLLMProviderProtocol:
    def test_subprocess_provider_satisfies_protocol(self) -> None:
        provider = SubprocessProvider(
            agent_name="claude",
            command_template="claude -p --output-format text",
        )
        assert isinstance(provider, LLMProvider)


# ── ProviderFactory.create() ─────────────────────────────────────────


class TestProviderFactory:
    def test_create_with_valid_config(self, tmp_path: Path) -> None:
        config = {"agent": "claude", "llm": {"timeout_seconds": 60}}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        with patch("specforge.core.llm_provider.shutil.which", return_value="/usr/bin/claude"):
            result = ProviderFactory.create(config_path)

        assert result.ok is True
        assert isinstance(result.value, SubprocessProvider)

    def test_create_missing_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "nonexistent.json"
        result = ProviderFactory.create(config_path)

        assert result.ok is False
        assert "Config not found" in result.error

    def test_create_unsupported_agent(self, tmp_path: Path) -> None:
        config = {"agent": "unsupported-ai"}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = ProviderFactory.create(config_path)

        assert result.ok is False
        assert "does not support LLM generation" in result.error

    def test_create_generic_agent_rejected(self, tmp_path: Path) -> None:
        config = {"agent": "generic"}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = ProviderFactory.create(config_path)

        assert result.ok is False
        assert "does not support LLM generation" in result.error

    def test_create_agent_not_on_path(self, tmp_path: Path) -> None:
        config = {"agent": "claude"}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        with patch("specforge.core.llm_provider.shutil.which", return_value=None):
            result = ProviderFactory.create(config_path)

        assert result.ok is False
        assert "not found on PATH" in result.error

    def test_create_invalid_json(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json {{{", encoding="utf-8")

        result = ProviderFactory.create(config_path)

        assert result.ok is False
        assert "Failed to read config" in result.error
