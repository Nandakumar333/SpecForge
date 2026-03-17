"""Unit tests for ContractChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specforge.core.checkers.contract_checker import ContractChecker
from specforge.core.quality_models import (
    CheckLevel,
    ContractAttribution,
    ErrorCategory,
)


class TestContractCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_microservice(self) -> None:
        checker = ContractChecker()
        assert checker.is_applicable("microservice") is True

    def test_not_applicable_for_monolithic(self) -> None:
        checker = ContractChecker()
        assert checker.is_applicable("monolithic") is False

    def test_not_applicable_for_modular_monolith(self) -> None:
        checker = ContractChecker()
        assert checker.is_applicable("modular-monolith") is False

    def test_name_is_contract(self) -> None:
        checker = ContractChecker()
        assert checker.name == "contract"

    def test_category_is_contract(self) -> None:
        checker = ContractChecker()
        assert checker.category == ErrorCategory.CONTRACT

    def test_levels_is_service(self) -> None:
        checker = ContractChecker()
        assert checker.levels == (CheckLevel.SERVICE,)


class TestContractCheckerExecution:
    """Verify contract test execution and attribution."""

    @patch("specforge.core.checkers.contract_checker.subprocess.run")
    def test_passing_tests(self, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="3 passed", stderr=""
        )
        checker = ContractChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.attribution is None

    @patch("specforge.core.checkers.contract_checker.subprocess.run")
    def test_consumer_failure_has_consumer_attribution(self, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="FAILED consumer test: expected 200 got 500",
            stderr="",
        )
        checker = ContractChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert cr.attribution == ContractAttribution.CONSUMER

    @patch("specforge.core.checkers.contract_checker.subprocess.run")
    def test_provider_failure_has_provider_attribution(self, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="FAILED provider verification: missing field 'id'",
            stderr="",
        )
        checker = ContractChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert cr.attribution == ContractAttribution.PROVIDER

    @patch("specforge.core.checkers.contract_checker.subprocess.run")
    def test_timeout(self, mock_run: object) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=300)
        checker = ContractChecker()
        result = checker.check([], object())
        assert not result.ok
        assert "timed out" in result.error

    @patch("specforge.core.checkers.contract_checker.subprocess.run")
    def test_test_runner_not_found_skips(self, mock_run: object) -> None:
        mock_run.side_effect = FileNotFoundError("pytest not found")
        checker = ContractChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
