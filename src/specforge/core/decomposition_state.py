"""DecompositionState persistence — save/load/resume partial state."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specforge.core.result import Err, Ok, Result


@dataclass(frozen=True)
class DecompositionState:
    """Persistent state for the multi-step decompose flow."""

    step: str = "architecture"
    architecture: str | None = None
    project_description: str = ""
    domain: str | None = None
    features: tuple[Any, ...] = ()
    services: tuple[Any, ...] = ()
    timestamp: str = field(default_factory=lambda: "")


def save_state(path: Path, state: DecompositionState) -> Result:
    """Save decomposition state atomically to disk."""
    data = _state_to_dict(state)
    return _atomic_write_json(path, data)


def load_state(path: Path) -> Result:
    """Load decomposition state from disk. Returns Ok(None) if no file."""
    if not path.exists():
        return Ok(None)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return Ok(_dict_to_state(data))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return Err(f"Invalid state file '{path}': {exc}")


def _state_to_dict(state: DecompositionState) -> dict:
    """Convert DecompositionState to a serializable dict."""
    return {
        "step": state.step,
        "architecture": state.architecture,
        "project_description": state.project_description,
        "domain": state.domain,
        "features": list(state.features),
        "services": list(state.services),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def _dict_to_state(data: dict) -> DecompositionState:
    """Convert a dict back to DecompositionState."""
    return DecompositionState(
        step=data["step"],
        architecture=data.get("architecture"),
        project_description=data.get("project_description", ""),
        domain=data.get("domain"),
        features=tuple(data.get("features", ())),
        services=tuple(data.get("services", ())),
        timestamp=data.get("timestamp", ""),
    )


def _atomic_write_json(path: Path, data: dict) -> Result:
    """Write JSON atomically: temp file + fsync + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    fd: int | None = None
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)
        os.write(fd, content)
        os.fsync(fd)
        os.close(fd)
        fd = None
        tmp_path.replace(path)
        tmp_path = None
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write state '{path}': {exc}")
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
