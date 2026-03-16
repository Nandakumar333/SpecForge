"""Unit tests for ServiceContext and target resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specforge.core.service_context import (
    FeatureInfo,
    ServiceContext,
    load_service_context,
    resolve_target,
)


def _microservice_manifest() -> dict:
    """Mock manifest with microservice architecture."""
    return {
        "schema_version": "1.0",
        "architecture": "microservice",
        "project_description": "Personal finance tracker",
        "domain": "finance",
        "features": [
            {
                "id": "001",
                "name": "auth",
                "display_name": "Authentication",
                "description": "User login and sessions",
                "priority": "P0",
                "category": "foundation",
                "service": "identity-service",
            },
            {
                "id": "002",
                "name": "accounts",
                "display_name": "Account Management",
                "description": "Bank account tracking",
                "priority": "P1",
                "category": "core",
                "service": "ledger-service",
            },
            {
                "id": "003",
                "name": "transactions",
                "display_name": "Transaction Processing",
                "description": "Income and expense tracking",
                "priority": "P1",
                "category": "core",
                "service": "ledger-service",
            },
        ],
        "services": [
            {
                "name": "Identity Service",
                "slug": "identity-service",
                "features": ["001"],
                "rationale": "Auth isolation",
                "communication": [],
            },
            {
                "name": "Ledger Service",
                "slug": "ledger-service",
                "features": ["002", "003"],
                "rationale": "Financial data",
                "communication": [
                    {
                        "target": "identity-service",
                        "pattern": "sync-rest",
                        "required": True,
                        "description": "User auth validation",
                    }
                ],
            },
        ],
        "events": [
            {
                "name": "transaction.created",
                "producer": "ledger-service",
                "consumers": ["identity-service"],
                "payload_summary": "Transaction details",
            }
        ],
    }


def _monolith_manifest() -> dict:
    """Mock manifest with monolithic architecture."""
    manifest = _microservice_manifest()
    manifest["architecture"] = "monolithic"
    return manifest


def _modular_monolith_manifest() -> dict:
    """Mock manifest with modular-monolith architecture."""
    manifest = _microservice_manifest()
    manifest["architecture"] = "modular-monolith"
    return manifest


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    """Write manifest.json to tmp_path/.specforge/."""
    manifest_dir = tmp_path / ".specforge"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


class TestServiceContext:
    """Tests for ServiceContext dataclass."""

    def test_frozen(self) -> None:
        ctx = ServiceContext(
            service_slug="test",
            service_name="Test",
            architecture="monolithic",
            project_description="A test",
            domain="test",
            features=(),
            dependencies=(),
            events=(),
            output_dir=Path(".specforge/features/test"),
        )
        with pytest.raises(AttributeError):
            ctx.service_slug = "changed"  # type: ignore[misc]


class TestFeatureInfo:
    """Tests for FeatureInfo dataclass."""

    def test_construction(self) -> None:
        f = FeatureInfo(
            id="001",
            name="auth",
            display_name="Authentication",
            description="Login",
            priority="P0",
            category="foundation",
        )
        assert f.id == "001"
        assert f.category == "foundation"


class TestLoadServiceContext:
    """Tests for load_service_context()."""

    def test_load_microservice_by_slug(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        ctx = result.value
        assert ctx.service_slug == "ledger-service"
        assert ctx.service_name == "Ledger Service"
        assert ctx.architecture == "microservice"
        assert len(ctx.features) == 2
        assert ctx.features[0].id == "002"
        assert ctx.features[1].id == "003"

    def test_load_dependencies(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        ctx = result.value
        assert len(ctx.dependencies) == 1
        assert ctx.dependencies[0].target_slug == "identity-service"
        assert ctx.dependencies[0].pattern == "sync-rest"

    def test_load_events(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        ctx = result.value
        assert len(ctx.events) == 1
        assert ctx.events[0].name == "transaction.created"

    def test_load_single_feature_service(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("identity-service", tmp_path)
        assert result.ok
        ctx = result.value
        assert len(ctx.features) == 1
        assert ctx.features[0].id == "001"

    def test_load_monolith(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _monolith_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        assert result.value.architecture == "monolithic"

    def test_load_modular_monolith(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _modular_monolith_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        assert result.value.architecture == "modular-monolith"

    def test_error_missing_manifest(self, tmp_path: Path) -> None:
        result = load_service_context("ledger-service", tmp_path)
        assert not result.ok
        assert "manifest.json" in result.error

    def test_error_unknown_service(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("unknown-service", tmp_path)
        assert not result.ok
        assert "not found" in result.error

    def test_output_dir_set(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = load_service_context("ledger-service", tmp_path)
        assert result.ok
        expected = tmp_path / ".specforge" / "features" / "ledger-service"
        assert result.value.output_dir == expected


class TestResolveTarget:
    """Tests for resolve_target() — slug and feature number."""

    def test_resolve_by_slug(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = resolve_target("ledger-service", tmp_path)
        assert result.ok
        assert result.value == "ledger-service"

    def test_resolve_by_feature_number(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = resolve_target("002", tmp_path)
        assert result.ok
        assert result.value == "ledger-service"

    def test_resolve_by_feature_number_single(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = resolve_target("001", tmp_path)
        assert result.ok
        assert result.value == "identity-service"

    def test_error_unknown_target(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _microservice_manifest())
        result = resolve_target("nonexistent", tmp_path)
        assert not result.ok

    def test_error_missing_manifest(self, tmp_path: Path) -> None:
        result = resolve_target("ledger-service", tmp_path)
        assert not result.ok
