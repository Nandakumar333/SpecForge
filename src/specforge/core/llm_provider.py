"""LLMProvider protocol + SubprocessProvider + ProviderFactory (Feature 015)."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from specforge.core.config import (
    INSTALL_HINTS,
    LLM_DEFAULT_BACKOFF_BASE,
    LLM_DEFAULT_MAX_BACKOFF,
    LLM_DEFAULT_MAX_RETRIES,
    LLM_DEFAULT_TIMEOUT,
)
from specforge.core.result import Err, Ok, Result

_AGENT_COMMAND_TEMPLATES: dict[str, str] = {
    "claude": "claude -p --output-format text",
    "copilot": "gh copilot suggest -t text",
    "gemini": "gemini chat",
    "codex": "codex --quiet",
}
"""Maps agent names to CLI command templates."""

_AGENT_EXECUTABLES: dict[str, str] = {
    "claude": "claude",
    "copilot": "gh",
    "gemini": "gemini",
    "codex": "codex",
}
"""Maps agent names to the executable checked via shutil.which()."""

_TRANSIENT_PATTERNS: tuple[str, ...] = (
    "rate limit",
    "connection",
    "timeout",
    "503",
    "429",
    "overloaded",
    "temporarily",
)

_PERMANENT_PATTERNS: tuple[str, ...] = (
    "not found",
    "authentication",
    "invalid model",
    "permission denied",
    "unauthorized",
)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for calling an LLM."""

    def call(self, system_prompt: str, user_prompt: str) -> Result[str, str]: ...

    def is_available(self) -> Result[None, str]: ...


class SubprocessProvider:
    """LLMProvider that invokes an LLM CLI tool via subprocess."""

    def __init__(
        self,
        agent_name: str,
        command_template: str,
        timeout: int = LLM_DEFAULT_TIMEOUT,
        max_retries: int = LLM_DEFAULT_MAX_RETRIES,
        backoff_base: float = LLM_DEFAULT_BACKOFF_BASE,
        max_backoff: float = LLM_DEFAULT_MAX_BACKOFF,
        model: str | None = None,
    ) -> None:
        self._agent_name = agent_name
        self._command_template = command_template
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._max_backoff = max_backoff
        self._model = model

    def call(self, system_prompt: str, user_prompt: str) -> Result[str, str]:
        """Execute CLI tool with retry and timeout."""
        last_error = ""
        for attempt in range(self._max_retries + 1):
            result = self._call_once(system_prompt, user_prompt)
            if result.ok:
                return result
            error_class = self._classify_error(result.error)
            last_error = result.error
            if error_class == "permanent":
                return result
            if attempt < self._max_retries:
                delay = min(
                    self._backoff_base * (2**attempt),
                    self._max_backoff,
                )
                time.sleep(delay)
        return Err(f"Max retries ({self._max_retries}) exceeded: {last_error}")

    def _call_once(self, system_prompt: str, user_prompt: str) -> Result[str, str]:
        """Single subprocess invocation."""
        cmd = self._build_command(system_prompt)
        try:
            proc = subprocess.run(
                cmd,
                input=user_prompt,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return Err(f"LLM call timed out after {self._timeout}s")
        except OSError as exc:
            return Err(f"Failed to invoke {self._agent_name}: {exc}")
        if proc.returncode != 0:
            stderr = proc.stderr.strip() if proc.stderr else "unknown error"
            return Err(f"{self._agent_name} exited {proc.returncode}: {stderr}")
        output = proc.stdout.strip() if proc.stdout else ""
        if not output:
            return Err(f"{self._agent_name} returned empty output")
        return Ok(output)

    def _build_command(self, system_prompt: str) -> list[str]:
        """Build the CLI command list from template."""
        parts = self._command_template.split()
        if self._agent_name == "claude":
            parts.extend(["--system-prompt", system_prompt])
            if self._model:
                parts.extend(["--model", self._model])
        elif self._agent_name == "gemini":
            parts.extend(["--system", system_prompt])
            if self._model:
                parts.extend(["--model", self._model])
        elif self._agent_name == "codex":
            if self._model:
                parts.extend(["--model", self._model])
        return parts

    @staticmethod
    def _classify_error(error_text: str) -> str:
        """Classify error as transient, permanent, or unknown."""
        lower = error_text.lower()
        if any(p in lower for p in _TRANSIENT_PATTERNS):
            return "transient"
        if any(p in lower for p in _PERMANENT_PATTERNS):
            return "permanent"
        return "unknown"

    def is_available(self) -> Result[None, str]:
        """Check CLI tool on PATH via shutil.which()."""
        exe = _AGENT_EXECUTABLES.get(self._agent_name, self._agent_name)
        if shutil.which(exe):
            return Ok(None)
        hint = INSTALL_HINTS.get(self._agent_name, "")
        msg = f"CLI tool '{exe}' not found on PATH"
        if hint:
            msg += f" — install: {hint}"
        return Err(msg)


class ProviderFactory:
    """Resolves configured agent to an LLMProvider instance."""

    @staticmethod
    def create(config_path: Path) -> Result[LLMProvider, str]:
        """Read config.json, map agent to provider, validate."""
        if not config_path.exists():
            return Err(f"Config not found: {config_path}")
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return Err(f"Failed to read config: {exc}")
        agent = data.get("agent", "generic")
        if agent not in _AGENT_COMMAND_TEMPLATES:
            return Err(f"Agent '{agent}' does not support LLM generation")
        cmd_template = _AGENT_COMMAND_TEMPLATES[agent]
        llm_cfg = data.get("llm", {})
        # Check env var overrides
        import os

        cli_path = os.environ.get("SPECFORGE_LLM_CLI_PATH")
        if cli_path:
            cmd_template = cli_path

        provider = SubprocessProvider(
            agent_name=agent,
            command_template=cmd_template,
            timeout=llm_cfg.get("timeout_seconds", LLM_DEFAULT_TIMEOUT),
            max_retries=llm_cfg.get("max_retries", LLM_DEFAULT_MAX_RETRIES),
            model=llm_cfg.get("model"),
        )
        avail = provider.is_available()
        if not avail.ok:
            return Err(avail.error)
        return Ok(provider)
