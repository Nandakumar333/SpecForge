"""Tests for TodoChecker."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.checkers.todo_checker import TodoChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


# ── Helpers ───────────────────────────────────────────────────────────


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write a file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ── Properties ────────────────────────────────────────────────────────


class TestProperties:
    def test_name(self) -> None:
        assert TodoChecker().name == "todo"

    def test_category(self) -> None:
        assert TodoChecker().category == ErrorCategory.LINT

    def test_levels(self) -> None:
        assert TodoChecker().levels == (CheckLevel.TASK,)

    def test_applicable_all(self) -> None:
        checker = TodoChecker()
        assert checker.is_applicable("monolithic")
        assert checker.is_applicable("microservices")


# ── Detection ─────────────────────────────────────────────────────────


class TestDetection:
    def test_todo_detected(self, tmp_path: Path) -> None:
        content = "# TODO: fix this later\nx = 1\n"
        fpath = _write_file(tmp_path, "main.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        assert len(result.value.error_details) == 1
        assert "TODO" in result.value.error_details[0].message

    def test_fixme_detected(self, tmp_path: Path) -> None:
        content = "x = 1\n# FIXME: broken logic\n"
        fpath = _write_file(tmp_path, "logic.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        assert len(result.value.error_details) == 1
        assert "FIXME" in result.value.error_details[0].message

    def test_hack_detected(self, tmp_path: Path) -> None:
        content = "# HACK: workaround for bug\n"
        fpath = _write_file(tmp_path, "hack.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False

    def test_xxx_detected(self, tmp_path: Path) -> None:
        content = "# XXX: needs review\n"
        fpath = _write_file(tmp_path, "review.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False

    def test_case_insensitive(self, tmp_path: Path) -> None:
        content = "# todo: lowercase\n# Fixme: mixed\n"
        fpath = _write_file(tmp_path, "mixed.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        assert len(result.value.error_details) == 2

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        content = "x = 1\ny = 2\nz = x + y\n"
        fpath = _write_file(tmp_path, "clean.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True
        assert result.value.error_details == ()

    def test_multiple_matches_one_file(self, tmp_path: Path) -> None:
        content = (
            "# TODO: first\n"
            "x = 1\n"
            "# FIXME: second\n"
            "# HACK: third\n"
        )
        fpath = _write_file(tmp_path, "multi.py", content)
        result = TodoChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        assert len(result.value.error_details) == 3


# ── Binary file handling ──────────────────────────────────────────────


class TestBinaryFiles:
    def test_binary_file_skipped(self, tmp_path: Path) -> None:
        fpath = tmp_path / "image.bin"
        fpath.write_bytes(b"\x00\x01\x02\xff\xfe TODO \x00")
        result = TodoChecker().check([fpath], None)
        assert result.ok
        # Should not crash — gracefully skip
