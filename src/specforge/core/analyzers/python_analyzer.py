"""Python AST analyzer for function/class line count analysis."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from specforge.core.quality_models import ClassInfo, FunctionInfo
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


class PythonAnalyzer:
    """Analyzes Python files for function/class line counts via AST."""

    def supports_extension(self, ext: str) -> bool:
        """Only .py files are supported."""
        return ext.lower() == ".py"

    def analyze_functions(
        self,
        file_path: Path,
    ) -> Result[tuple[FunctionInfo, ...], str]:
        """Parse file and extract all function definitions with line spans."""
        tree = _parse_file(file_path)
        if not tree.ok:
            return Err(tree.error)

        functions: list[FunctionInfo] = []
        for node in ast.walk(tree.value):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno is None:
                    continue
                line_count = node.end_lineno - node.lineno + 1
                functions.append(
                    FunctionInfo(
                        name=node.name,
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        line_count=line_count,
                    )
                )
        return Ok(tuple(functions))

    def analyze_classes(
        self,
        file_path: Path,
    ) -> Result[tuple[ClassInfo, ...], str]:
        """Parse file and extract all class definitions with line spans."""
        tree = _parse_file(file_path)
        if not tree.ok:
            return Err(tree.error)

        classes: list[ClassInfo] = []
        for node in ast.walk(tree.value):
            if isinstance(node, ast.ClassDef):
                if node.end_lineno is None:
                    continue
                line_count = node.end_lineno - node.lineno + 1
                classes.append(
                    ClassInfo(
                        name=node.name,
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        line_count=line_count,
                    )
                )
        return Ok(tuple(classes))


def _parse_file(file_path: Path) -> Result[ast.Module, str]:
    """Read and parse a Python file, returning AST or error."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        return Ok(tree)
    except SyntaxError as exc:
        return Err(f"Syntax error in {file_path}: {exc}")
    except OSError as exc:
        return Err(f"Cannot read {file_path}: {exc}")
