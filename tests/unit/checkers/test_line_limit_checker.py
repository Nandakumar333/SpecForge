"""Tests for LineLimitChecker."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.checkers.line_limit_checker import LineLimitChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


# ── Helpers ───────────────────────────────────────────────────────────


def _write_python(tmp_path: Path, name: str, content: str) -> Path:
    """Write a .py file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _short_function() -> str:
    """Return a function that fits in 5 lines."""
    return (
        "def short():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    return a + b + c\n"
    )


def _long_function(lines: int = 45) -> str:
    """Return a function body with the given number of lines."""
    body = "\n".join(f"    x{i} = {i}" for i in range(lines - 2))
    return f"def long_fn():\n{body}\n    return 0\n"


def _long_class(lines: int = 210) -> str:
    """Return a class body with the given number of lines."""
    body = "\n".join(f"    attr{i} = {i}" for i in range(lines - 2))
    return f"class BigClass:\n{body}\n    pass\n"


# ── Properties ────────────────────────────────────────────────────────


class TestProperties:
    def test_name(self) -> None:
        assert LineLimitChecker().name == "line-limit"

    def test_category(self) -> None:
        assert LineLimitChecker().category == ErrorCategory.LINT

    def test_levels(self) -> None:
        assert LineLimitChecker().levels == (CheckLevel.TASK,)

    def test_applicable_all(self) -> None:
        checker = LineLimitChecker()
        assert checker.is_applicable("monolithic")
        assert checker.is_applicable("microservices")


# ── check() ──────────────────────────────────────────────────────────


class TestCheckFunctions:
    def test_function_under_limit_passes(self, tmp_path: Path) -> None:
        fpath = _write_python(tmp_path, "ok.py", _short_function())
        result = LineLimitChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True
        assert result.value.error_details == ()

    def test_function_over_limit_fails(self, tmp_path: Path) -> None:
        fpath = _write_python(tmp_path, "big.py", _long_function(45))
        result = LineLimitChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        details = result.value.error_details
        assert len(details) == 1
        assert "long_fn" in details[0].message
        assert "45 lines" in details[0].message
        assert "(max 30)" in details[0].message

    def test_class_over_limit_fails(self, tmp_path: Path) -> None:
        fpath = _write_python(tmp_path, "cls.py", _long_class(210))
        result = LineLimitChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is False
        details = result.value.error_details
        assert len(details) == 1
        assert "BigClass" in details[0].message
        assert "210 lines" in details[0].message

    def test_custom_thresholds(self, tmp_path: Path) -> None:
        fpath = _write_python(tmp_path, "t.py", _long_function(10))
        checker = LineLimitChecker(max_function_lines=5)
        result = checker.check([fpath], None)
        assert result.ok
        assert result.value.passed is False


class TestFileSkipping:
    def test_non_py_skipped(self, tmp_path: Path) -> None:
        fpath = tmp_path / "readme.md"
        fpath.write_text("# Hello\n" * 100, encoding="utf-8")
        result = LineLimitChecker().check([fpath], None)
        assert result.ok
        assert result.value.passed is True
        assert "Skipped" in result.value.output

    def test_delegates_to_analyzer(self, tmp_path: Path) -> None:
        """Verify the checker calls analyzer methods."""
        fpath = _write_python(tmp_path, "a.py", _short_function())
        from specforge.core.analyzers.python_analyzer import PythonAnalyzer
        analyzer = PythonAnalyzer()
        checker = LineLimitChecker(analyzers=(analyzer,))
        result = checker.check([fpath], None)
        assert result.ok
        assert result.value.passed is True
