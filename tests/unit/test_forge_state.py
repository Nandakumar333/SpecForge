"""Unit tests for ForgeState and ServiceForgeStatus (Feature 017)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specforge.core.forge_state import ForgeState, ServiceForgeStatus


class TestServiceForgeStatus:
    def test_default_values(self) -> None:
        svc = ServiceForgeStatus(slug="auth-service")
        assert svc.slug == "auth-service"
        assert svc.last_completed_phase == 0
        assert svc.status == "pending"
        assert svc.retry_count == 0
        assert svc.error is None

    def test_round_trip(self) -> None:
        svc = ServiceForgeStatus(slug="api", last_completed_phase=3, status="in_progress")
        data = svc.to_dict()
        restored = ServiceForgeStatus.from_dict(data)
        assert restored.slug == svc.slug
        assert restored.last_completed_phase == 3


class TestForgeState:
    def test_create_defaults(self) -> None:
        state = ForgeState.create()
        assert state.stage == "init"
        assert state.run_status == "idle"
        assert state.services == {}

    def test_update_stage(self) -> None:
        state = ForgeState.create()
        state.update_stage("decompose")
        assert state.stage == "decompose"
        state.update_stage("spec_generation")
        assert state.stage == "spec_generation"
        state.update_stage("invalid_stage")
        assert state.stage == "spec_generation"

    def test_mark_service_phase_complete(self) -> None:
        state = ForgeState.create()
        state.services["svc"] = ServiceForgeStatus(slug="svc")
        state.mark_service_phase_complete("svc")
        assert state.services["svc"].last_completed_phase == 1
        for _ in range(6):
            state.mark_service_phase_complete("svc")
        assert state.services["svc"].last_completed_phase == 7
        state.mark_service_phase_complete("svc")
        assert state.services["svc"].last_completed_phase == 7

    def test_mark_service_failed(self) -> None:
        state = ForgeState.create()
        state.services["svc"] = ServiceForgeStatus(slug="svc")
        state.mark_service_failed("svc", "timeout")
        assert state.services["svc"].retry_count == 1
        assert state.services["svc"].error == "timeout"
        assert state.services["svc"].status == "failed"

    def test_mark_permanently_failed(self) -> None:
        state = ForgeState.create()
        state.services["svc"] = ServiceForgeStatus(slug="svc")
        state.mark_service_permanently_failed("svc")
        assert state.services["svc"].status == "permanently_failed"

    def test_incomplete_services(self) -> None:
        state = ForgeState.create()
        state.services["a"] = ServiceForgeStatus(slug="a", status="complete")
        state.services["b"] = ServiceForgeStatus(slug="b", status="failed")
        state.services["c"] = ServiceForgeStatus(slug="c", status="permanently_failed")
        state.services["d"] = ServiceForgeStatus(slug="d", status="pending")
        assert state.incomplete_services() == ["b", "d"]

    def test_to_dict_from_dict_round_trip(self) -> None:
        state = ForgeState.create(description="test app", architecture="microservice")
        state.services["svc"] = ServiceForgeStatus(slug="svc", last_completed_phase=3)
        data = state.to_dict()
        restored = ForgeState.from_dict(data)
        assert restored.description == "test app"
        assert restored.architecture == "microservice"
        assert restored.services["svc"].last_completed_phase == 3

    def test_save_and_load(self, tmp_path: Path) -> None:
        state = ForgeState.create(description="save test")
        state.services["svc"] = ServiceForgeStatus(slug="svc", last_completed_phase=5)
        path = tmp_path / "forge-state.json"
        result = state.save(path)
        assert result.ok
        assert path.exists()

        loaded = ForgeState.load(path)
        assert loaded.ok
        assert loaded.value.description == "save test"
        assert loaded.value.services["svc"].last_completed_phase == 5

    def test_load_missing_returns_fresh(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        result = ForgeState.load(path)
        assert result.ok
        assert result.value.stage == "init"

    def test_load_corrupt_returns_fresh(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt.json"
        path.write_text("not json at all", encoding="utf-8")
        result = ForgeState.load(path)
        assert result.ok
        assert result.value.stage == "init"

    def test_lock_lifecycle(self) -> None:
        state = ForgeState.create()
        assert not state.is_locked()
        state.acquire_lock()
        assert state.is_locked()
        assert state.pid is not None
        state.release_lock()
        assert not state.is_locked()

    def test_clear_stale_lock(self) -> None:
        state = ForgeState.create()
        state.acquire_lock()
        state.lock_timestamp = "2020-01-01T00:00:00+00:00"
        assert state.clear_stale_lock()
        assert not state.is_locked()

    def test_clear_non_stale_lock(self) -> None:
        state = ForgeState.create()
        state.acquire_lock()
        assert not state.clear_stale_lock()
        assert state.is_locked()

    def test_save_atomic(self, tmp_path: Path) -> None:
        """Verify atomic write (no .tmp leftover on success)."""
        state = ForgeState.create()
        path = tmp_path / "state.json"
        state.save(path)
        tmp_file = path.with_suffix(".tmp")
        assert not tmp_file.exists()
        assert path.exists()
