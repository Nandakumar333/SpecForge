"""Unit tests for MigrationChecker."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.checkers.migration_checker import MigrationChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestMigrationCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_modular_monolith(self) -> None:
        checker = MigrationChecker()
        assert checker.is_applicable("modular-monolith") is True

    def test_not_applicable_for_microservice(self) -> None:
        checker = MigrationChecker()
        assert checker.is_applicable("microservice") is False

    def test_not_applicable_for_monolithic(self) -> None:
        checker = MigrationChecker()
        assert checker.is_applicable("monolithic") is False

    def test_name_is_migration(self) -> None:
        checker = MigrationChecker()
        assert checker.name == "migration"

    def test_category_is_boundary(self) -> None:
        checker = MigrationChecker()
        assert checker.category == ErrorCategory.BOUNDARY

    def test_levels_is_task(self) -> None:
        checker = MigrationChecker()
        assert checker.levels == (CheckLevel.TASK,)


class TestMigrationCheckerExecution:
    """Verify cross-module table access detection."""

    def test_cross_module_table_access_detected(self, tmp_path: Path) -> None:
        """Migration in module_a accessing module_b's table should be flagged."""
        src = tmp_path / "src"
        mod_a = src / "module_a" / "migrations"
        mod_a.mkdir(parents=True)

        migration = mod_a / "001_migration.py"
        migration.write_text(
            'op.execute("INSERT INTO orders (id) VALUES (1)")\n'
        )

        class Ctx:
            table_boundaries = {"orders": "module_b"}

        checker = MigrationChecker()
        result = checker.check([migration], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0
        assert "Cross-module table access" in cr.error_details[0].message
        assert "orders" in cr.error_details[0].message

    def test_own_module_migration_passes(self, tmp_path: Path) -> None:
        """Migration in module_a accessing module_a's own table should pass."""
        src = tmp_path / "src"
        mod_a = src / "module_a" / "migrations"
        mod_a.mkdir(parents=True)

        migration = mod_a / "001_migration.py"
        migration.write_text(
            'op.execute("CREATE TABLE users (id INT PRIMARY KEY)")\n'
        )

        class Ctx:
            table_boundaries = {"users": "module_a"}

        checker = MigrationChecker()
        result = checker.check([migration], Ctx())
        assert result.ok
        assert result.value.passed is True

    def test_no_migration_files_passes(self) -> None:
        """Non-migration files should be ignored."""
        checker = MigrationChecker()
        files = [Path("src/module_a/service.py")]
        result = checker.check(files, object())
        assert result.ok
        assert result.value.passed is True

    def test_migration_with_no_boundaries_passes(self, tmp_path: Path) -> None:
        """Without boundary definitions, no violations can be detected."""
        src = tmp_path / "src"
        mod_a = src / "module_a" / "migrations"
        mod_a.mkdir(parents=True)

        migration = mod_a / "001_migration.py"
        migration.write_text(
            'op.execute("INSERT INTO orders (id) VALUES (1)")\n'
        )

        checker = MigrationChecker()
        result = checker.check([migration], object())
        assert result.ok
        assert result.value.passed is True
