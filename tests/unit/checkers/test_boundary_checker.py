"""Unit tests for BoundaryChecker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specforge.core.checkers.boundary_checker import BoundaryChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestBoundaryCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_modular_monolith(self) -> None:
        checker = BoundaryChecker()
        assert checker.is_applicable("modular-monolith") is True

    def test_not_applicable_for_microservice(self) -> None:
        checker = BoundaryChecker()
        assert checker.is_applicable("microservice") is False

    def test_not_applicable_for_monolithic(self) -> None:
        checker = BoundaryChecker()
        assert checker.is_applicable("monolithic") is False

    def test_name_is_boundary(self) -> None:
        checker = BoundaryChecker()
        assert checker.name == "boundary"

    def test_category_is_boundary(self) -> None:
        checker = BoundaryChecker()
        assert checker.category == ErrorCategory.BOUNDARY

    def test_levels_is_task(self) -> None:
        checker = BoundaryChecker()
        assert checker.levels == (CheckLevel.TASK,)


class TestBoundaryCheckerExecution:
    """Verify cross-module import detection."""

    def test_cross_module_import_detected(self, tmp_path: Path) -> None:
        """A file in module_a importing from module_b should be flagged."""
        src = tmp_path / "src"
        mod_a = src / "module_a"
        mod_b = src / "module_b"
        mod_a.mkdir(parents=True)
        mod_b.mkdir(parents=True)

        file_a = mod_a / "service.py"
        file_a.write_text("from module_b.internal import helper\n")

        checker = BoundaryChecker()
        result = checker.check([file_a], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0
        assert "Cross-module import" in cr.error_details[0].message

    def test_clean_import_passes(self, tmp_path: Path) -> None:
        """A file in module_a importing from module_a should pass."""
        src = tmp_path / "src"
        mod_a = src / "module_a"
        mod_a.mkdir(parents=True)

        file_a = mod_a / "service.py"
        file_a.write_text("from module_a.models import User\n")

        checker = BoundaryChecker()
        result = checker.check([file_a], object())
        assert result.ok
        cr = result.value
        assert cr.passed is True

    def test_public_api_import_allowed(self, tmp_path: Path) -> None:
        """Imports through public API should not be flagged."""
        src = tmp_path / "src"
        mod_a = src / "module_a"
        mod_a.mkdir(parents=True)

        file_a = mod_a / "service.py"
        file_a.write_text("from module_b.api import public_func\n")

        class Ctx:
            module_boundaries = {"module_b": ["module_b.api"]}

        checker = BoundaryChecker()
        result = checker.check([file_a], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is True

    def test_no_imports_passes(self, tmp_path: Path) -> None:
        """A file with no imports should pass cleanly."""
        src = tmp_path / "src"
        mod_a = src / "module_a"
        mod_a.mkdir(parents=True)

        file_a = mod_a / "utils.py"
        file_a.write_text("x = 42\n")

        checker = BoundaryChecker()
        result = checker.check([file_a], object())
        assert result.ok
        assert result.value.passed is True
