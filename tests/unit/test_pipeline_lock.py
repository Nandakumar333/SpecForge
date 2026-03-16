"""Unit tests for PipelineLock acquire/release/stale detection."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from specforge.core.pipeline_lock import (
    acquire_lock,
    is_stale,
    release_lock,
)


class TestAcquireLock:
    """Tests for acquire_lock()."""

    def test_creates_lock_file(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        result = acquire_lock(lock_path, "ledger-service")
        assert result.ok
        assert lock_path.exists()
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["service_slug"] == "ledger-service"
        assert "pid" in data
        assert "timestamp" in data

    def test_fails_when_lock_exists(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        result1 = acquire_lock(lock_path, "ledger-service")
        assert result1.ok
        result2 = acquire_lock(lock_path, "ledger-service")
        assert not result2.ok
        assert "already" in result2.error.lower() or "lock" in result2.error.lower()

    def test_concurrent_different_services(self, tmp_path: Path) -> None:
        lock1 = tmp_path / "svc1" / ".pipeline-lock"
        lock2 = tmp_path / "svc2" / ".pipeline-lock"
        lock1.parent.mkdir(parents=True)
        lock2.parent.mkdir(parents=True)
        r1 = acquire_lock(lock1, "svc1")
        r2 = acquire_lock(lock2, "svc2")
        assert r1.ok
        assert r2.ok


class TestReleaseLock:
    """Tests for release_lock()."""

    def test_removes_lock_file(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        acquire_lock(lock_path, "test")
        release_lock(lock_path)
        assert not lock_path.exists()

    def test_no_error_if_missing(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        release_lock(lock_path)  # Should not raise


class TestIsStale:
    """Tests for is_stale()."""

    def test_fresh_lock_not_stale(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        acquire_lock(lock_path, "test")
        assert not is_stale(lock_path)

    def test_old_lock_is_stale(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        old_ts = (datetime.now(tz=UTC) - timedelta(minutes=31)).isoformat()
        lock_data = {
            "service_slug": "test",
            "pid": 12345,
            "timestamp": old_ts,
        }
        lock_path.write_text(
            json.dumps(lock_data), encoding="utf-8"
        )
        assert is_stale(lock_path)

    def test_missing_lock_not_stale(self, tmp_path: Path) -> None:
        lock_path = tmp_path / ".pipeline-lock"
        assert not is_stale(lock_path)
