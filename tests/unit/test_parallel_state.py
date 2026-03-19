"""Unit tests for parallel_state module (Feature 016)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.parallel_state import (
    ParallelExecutionState,
    ServiceRunStatus,
    WaveStatus,
    create_initial_state,
    detect_resume_point,
    load_state,
    mark_service_blocked,
    mark_service_cancelled,
    mark_service_completed,
    mark_service_failed,
    mark_service_in_progress,
    save_state,
)


class TestServiceRunStatus:
    def test_defaults(self):
        s = ServiceRunStatus(slug="auth-service")
        assert s.status == "pending"
        assert s.wave_index == 0
        assert s.phases_completed == 0
        assert s.phases_total == 7
        assert s.error is None
        assert s.blocked_by is None

    def test_frozen(self):
        s = ServiceRunStatus(slug="a")
        with pytest.raises(AttributeError):
            s.status = "completed"


class TestWaveStatus:
    def test_creation(self):
        w = WaveStatus(index=0, services=("a", "b"))
        assert w.status == "pending"
        assert w.services == ("a", "b")


class TestParallelExecutionState:
    def test_creation(self):
        state = ParallelExecutionState(
            run_id="2026-01-01",
            mode="decompose",
            architecture="microservice",
            total_services=3,
            max_workers=4,
        )
        assert state.status == "pending"
        assert state.fail_fast is False
        assert state.services == ()
        assert state.waves == ()


class TestStateTransitions:
    @pytest.fixture()
    def base_state(self):
        return create_initial_state(
            mode="decompose",
            architecture="microservice",
            service_slugs=("auth", "ledger", "admin"),
            max_workers=4,
        )

    def test_mark_in_progress(self, base_state):
        updated = mark_service_in_progress(base_state, "auth")
        auth = next(s for s in updated.services if s.slug == "auth")
        assert auth.status == "in-progress"
        assert auth.started_at is not None

    def test_mark_completed(self, base_state):
        updated = mark_service_completed(base_state, "ledger", 7)
        ledger = next(s for s in updated.services if s.slug == "ledger")
        assert ledger.status == "completed"
        assert ledger.phases_completed == 7

    def test_mark_failed(self, base_state):
        updated = mark_service_failed(base_state, "admin", "timeout", 3)
        admin = next(s for s in updated.services if s.slug == "admin")
        assert admin.status == "failed"
        assert admin.error == "timeout"
        assert admin.phases_completed == 3

    def test_mark_blocked(self, base_state):
        updated = mark_service_blocked(base_state, "ledger", "auth")
        ledger = next(s for s in updated.services if s.slug == "ledger")
        assert ledger.status == "blocked"
        assert ledger.blocked_by == "auth"

    def test_mark_cancelled(self, base_state):
        updated = mark_service_cancelled(base_state, "auth")
        auth = next(s for s in updated.services if s.slug == "auth")
        assert auth.status == "cancelled"


class TestCreateInitialState:
    def test_basic(self):
        state = create_initial_state(
            mode="decompose",
            architecture="microservice",
            service_slugs=("a", "b"),
            max_workers=2,
        )
        assert state.total_services == 2
        assert len(state.services) == 2
        assert state.services[0].slug == "a"
        assert state.services[1].slug == "b"

    def test_with_waves(self):
        waves = (
            WaveStatus(index=0, services=("a",)),
            WaveStatus(index=1, services=("b",)),
        )
        state = create_initial_state(
            mode="implement",
            architecture="microservice",
            service_slugs=("a", "b"),
            max_workers=4,
            waves=waves,
        )
        a = next(s for s in state.services if s.slug == "a")
        b = next(s for s in state.services if s.slug == "b")
        assert a.wave_index == 0
        assert b.wave_index == 1


class TestDetectResumePoint:
    def test_filters_completed(self):
        state = create_initial_state(
            mode="decompose",
            architecture="microservice",
            service_slugs=("a", "b", "c"),
            max_workers=4,
        )
        state = mark_service_completed(state, "a")
        state = mark_service_blocked(state, "c", "a")
        remaining = detect_resume_point(state)
        assert remaining == ("b",)


class TestPersistence:
    def test_round_trip(self, tmp_path):
        state = create_initial_state(
            mode="decompose",
            architecture="microservice",
            service_slugs=("x", "y"),
            max_workers=2,
            fail_fast=True,
        )
        state = mark_service_completed(state, "x")

        path = tmp_path / ".specforge" / "parallel-state.json"
        save_state(path, state)
        loaded = load_state(path)

        assert loaded is not None
        assert loaded.mode == "decompose"
        assert loaded.total_services == 2
        assert loaded.fail_fast is True
        x = next(s for s in loaded.services if s.slug == "x")
        assert x.status == "completed"
        y = next(s for s in loaded.services if s.slug == "y")
        assert y.status == "pending"

    def test_load_nonexistent(self, tmp_path):
        result = load_state(tmp_path / "nope.json")
        assert result is None

    def test_load_corrupt(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        result = load_state(path)
        assert result is None

    def test_round_trip_with_waves(self, tmp_path):
        waves = (WaveStatus(index=0, services=("a", "b")),)
        state = create_initial_state(
            mode="implement",
            architecture="microservice",
            service_slugs=("a", "b"),
            max_workers=4,
            waves=waves,
        )
        path = tmp_path / "state.json"
        save_state(path, state)
        loaded = load_state(path)
        assert loaded is not None
        assert len(loaded.waves) == 1
        assert loaded.waves[0].services == ("a", "b")
