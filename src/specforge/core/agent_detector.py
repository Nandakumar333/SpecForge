"""PATH-based agent detection for SpecForge."""

from __future__ import annotations

import shutil

from specforge.core.config import AGENT_EXECUTABLES, AGENT_PRIORITY
from specforge.core.project import DetectionResult


def detect_agent(explicit: str | None = None) -> DetectionResult:
    """Detect the first available AI agent CLI in PATH.

    If explicit is provided, skip detection and return it directly.
    Otherwise, iterate AGENT_PRIORITY and probe each executable.
    """
    if explicit:
        return DetectionResult(
            agent=explicit,
            source="explicit",
            executable=None,
        )
    for agent in AGENT_PRIORITY:
        for exe in AGENT_EXECUTABLES.get(agent, []):
            if shutil.which(exe):
                return DetectionResult(
                    agent=agent,
                    source="auto-detected",
                    executable=exe,
                )
    return DetectionResult(agent="agnostic", source="agnostic")
