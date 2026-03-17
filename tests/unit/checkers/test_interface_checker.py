"""Unit tests for InterfaceChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specforge.core.checkers.interface_checker import InterfaceChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestInterfaceCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_microservice(self) -> None:
        checker = InterfaceChecker()
        assert checker.is_applicable("microservice") is True

    def test_not_applicable_for_monolithic(self) -> None:
        checker = InterfaceChecker()
        assert checker.is_applicable("monolithic") is False

    def test_not_applicable_for_modular_monolith(self) -> None:
        checker = InterfaceChecker()
        assert checker.is_applicable("modular-monolith") is False

    def test_name_is_interface(self) -> None:
        checker = InterfaceChecker()
        assert checker.name == "interface"

    def test_category_is_contract(self) -> None:
        checker = InterfaceChecker()
        assert checker.category == ErrorCategory.CONTRACT

    def test_levels_is_service(self) -> None:
        checker = InterfaceChecker()
        assert checker.levels == (CheckLevel.SERVICE,)


class TestInterfaceCheckerSkip:
    """Verify skip conditions."""

    def test_skip_if_no_proto_files(self, tmp_path: Path) -> None:
        """Should skip gracefully when no .proto files exist."""

        class Ctx:
            project_root = str(tmp_path)

        checker = InterfaceChecker()
        result = checker.check([], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
        assert "No .proto files found" in cr.skip_reason

    @patch("specforge.core.checkers.interface_checker.shutil.which", return_value=None)
    def test_skip_if_protoc_not_available(self, mock_which: object, tmp_path: Path) -> None:
        """Should skip when protoc is not installed."""
        proto_file = tmp_path / "service.proto"
        proto_file.write_text('syntax = "proto3";\n')

        class Ctx:
            project_root = str(tmp_path)

        checker = InterfaceChecker()
        result = checker.check([], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
        assert "protoc not available" in cr.skip_reason


class TestInterfaceCheckerExecution:
    """Verify protoc execution."""

    @patch("specforge.core.checkers.interface_checker.subprocess.run")
    @patch("specforge.core.checkers.interface_checker.shutil.which", return_value="/usr/bin/protoc")
    def test_proto_compilation_success(self, mock_which: object, mock_run: object, tmp_path: Path) -> None:
        proto_file = tmp_path / "service.proto"
        proto_file.write_text('syntax = "proto3";\n')

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        class Ctx:
            project_root = str(tmp_path)

        checker = InterfaceChecker()
        result = checker.check([], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is False

    @patch("specforge.core.checkers.interface_checker.subprocess.run")
    @patch("specforge.core.checkers.interface_checker.shutil.which", return_value="/usr/bin/protoc")
    def test_proto_compilation_failure(self, mock_which: object, mock_run: object, tmp_path: Path) -> None:
        proto_file = tmp_path / "broken.proto"
        proto_file.write_text("invalid proto content\n")

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="broken.proto:1:1: Expected syntax statement."
        )

        class Ctx:
            project_root = str(tmp_path)

        checker = InterfaceChecker()
        result = checker.check([], Ctx())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0
