"""Post-phase contract verification for inter-service consistency."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from specforge.core.orchestrator_models import (
    BoundaryCheckResult,
    ContractCheckResult,
    ContractMismatch,
    VerificationResult,
)
from specforge.core.result import Ok, Result

_FEATURES_REL = Path(".specforge") / "features"
_CONTRACTS_DIR = "contracts"
_CONSUMER_FILE = "consumer-expectations.json"
_MICROSERVICE = "microservice"
_MODULAR_MONOLITH = "modular-monolith"


def _deep_find(data: Any, key: str) -> Any:
    """Recursively search for *key* in a nested dict/list structure."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for v in data.values():
            found = _deep_find(v, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _deep_find(item, key)
            if found is not None:
                return found
    return None


class BoundaryAnalyzer(Protocol):
    """Protocol for pluggable boundary analyzers."""

    def analyze(self, *args: Any, **kwargs: Any) -> list[BoundaryCheckResult]: ...


class ContractEnforcer:
    """Verifies inter-service contracts and boundary isolation."""

    def __init__(
        self,
        project_root: Path,
        boundary_analyzer: BoundaryAnalyzer | None = None,
    ) -> None:
        self._root = project_root
        self._boundary_analyzer = boundary_analyzer

    def verify(
        self,
        implemented_services: tuple[str, ...],
        manifest: dict[str, Any],
        phase: int = 0,
    ) -> Result[VerificationResult, str]:
        """Run contract + boundary checks for implemented services."""
        arch = manifest.get("architecture", "monolithic")
        run_contracts = arch == _MICROSERVICE
        run_boundary = arch in {_MICROSERVICE, _MODULAR_MONOLITH}

        contract_results: list[ContractCheckResult] = []
        if run_contracts:
            contract_results = self._check_all_contracts(
                implemented_services, manifest,
            )

        boundary_results = self._run_boundary_analysis(
            implemented_services, manifest, run_boundary,
        )

        return self._build_verification_result(
            phase, contract_results, boundary_results,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _contracts_path(self, slug: str) -> Path:
        return self._root / _FEATURES_REL / slug / _CONTRACTS_DIR

    def _load_service_contracts(self, slug: str) -> dict[str, Any]:
        """Load all JSON contract files for a service."""
        contracts_dir = self._contracts_path(slug)
        result: dict[str, Any] = {}
        if not contracts_dir.is_dir():
            return result
        for f in contracts_dir.iterdir():
            if f.suffix == ".json" and f.name != _CONSUMER_FILE:
                result[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        return result

    def _find_consumer_expectations(
        self, slug: str,
    ) -> dict[str, Any] | None:
        """Load consumer-expectations.json for a service."""
        path = self._contracts_path(slug) / _CONSUMER_FILE
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _check_all_contracts(
        self,
        implemented_services: tuple[str, ...],
        manifest: dict[str, Any],
    ) -> list[ContractCheckResult]:
        """Check contracts for every consumer→provider pair."""
        results: list[ContractCheckResult] = []
        for slug in implemented_services:
            expectations = self._find_consumer_expectations(slug)
            if expectations is None:
                continue
            results.extend(
                self._check_consumer(slug, expectations, implemented_services),
            )
        return results

    def _check_consumer(
        self,
        consumer: str,
        expectations: dict[str, Any],
        implemented: tuple[str, ...],
    ) -> list[ContractCheckResult]:
        """Check one consumer against all providers it consumes."""
        results: list[ContractCheckResult] = []
        consumes = expectations.get("consumes", {})
        for provider, apis in consumes.items():
            if provider not in implemented:
                continue
            actual_contracts = self._load_service_contracts(provider)
            for api_name, expected in apis.items():
                actual = actual_contracts.get(api_name, {})
                mismatches = self._compare_contracts(
                    consumer, provider, expected, actual,
                )
                passed = len(mismatches) == 0
                results.append(ContractCheckResult(
                    consumer=consumer,
                    provider=provider,
                    passed=passed,
                    mismatches=tuple(mismatches),
                ))
        db_mismatches = self._check_database_isolation(
            consumer, expectations,
        )
        if db_mismatches:
            results.append(ContractCheckResult(
                consumer=consumer,
                provider="database",
                passed=False,
                mismatches=tuple(db_mismatches),
            ))
        return results

    def _compare_contracts(
        self,
        consumer: str,
        provider: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        prefix: str = "",
    ) -> list[ContractMismatch]:
        """Deep-compare expected fields against actual contract."""
        mismatches: list[ContractMismatch] = []
        for key, exp_val in expected.items():
            field = f"{prefix}{key}" if prefix else key
            act_val = actual.get(key)
            if act_val is None:
                act_val = _deep_find(actual, key)
            if isinstance(exp_val, dict) and isinstance(act_val, dict):
                mismatches.extend(self._compare_contracts(
                    consumer, provider, exp_val, act_val, f"{field}.",
                ))
            elif isinstance(exp_val, dict) and act_val is None:
                mismatches.append(ContractMismatch(
                    contract_file=f"{provider}/{key}",
                    field=field,
                    expected=str(exp_val),
                    actual="missing",
                ))
            elif exp_val != act_val and not isinstance(exp_val, dict):
                mismatches.append(ContractMismatch(
                    contract_file=f"{provider}",
                    field=field,
                    expected=str(exp_val),
                    actual=str(act_val),
                ))
        return mismatches

    def _check_database_isolation(
        self,
        slug: str,
        expectations: dict[str, Any],
    ) -> list[ContractMismatch]:
        """Check for cross-service database access violations."""
        db_refs = expectations.get("database_refs", {})
        mismatches: list[ContractMismatch] = []
        for schema, access_type in db_refs.items():
            if access_type == "direct_access":
                mismatches.append(ContractMismatch(
                    contract_file=f"{slug}/{_CONSUMER_FILE}",
                    field="database_refs",
                    expected="no_direct_access",
                    actual=f"{schema}:{access_type}",
                    severity="error",
                ))
        return mismatches

    def _run_boundary_analysis(
        self,
        implemented_services: tuple[str, ...],
        manifest: dict[str, Any],
        run_boundary: bool,
    ) -> list[BoundaryCheckResult]:
        """Delegate to boundary analyzer if provided."""
        if not run_boundary and self._boundary_analyzer is None:
            return []
        if self._boundary_analyzer is None:
            return []
        return list(self._boundary_analyzer.analyze(
            implemented_services, manifest,
        ))

    def _build_verification_result(
        self,
        phase: int,
        contract_results: list[ContractCheckResult],
        boundary_results: list[BoundaryCheckResult],
    ) -> Result[VerificationResult, str]:
        """Assemble the final VerificationResult."""
        contracts_ok = all(cr.passed for cr in contract_results)
        boundaries_ok = len(boundary_results) == 0
        passed = contracts_ok and boundaries_ok
        return Ok(VerificationResult(
            after_phase=phase,
            passed=passed,
            contract_results=tuple(contract_results),
            boundary_results=tuple(boundary_results),
        ))
