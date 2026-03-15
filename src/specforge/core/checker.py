"""Prerequisite checker — verify required tools are available."""

from __future__ import annotations

import re
import shutil
import subprocess

from specforge.core.config import INSTALL_HINTS, PREREQUISITES
from specforge.core.project import CheckResult


def check_prerequisites(agent: str | None = None) -> list[CheckResult]:
    """Check all prerequisites and optionally an agent CLI."""
    tools = list(PREREQUISITES)
    if agent:
        tools.append(agent)
    return [_check_tool(tool) for tool in tools]


def _check_tool(tool: str) -> CheckResult:
    """Check a single tool for availability and version."""
    found = shutil.which(tool) is not None
    version = _get_version(tool) if found else None
    hint = INSTALL_HINTS.get(tool, "")
    return CheckResult(
        tool=tool,
        found=found,
        version=version,
        install_hint=hint,
    )


def _get_version(tool: str) -> str | None:
    """Attempt to detect tool version via --version flag."""
    try:
        result = subprocess.run(
            [tool, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip() or result.stderr.strip()
        match = re.search(r"(\d+\.\d+[\.\d]*)", output)
        return match.group(1) if match else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
