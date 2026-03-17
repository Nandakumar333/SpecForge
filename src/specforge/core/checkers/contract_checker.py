"""Contract/Pact test checker for microservice architectures."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ContractAttribution,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

if TYPE_CHECKING:
    from pathlib import Path

_CONSUMER_KEYWORDS: tuple[str, ...] = (
    "consumer",
    "consumer test",
    "pact consumer",
    "consumer verification",
)

_PROVIDER_KEYWORDS: tuple[str, ...] = (
    "provider",
    "provider test",
    "pact provider",
    "provider verification",
)


class ContractChecker:
    """Runs contract/Pact tests and attributes failures."""

    @property
    def name(self) -> str:
        return "contract"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.CONTRACT

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.SERVICE,)

    def is_applicable(self, architecture: str) -> bool:
        return architecture == "microservice"

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Run contract tests and attribute failures."""
        cmd = self._get_command(service_context)
        return self._run_tests(cmd)

    def _get_command(self, ctx: object) -> list[str]:
        """Get contract test command from context or use default."""
        cmd = getattr(ctx, "contract_test_command", None)
        if cmd:
            return cmd if isinstance(cmd, list) else [cmd]
        return ["python", "-m", "pytest", "tests/contract/", "-v"]

    def _run_tests(
        self, cmd: list[str]
    ) -> Ok[CheckResult] | Err[str]:
        """Execute contract test suite."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return Err("Contract tests timed out")
        except FileNotFoundError:
            return Ok(self._skipped("Test runner not available"))

        if result.returncode == 0:
            return Ok(self._passed(result.stdout))

        combined = result.stdout + result.stderr
        attribution = _determine_attribution(combined)
        errors = _parse_contract_errors(combined)
        return Ok(self._failed(combined, errors, attribution))

    def _skipped(self, reason: str) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=True,
            category=self.category,
            skipped=True,
            skip_reason=reason,
        )

    def _passed(self, output: str) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=True,
            category=self.category,
            output=output,
        )

    def _failed(
        self,
        output: str,
        errors: tuple[ErrorDetail, ...],
        attribution: ContractAttribution | None,
    ) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=False,
            category=self.category,
            output=output,
            error_details=errors,
            attribution=attribution,
        )


def _determine_attribution(
    output: str,
) -> ContractAttribution | None:
    """Determine consumer vs provider attribution from output."""
    lower = output.lower()
    has_consumer = any(kw in lower for kw in _CONSUMER_KEYWORDS)
    has_provider = any(kw in lower for kw in _PROVIDER_KEYWORDS)

    if has_consumer and not has_provider:
        return ContractAttribution.CONSUMER
    if has_provider and not has_consumer:
        return ContractAttribution.PROVIDER
    return None


def _parse_contract_errors(output: str) -> tuple[ErrorDetail, ...]:
    """Extract error details from contract test output."""
    errors: list[ErrorDetail] = []
    for line in output.splitlines():
        stripped = line.strip()
        if "FAILED" in stripped or "Error" in stripped:
            errors.append(
                ErrorDetail(file_path="contract", message=stripped)
            )
    return tuple(errors) if errors else (
        ErrorDetail(file_path="contract", message="Contract test failed"),
    )
