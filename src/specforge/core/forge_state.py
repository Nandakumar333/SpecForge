"""ForgeState — persisted forge run state for resume capability (Feature 017)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.config import (
    FORGE_LOCK_TIMEOUT_HOURS,
    FORGE_STAGES,
    FORGE_STATE_SCHEMA_VERSION,
)
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ServiceForgeStatus:
    """Per-service forge progress tracking."""

    slug: str
    last_completed_phase: int = 0
    status: str = "pending"
    retry_count: int = 0
    error: str | None = None
    last_update: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ServiceForgeStatus:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ForgeState:
    """Persisted state for a forge run."""

    schema_version: str = FORGE_STATE_SCHEMA_VERSION
    stage: str = "init"
    description: str = ""
    architecture: str = "monolithic"
    services: dict[str, ServiceForgeStatus] = field(default_factory=dict)
    started_at: str = field(default_factory=_now_iso)
    last_update: str = field(default_factory=_now_iso)
    run_status: str = "idle"
    pid: int | None = None
    lock_timestamp: str | None = None

    @classmethod
    def create(
        cls, description: str = "", architecture: str = "monolithic",
    ) -> ForgeState:
        return cls(
            description=description,
            architecture=architecture,
            started_at=_now_iso(),
            last_update=_now_iso(),
        )

    def update_stage(self, stage: str) -> None:
        if stage in FORGE_STAGES:
            self.stage = stage
            self.last_update = _now_iso()

    def mark_service_phase_complete(self, slug: str) -> None:
        svc = self.services.get(slug)
        if svc and svc.last_completed_phase < 7:
            svc.last_completed_phase += 1
            svc.status = "in_progress"
            svc.last_update = _now_iso()
            self.last_update = _now_iso()

    def mark_service_complete(self, slug: str) -> None:
        svc = self.services.get(slug)
        if svc:
            svc.status = "complete"
            svc.last_update = _now_iso()
            self.last_update = _now_iso()

    def mark_service_failed(self, slug: str, error: str) -> None:
        svc = self.services.get(slug)
        if svc:
            svc.retry_count += 1
            svc.error = error
            svc.status = "failed"
            svc.last_update = _now_iso()
            self.last_update = _now_iso()

    def mark_service_permanently_failed(self, slug: str) -> None:
        svc = self.services.get(slug)
        if svc:
            svc.status = "permanently_failed"
            svc.last_update = _now_iso()
            self.last_update = _now_iso()

    def incomplete_services(self) -> list[str]:
        return [
            slug for slug, svc in self.services.items()
            if svc.status not in ("complete", "permanently_failed")
        ]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "description": self.description,
            "architecture": self.architecture,
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "started_at": self.started_at,
            "last_update": self.last_update,
            "run_status": self.run_status,
            "pid": self.pid,
            "lock_timestamp": self.lock_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ForgeState:
        services = {}
        for slug, svc_data in data.get("services", {}).items():
            services[slug] = ServiceForgeStatus.from_dict(svc_data)
        return cls(
            schema_version=data.get("schema_version", FORGE_STATE_SCHEMA_VERSION),
            stage=data.get("stage", "init"),
            description=data.get("description", ""),
            architecture=data.get("architecture", "monolithic"),
            services=services,
            started_at=data.get("started_at", _now_iso()),
            last_update=data.get("last_update", _now_iso()),
            run_status=data.get("run_status", "idle"),
            pid=data.get("pid"),
            lock_timestamp=data.get("lock_timestamp"),
        )

    def save(self, path: Path) -> Result[None, str]:
        """Atomic save via write-to-tmp + os.replace."""
        tmp_path = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.last_update = _now_iso()
            tmp_path.write_text(
                json.dumps(self.to_dict(), indent=2),
                encoding="utf-8",
            )
            os.replace(str(tmp_path), str(path))
            return Ok(None)
        except OSError as exc:
            return Err(f"Failed to save forge state: {exc}")

    @classmethod
    def load(cls, path: Path) -> Result[ForgeState, str]:
        """Load state from JSON file. Corrupt file → fresh state + warning."""
        if not path.exists():
            return Ok(cls.create())
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Ok(cls.from_dict(data))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt forge-state.json: %s — starting fresh", exc)
            return Ok(cls.create())

    def is_locked(self) -> bool:
        return self.run_status == "running" and self.pid is not None

    def acquire_lock(self) -> None:
        self.run_status = "running"
        self.pid = os.getpid()
        self.lock_timestamp = _now_iso()

    def release_lock(self) -> None:
        self.run_status = "idle"
        self.pid = None
        self.lock_timestamp = None

    def clear_stale_lock(self) -> bool:
        """Clear lock if stale. Returns True if cleared."""
        if not self.lock_timestamp:
            return False
        try:
            lock_time = datetime.fromisoformat(self.lock_timestamp)
            elapsed = (datetime.now(UTC) - lock_time).total_seconds()
            if elapsed > FORGE_LOCK_TIMEOUT_HOURS * 3600:
                self.release_lock()
                return True
        except (ValueError, TypeError):
            self.release_lock()
            return True
        return False
