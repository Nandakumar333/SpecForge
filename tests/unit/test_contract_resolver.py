"""Unit tests for contract_resolver.py — dependency contract loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specforge.core.service_context import ServiceDependency


def _make_dep(slug: str, name: str = "") -> ServiceDependency:
    """Helper to create a ServiceDependency."""
    return ServiceDependency(
        target_slug=slug,
        target_name=name or slug,
        pattern="sync-rest",
        required=True,
        description=f"Depends on {slug}",
    )


class TestContractResolverResolve:
    """ContractResolver.resolve() loads contracts from dependent services."""

    def test_single_dependency_loads_contracts(self, tmp_path: Path) -> None:
        from specforge.core.contract_resolver import ContractResolver

        # Set up identity-service contracts
        contracts_dir = tmp_path / ".specforge" / "features" / "identity-service" / "contracts"
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "api-spec.json").write_text(
            json.dumps({"endpoint": "/auth"}), encoding="utf-8",
        )
        (contracts_dir / "events.json").write_text(
            json.dumps({"event": "UserCreated"}), encoding="utf-8",
        )

        resolver = ContractResolver(tmp_path)
        deps = (_make_dep("identity-service"),)
        result = resolver.resolve(deps)

        assert result.ok
        contracts = result.value
        assert "identity-service" in contracts
        assert "/auth" in contracts["identity-service"]
        assert "UserCreated" in contracts["identity-service"]

    def test_missing_contracts_dir_warns_but_ok(self, tmp_path: Path) -> None:
        from specforge.core.contract_resolver import ContractResolver

        # No contracts directory exists for the dependency
        resolver = ContractResolver(tmp_path)
        deps = (_make_dep("missing-service"),)
        result = resolver.resolve(deps)

        assert result.ok
        contracts = result.value
        assert contracts == {} or "missing-service" not in contracts

    def test_empty_dependencies_returns_empty(self, tmp_path: Path) -> None:
        from specforge.core.contract_resolver import ContractResolver

        resolver = ContractResolver(tmp_path)
        result = resolver.resolve(())

        assert result.ok
        assert result.value == {}

    def test_multiple_dependencies_merges(self, tmp_path: Path) -> None:
        from specforge.core.contract_resolver import ContractResolver

        # Set up two dependency services
        for slug in ("identity-service", "payment-service"):
            contracts_dir = tmp_path / ".specforge" / "features" / slug / "contracts"
            contracts_dir.mkdir(parents=True)
            (contracts_dir / "api-spec.json").write_text(
                json.dumps({"service": slug}), encoding="utf-8",
            )

        resolver = ContractResolver(tmp_path)
        deps = (_make_dep("identity-service"), _make_dep("payment-service"))
        result = resolver.resolve(deps)

        assert result.ok
        contracts = result.value
        assert "identity-service" in contracts
        assert "payment-service" in contracts

    def test_never_accesses_non_dependent_services(self, tmp_path: Path) -> None:
        from specforge.core.contract_resolver import ContractResolver

        # Create contracts for BOTH identity and planning services
        for slug in ("identity-service", "planning-service"):
            contracts_dir = tmp_path / ".specforge" / "features" / slug / "contracts"
            contracts_dir.mkdir(parents=True)
            (contracts_dir / "api-spec.json").write_text(
                json.dumps({"service": slug}), encoding="utf-8",
            )

        # Only depend on identity-service
        resolver = ContractResolver(tmp_path)
        deps = (_make_dep("identity-service"),)
        result = resolver.resolve(deps)

        assert result.ok
        contracts = result.value
        assert "identity-service" in contracts
        assert "planning-service" not in contracts
