"""Language analyzer protocol for code structure analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from specforge.core.quality_models import ClassInfo, FunctionInfo
    from specforge.core.result import Result


class LanguageAnalyzerProtocol(Protocol):
    """Pluggable interface for language-specific code analysis."""

    def analyze_functions(
        self,
        file_path: Path,
    ) -> Result[tuple[FunctionInfo, ...], str]: ...

    def analyze_classes(
        self,
        file_path: Path,
    ) -> Result[tuple[ClassInfo, ...], str]: ...

    def supports_extension(self, ext: str) -> bool: ...
