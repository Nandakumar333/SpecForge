"""Unit tests for DecompositionState persistence (UT-012, UT-013)."""

from __future__ import annotations

from pathlib import Path

from specforge.core.decomposition_state import (
    DecompositionState,
    load_state,
    save_state,
)


class TestDecompositionStateSaveLoad:
    """UT-012: save/load round-trip for each step."""

    def test_save_and_load_architecture_step(self, tmp_path: Path) -> None:
        state = DecompositionState(
            step="architecture",
            architecture="microservice",
            project_description="Create a finance app",
            domain=None,
            features=(),
            services=(),
        )
        path = tmp_path / "state.json"
        result = save_state(path, state)
        assert result.ok
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.step == "architecture"
        assert loaded.value.architecture == "microservice"
        assert loaded.value.project_description == "Create a finance app"

    def test_save_and_load_decomposition_step(self, tmp_path: Path) -> None:
        state = DecompositionState(
            step="decomposition",
            architecture="monolithic",
            project_description="Build a TODO app",
            domain="generic",
            features=(
                {"id": "001", "name": "auth", "description": "Auth"},
            ),
            services=(),
        )
        path = tmp_path / "state.json"
        result = save_state(path, state)
        assert result.ok
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.step == "decomposition"
        assert loaded.value.domain == "generic"
        assert len(loaded.value.features) == 1

    def test_save_and_load_mapping_step(self, tmp_path: Path) -> None:
        state = DecompositionState(
            step="mapping",
            architecture="microservice",
            project_description="Finance app",
            domain="finance",
            features=({"id": "001", "name": "auth"},),
            services=({"name": "Identity", "slug": "identity", "feature_ids": ["001"]},),
        )
        path = tmp_path / "state.json"
        save_state(path, state)
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.step == "mapping"
        assert len(loaded.value.services) == 1

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "dir" / "state.json"
        state = DecompositionState(
            step="architecture",
            architecture="monolithic",
            project_description="test",
        )
        result = save_state(path, state)
        assert result.ok
        assert path.exists()

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state1 = DecompositionState(step="architecture", project_description="v1")
        state2 = DecompositionState(step="decomposition", project_description="v2")
        save_state(path, state1)
        save_state(path, state2)
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.step == "decomposition"


class TestDecompositionStateResume:
    """UT-013: resume detection from partial state file."""

    def test_load_returns_none_when_no_file(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        result = load_state(path)
        assert result.ok
        assert result.value is None

    def test_load_detects_partial_state(self, tmp_path: Path) -> None:
        state = DecompositionState(
            step="architecture",
            architecture="microservice",
            project_description="test",
        )
        path = tmp_path / "state.json"
        save_state(path, state)
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.step != "complete"

    def test_load_returns_error_on_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text("not json{{{", encoding="utf-8")
        result = load_state(path)
        assert not result.ok

    def test_state_has_timestamp(self, tmp_path: Path) -> None:
        state = DecompositionState(
            step="architecture",
            project_description="test",
        )
        path = tmp_path / "state.json"
        save_state(path, state)
        loaded = load_state(path)
        assert loaded.ok
        assert loaded.value is not None
        assert loaded.value.timestamp is not None
        assert len(loaded.value.timestamp) > 0
