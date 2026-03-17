"""Tests for PythonAnalyzer — AST-based function/class analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.analyzers.python_analyzer import PythonAnalyzer
from specforge.core.quality_models import ClassInfo, FunctionInfo
from specforge.core.result import Err, Ok


@pytest.fixture()
def analyzer() -> PythonAnalyzer:
    return PythonAnalyzer()


# ── supports_extension ──────────────────────────────────────────────


class TestSupportsExtension:
    def test_py_supported(self, analyzer: PythonAnalyzer) -> None:
        assert analyzer.supports_extension(".py") is True

    def test_cs_not_supported(self, analyzer: PythonAnalyzer) -> None:
        assert analyzer.supports_extension(".cs") is False

    def test_case_insensitive(self, analyzer: PythonAnalyzer) -> None:
        assert analyzer.supports_extension(".PY") is True


# ── analyze_functions ───────────────────────────────────────────────


class TestAnalyzeFunctions:
    def test_short_function(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "short.py"
        src.write_text(
            "def greet(name):\n"
            "    greeting = f'Hello {name}'\n"
            "    print(greeting)\n"
            "    return greeting\n"
            "    pass  # pad\n"
        )
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Ok)
        funcs = result.value
        assert len(funcs) == 1
        assert funcs[0] == FunctionInfo(
            name="greet",
            file_path=str(src),
            start_line=1,
            end_line=5,
            line_count=5,
        )

    def test_long_function(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        lines = ["def big():\n"] + [f"    x = {i}\n" for i in range(39)]
        src = tmp_path / "long.py"
        src.write_text("".join(lines))
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Ok)
        assert result.value[0].line_count == 40

    def test_async_function(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "async_mod.py"
        src.write_text("async def fetch():\n    return 1\n")
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Ok)
        assert len(result.value) == 1
        assert result.value[0].name == "fetch"
        assert result.value[0].line_count == 2

    def test_nested_functions(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "nested.py"
        src.write_text(
            "def outer():\n"
            "    def inner():\n"
            "        pass\n"
            "    return inner\n"
        )
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Ok)
        names = {f.name for f in result.value}
        assert names == {"outer", "inner"}

    def test_only_functions_not_classes(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "mixed.py"
        src.write_text(
            "def standalone():\n"
            "    pass\n"
            "\n"
            "class Foo:\n"
            "    pass\n"
        )
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Ok)
        assert len(result.value) == 1
        assert result.value[0].name == "standalone"


# ── analyze_classes ─────────────────────────────────────────────────


class TestAnalyzeClasses:
    def test_single_class(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "cls.py"
        src.write_text(
            "class Widget:\n"
            "    def __init__(self):\n"
            "        self.x = 1\n"
            "\n"
            "    def run(self):\n"
            "        return self.x\n"
        )
        result = analyzer.analyze_classes(src)
        assert isinstance(result, Ok)
        assert len(result.value) == 1
        cls = result.value[0]
        assert cls == ClassInfo(
            name="Widget",
            file_path=str(src),
            start_line=1,
            end_line=6,
            line_count=6,
        )

    def test_only_classes_not_functions(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "mixed.py"
        src.write_text(
            "def standalone():\n"
            "    pass\n"
            "\n"
            "class Bar:\n"
            "    pass\n"
        )
        result = analyzer.analyze_classes(src)
        assert isinstance(result, Ok)
        assert len(result.value) == 1
        assert result.value[0].name == "Bar"


# ── error handling ──────────────────────────────────────────────────


class TestErrorHandling:
    def test_syntax_error(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "bad.py"
        src.write_text("def broken(\n")
        result = analyzer.analyze_functions(src)
        assert isinstance(result, Err)
        assert "Syntax error" in result.error

    def test_nonexistent_file(self, analyzer: PythonAnalyzer) -> None:
        result = analyzer.analyze_functions(Path("/no/such/file.py"))
        assert isinstance(result, Err)
        assert "Cannot read" in result.error


# ── edge cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_file(
        self, analyzer: PythonAnalyzer, tmp_path: Path,
    ) -> None:
        src = tmp_path / "empty.py"
        src.write_text("")
        funcs = analyzer.analyze_functions(src)
        classes = analyzer.analyze_classes(src)
        assert isinstance(funcs, Ok)
        assert funcs.value == ()
        assert isinstance(classes, Ok)
        assert classes.value == ()
