"""Unit tests for contract_enforcer.py — post-phase contract verification."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specforge.core.contract_enforcer import ContractEnforcer
from specforge.core.orchestrator_models import (
    BoundaryCheckResult,
)


@pytest.fixture()
def contract_tree(tmp_path: Path) -> Path:
    """Create a contract directory structure for testing."""
    features = tmp_path / ".specforge" / "features"

    # identity-service publishes auth-api contract
    identity_contracts = features / "identity-service" / "contracts"
    identity_contracts.mkdir(parents=True)
    (identity_contracts / "auth-api.json").write_text(json.dumps({
        "endpoints": [{
            "path": "/auth/token",
            "response": {
                "claims": {
                    "role": {"type": "string", "enum": ["admin", "user", "readonly"]},
                },
            },
        }],
    }))

    # ledger-service has its own contract + consumer expectations
    ledger_contracts = features / "ledger-service" / "contracts"
    ledger_contracts.mkdir(parents=True)
    (ledger_contracts / "ledger-api.json").write_text(json.dumps({
        "endpoints": [{"path": "/ledger/entries", "auth": "jwt"}],
    }))
    (ledger_contracts / "consumer-expectations.json").write_text(json.dumps({
        "consumes": {
            "identity-service": {
                "auth-api": {
                    "claims": {
                        "role": {"type": "string", "enum": ["admin", "user", "readonly"]},
                    },
                },
            },
        },
    }))

    # portfolio-service has consumer expectations for identity
    portfolio_contracts = features / "portfolio-service" / "contracts"
    portfolio_contracts.mkdir(parents=True)
    (portfolio_contracts / "consumer-expectations.json").write_text(json.dumps({
        "consumes": {
            "identity-service": {
                "auth-api": {
                    "claims": {
                        "role": {"type": "string", "enum": ["admin", "user", "readonly"]},
                    },
                },
            },
        },
    }))

    return tmp_path


@pytest.fixture()
def manifest() -> dict:
    return {
        "architecture": "microservice",
        "services": [
            {"slug": "identity-service", "communication": []},
            {"slug": "ledger-service", "communication": [{"target": "identity-service"}]},
            {"slug": "portfolio-service", "communication": [{"target": "identity-service"}]},
        ],
    }


class TestContractEnforcer:
    def test_verify_passing_contracts(
        self, contract_tree: Path, manifest: dict,
    ) -> None:
        enforcer = ContractEnforcer(project_root=contract_tree)
        result = enforcer.verify(
            implemented_services=("identity-service", "ledger-service"),
            manifest=manifest,
        )
        assert result.ok
        assert result.value.passed is True

    def test_verify_contract_mismatch_detected(
        self, contract_tree: Path, manifest: dict,
    ) -> None:
        # Modify identity's contract to remove enum (breaking change)
        identity_contract = (
            contract_tree / ".specforge" / "features"
            / "identity-service" / "contracts" / "auth-api.json"
        )
        identity_contract.write_text(json.dumps({
            "endpoints": [{
                "path": "/auth/token",
                "response": {
                    "claims": {
                        "role": {"type": "string"},  # No enum!
                    },
                },
            }],
        }))

        enforcer = ContractEnforcer(project_root=contract_tree)
        result = enforcer.verify(
            implemented_services=("identity-service", "ledger-service"),
            manifest=manifest,
        )
        assert result.ok
        vr = result.value
        assert vr.passed is False
        assert len(vr.contract_results) > 0
        failed = [cr for cr in vr.contract_results if not cr.passed]
        assert len(failed) > 0
        mismatch = failed[0].mismatches[0]
        assert "role" in mismatch.field

    def test_verify_multiple_mismatches_all_reported(
        self, contract_tree: Path, manifest: dict,
    ) -> None:
        # Break identity contract
        identity_contract = (
            contract_tree / ".specforge" / "features"
            / "identity-service" / "contracts" / "auth-api.json"
        )
        identity_contract.write_text(json.dumps({
            "endpoints": [{
                "path": "/auth/token",
                "response": {"claims": {"role": {"type": "string"}}},
            }],
        }))

        enforcer = ContractEnforcer(project_root=contract_tree)
        result = enforcer.verify(
            implemented_services=(
                "identity-service", "ledger-service", "portfolio-service",
            ),
            manifest=manifest,
        )
        assert result.ok
        vr = result.value
        assert vr.passed is False
        # Both ledger and portfolio should detect mismatch with identity
        failed = [cr for cr in vr.contract_results if not cr.passed]
        consumers = {cr.consumer for cr in failed}
        assert "ledger-service" in consumers
        assert "portfolio-service" in consumers

    def test_verify_cumulative_scope(
        self, contract_tree: Path, manifest: dict,
    ) -> None:
        enforcer = ContractEnforcer(project_root=contract_tree)
        result = enforcer.verify(
            implemented_services=(
                "identity-service", "ledger-service", "portfolio-service",
            ),
            manifest=manifest,
        )
        assert result.ok
        # Should check all pairs, not just within latest phase
        assert result.value.passed is True

    def test_verify_no_contracts_dir_is_warning(
        self, tmp_path: Path, manifest: dict,
    ) -> None:
        features = tmp_path / ".specforge" / "features"
        (features / "identity-service").mkdir(parents=True)
        # No contracts dir

        enforcer = ContractEnforcer(project_root=tmp_path)
        result = enforcer.verify(
            implemented_services=("identity-service",),
            manifest=manifest,
        )
        assert result.ok
        assert result.value.passed is True  # Warning, not failure

    def test_verify_boundary_analysis_runs(
        self, contract_tree: Path, manifest: dict,
    ) -> None:
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []

        enforcer = ContractEnforcer(
            project_root=contract_tree, boundary_analyzer=mock_analyzer,
        )
        enforcer.verify(
            implemented_services=("identity-service", "ledger-service"),
            manifest=manifest,
        )
        mock_analyzer.analyze.assert_called_once()

    def test_verify_monolith_skips_contracts(
        self, contract_tree: Path,
    ) -> None:
        monolith_manifest = {
            "architecture": "monolithic",
            "services": [{"slug": "identity-service", "communication": []}],
        }
        enforcer = ContractEnforcer(project_root=contract_tree)
        result = enforcer.verify(
            implemented_services=("identity-service",),
            manifest=monolith_manifest,
        )
        assert result.ok
        assert result.value.passed is True
        assert result.value.contract_results == ()

    def test_verify_modular_monolith_boundary_checks(
        self, contract_tree: Path,
    ) -> None:
        mod_manifest = {
            "architecture": "modular-monolith",
            "services": [
                {"slug": "identity-service", "communication": []},
                {"slug": "ledger-service", "communication": [{"target": "identity-service"}]},
            ],
        }
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []

        enforcer = ContractEnforcer(
            project_root=contract_tree, boundary_analyzer=mock_analyzer,
        )
        result = enforcer.verify(
            implemented_services=("identity-service", "ledger-service"),
            manifest=mod_manifest,
        )
        assert result.ok
        assert result.value.contract_results == ()  # No contract checks
        mock_analyzer.analyze.assert_called_once()  # But boundary runs

    def test_cross_service_db_access_detected(
        self, tmp_path: Path,
    ) -> None:
        features = tmp_path / ".specforge" / "features"
        svc_a = features / "service-a" / "contracts"
        svc_a.mkdir(parents=True)
        (svc_a / "service-a-api.json").write_text(json.dumps({
            "database": {"schema": "service_a_schema"},
        }))

        svc_b = features / "service-b" / "contracts"
        svc_b.mkdir(parents=True)
        (svc_b / "consumer-expectations.json").write_text(json.dumps({
            "consumes": {
                "service-a": {
                    "service-a-api": {
                        "database": {"schema": "service_a_schema"},
                    },
                },
            },
            "database_refs": {"service_a_schema": "direct_access"},
        }))

        manifest = {
            "architecture": "microservice",
            "services": [
                {"slug": "service-a", "communication": []},
                {"slug": "service-b", "communication": [{"target": "service-a"}]},
            ],
        }

        enforcer = ContractEnforcer(project_root=tmp_path)
        result = enforcer.verify(
            implemented_services=("service-a", "service-b"),
            manifest=manifest,
        )
        assert result.ok
        vr = result.value
        assert vr.passed is False

    def test_cross_module_schema_violation_monolith(
        self, tmp_path: Path,
    ) -> None:
        features = tmp_path / ".specforge" / "features"
        mod_a = features / "module-a" / "contracts"
        mod_a.mkdir(parents=True)
        (mod_a / "module-a-api.json").write_text(json.dumps({
            "database": {"schema": "module_a_schema"},
        }))

        mod_b = features / "module-b" / "contracts"
        mod_b.mkdir(parents=True)
        (mod_b / "consumer-expectations.json").write_text(json.dumps({
            "consumes": {},
            "database_refs": {"module_a_schema": "direct_access"},
        }))

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = [
            BoundaryCheckResult(
                entity="module_a_schema",
                services=("module-a", "module-b"),
                violation_type="direct_access",
                details="module-b accesses module-a's schema directly",
            ),
        ]

        manifest = {
            "architecture": "modular-monolith",
            "services": [
                {"slug": "module-a", "communication": []},
                {"slug": "module-b", "communication": []},
            ],
        }

        enforcer = ContractEnforcer(
            project_root=tmp_path, boundary_analyzer=mock_analyzer,
        )
        result = enforcer.verify(
            implemented_services=("module-a", "module-b"),
            manifest=manifest,
        )
        assert result.ok
        vr = result.value
        assert vr.passed is False
        assert len(vr.boundary_results) > 0
