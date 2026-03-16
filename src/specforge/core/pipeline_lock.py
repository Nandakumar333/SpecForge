"""PipelineLock — cross-platform atomic file locking via O_CREAT|O_EXCL."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from specforge.core.config import LOCK_STALE_THRESHOLD_MINUTES
from specforge.core.result import Err, Ok, Result


def acquire_lock(lock_path: Path, service_slug: str) -> Result:
    """Acquire a pipeline lock atomically.

    Uses os.open(O_CREAT|O_EXCL) for cross-platform atomicity.
    Returns Err if the lock already exists.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_data = {
        "service_slug": service_slug,
        "pid": os.getpid(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    content = json.dumps(lock_data, indent=2).encode("utf-8")
    try:
        fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
        os.write(fd, content)
        os.fsync(fd)
        os.close(fd)
        return Ok(lock_path)
    except FileExistsError:
        return _lock_exists_error(lock_path, service_slug)
    except OSError as exc:
        return Err(f"Failed to acquire lock: {exc}")


def release_lock(lock_path: Path) -> None:
    """Release a pipeline lock by removing the lock file."""
    import contextlib

    with contextlib.suppress(OSError):
        lock_path.unlink(missing_ok=True)


def is_stale(lock_path: Path) -> bool:
    """Check whether a lock file is stale (older than threshold)."""
    if not lock_path.exists():
        return False
    try:
        raw = lock_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        ts = datetime.fromisoformat(data["timestamp"])
        age = datetime.now(tz=UTC) - ts
        return age > timedelta(minutes=LOCK_STALE_THRESHOLD_MINUTES)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return True


def _lock_exists_error(lock_path: Path, service_slug: str) -> Result:
    """Build a descriptive error for an existing lock."""
    try:
        raw = lock_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        ts = data.get("timestamp", "unknown")
        pid = data.get("pid", "unknown")
        return Err(
            f"Pipeline already locked for '{service_slug}' "
            f"(PID {pid}, since {ts}). "
            "Use --force to override if stale."
        )
    except (OSError, json.JSONDecodeError):
        return Err(
            f"Pipeline lock exists for '{service_slug}'. "
            "Use --force to override."
        )
