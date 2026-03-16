"""Unit tests for PipelineState transitions and persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.pipeline_state import (
    PhaseStatus,
    PipelineState,
    create_initial_state,
    detect_interrupted,
    get_next_phase,
    is_phase_complete,
    load_state,
    mark_complete,
    mark_failed,
    mark_in_progress,
    reset_all_phases,
    save_state,
)


class TestPhaseStatus:
    """Tests for PhaseStatus dataclass."""

    def test_frozen(self) -> None:
        ps = PhaseStatus(name="spec", status="pending")
        with pytest.raises(AttributeError):
            ps.status = "complete"  # type: ignore[misc]

    def test_defaults(self) -> None:
        ps = PhaseStatus(name="spec", status="pending")
        assert ps.started_at is None
        assert ps.completed_at is None
        assert ps.artifact_paths == ()
        assert ps.error is None


class TestCreateInitialState:
    """Tests for create_initial_state()."""

    def test_creates_all_phases(self) -> None:
        state = create_initial_state("ledger-service")
        assert state.service_slug == "ledger-service"
        assert state.schema_version == "1.0"
        assert len(state.phases) == 7
        for ps in state.phases:
            assert ps.status == "pending"

    def test_phase_names_match_config(self) -> None:
        from specforge.core.config import PIPELINE_PHASES

        state = create_initial_state("test")
        names = [ps.name for ps in state.phases]
        assert names == PIPELINE_PHASES


class TestStateTransitions:
    """Tests for mark_in_progress, mark_complete, mark_failed."""

    def test_mark_in_progress(self) -> None:
        state = create_initial_state("test")
        new_state = mark_in_progress(state, "spec")
        spec = _get_phase(new_state, "spec")
        assert spec.status == "in-progress"
        assert spec.started_at is not None

    def test_mark_complete(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        new_state = mark_complete(state, "spec", ("spec.md",))
        spec = _get_phase(new_state, "spec")
        assert spec.status == "complete"
        assert spec.completed_at is not None
        assert spec.artifact_paths == ("spec.md",)

    def test_mark_failed(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        new_state = mark_failed(state, "spec", "Template error")
        spec = _get_phase(new_state, "spec")
        assert spec.status == "failed"
        assert spec.error == "Template error"

    def test_immutability(self) -> None:
        state = create_initial_state("test")
        new_state = mark_in_progress(state, "spec")
        assert _get_phase(state, "spec").status == "pending"
        assert _get_phase(new_state, "spec").status == "in-progress"


class TestIsPhaseComplete:
    """Tests for is_phase_complete()."""

    def test_pending_not_complete(self) -> None:
        state = create_initial_state("test")
        assert not is_phase_complete(state, "spec")

    def test_complete_is_complete(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        state = mark_complete(state, "spec", ("spec.md",))
        assert is_phase_complete(state, "spec")


class TestGetNextPhase:
    """Tests for get_next_phase()."""

    def test_first_phase(self) -> None:
        state = create_initial_state("test")
        assert get_next_phase(state) == "spec"

    def test_after_first_complete(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        state = mark_complete(state, "spec", ("spec.md",))
        assert get_next_phase(state) == "research"

    def test_all_complete(self) -> None:
        state = create_initial_state("test")
        for name in ["spec", "research", "datamodel", "edgecase",
                      "plan", "checklist", "tasks"]:
            state = mark_in_progress(state, name)
            state = mark_complete(state, name, (f"{name}.md",))
        assert get_next_phase(state) is None


class TestDetectInterrupted:
    """Tests for detect_interrupted()."""

    def test_no_interrupted(self) -> None:
        state = create_initial_state("test")
        new_state = detect_interrupted(state)
        for ps in new_state.phases:
            assert ps.status == "pending"

    def test_resets_in_progress(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        new_state = detect_interrupted(state)
        assert _get_phase(new_state, "spec").status == "pending"


class TestResetAllPhases:
    """Tests for reset_all_phases() (--force)."""

    def test_resets_completed(self) -> None:
        state = create_initial_state("test")
        state = mark_in_progress(state, "spec")
        state = mark_complete(state, "spec", ("spec.md",))
        new_state = reset_all_phases(state)
        for ps in new_state.phases:
            assert ps.status == "pending"


class TestPersistence:
    """Tests for save_state() and load_state()."""

    def test_round_trip(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".pipeline-state.json"
        state = create_initial_state("ledger-service")
        state = mark_in_progress(state, "spec")
        state = mark_complete(state, "spec", ("spec.md",))
        save_result = save_state(state_path, state)
        assert save_result.ok
        load_result = load_state(state_path)
        assert load_result.ok
        loaded = load_result.value
        assert loaded.service_slug == "ledger-service"
        assert is_phase_complete(loaded, "spec")

    def test_load_missing_file(self, tmp_path: Path) -> None:
        state_path = tmp_path / "missing.json"
        result = load_state(state_path)
        assert result.ok
        assert result.value is None

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        state_path = tmp_path / "bad.json"
        state_path.write_text("not json", encoding="utf-8")
        result = load_state(state_path)
        assert not result.ok


def _get_phase(state: PipelineState, name: str) -> PhaseStatus:
    """Helper to find a phase by name."""
    for ps in state.phases:
        if ps.name == name:
            return ps
    msg = f"Phase '{name}' not found"
    raise ValueError(msg)
