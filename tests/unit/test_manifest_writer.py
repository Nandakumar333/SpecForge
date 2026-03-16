"""Unit tests for ManifestWriter (UT-010, UT-011)."""

from __future__ import annotations

import json
from pathlib import Path

from specforge.core.manifest_writer import ManifestWriter


class TestAtomicWrite:
    """UT-010: atomic write (temp + fsync + rename)."""

    def test_write_creates_valid_json(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        manifest = _minimal_manifest()
        path = tmp_path / "manifest.json"
        result = writer.write(path, manifest)
        assert result.ok
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "nested" / "dir" / "manifest.json"
        result = writer.write(path, _minimal_manifest())
        assert result.ok
        assert path.exists()

    def test_write_overwrites_existing(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        writer.write(path, _minimal_manifest())
        m2 = _minimal_manifest()
        m2["domain"] = "updated"
        writer.write(path, m2)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["domain"] == "updated"


class TestPostWriteValidation:
    """UT-011: post-write validation catches errors."""

    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        writer.write(path, _minimal_manifest())
        result = writer.validate(path)
        assert result.ok

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        path.write_text("not json{{{", encoding="utf-8")
        result = writer.validate(path)
        assert not result.ok

    def test_missing_schema_version_fails(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        m = _minimal_manifest()
        del m["schema_version"]
        path.write_text(json.dumps(m), encoding="utf-8")
        result = writer.validate(path)
        assert not result.ok

    def test_duplicate_feature_id_fails(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        m = _minimal_manifest()
        m["features"].append(m["features"][0].copy())
        path.write_text(json.dumps(m), encoding="utf-8")
        result = writer.validate(path)
        assert not result.ok

    def test_feature_references_unknown_service(self, tmp_path: Path) -> None:
        writer = ManifestWriter()
        path = tmp_path / "manifest.json"
        m = _minimal_manifest()
        m["features"][0]["service"] = "nonexistent"
        path.write_text(json.dumps(m), encoding="utf-8")
        result = writer.validate(path)
        assert not result.ok


class TestBuildManifest:
    """Test manifest construction from domain objects."""

    def test_build_produces_valid_structure(self) -> None:
        from specforge.core.domain_analyzer import Feature

        writer = ManifestWriter()
        feat = Feature(
            id="001", name="auth", display_name="Auth",
            description="test", priority="P0", category="foundation",
            always_separate=True, data_keywords=("user",),
        )
        from specforge.core.service_mapper import Service

        svc = Service(
            name="Auth Service", slug="auth-service",
            feature_ids=("001",), rationale="test", communication=(),
        )
        manifest = writer.build_manifest(
            arch="microservice", domain="finance",
            features=[feat], services=[svc],
            events=[], description="test app",
        )
        assert manifest["schema_version"] == "1.0"
        assert manifest["architecture"] == "microservice"
        assert len(manifest["features"]) == 1
        assert len(manifest["services"]) == 1


def _minimal_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "architecture": "monolithic",
        "project_description": "test",
        "domain": "generic",
        "features": [
            {
                "id": "001",
                "name": "auth",
                "display_name": "Auth",
                "description": "test",
                "priority": "P0",
                "category": "foundation",
                "service": "application",
            }
        ],
        "services": [
            {
                "name": "Application",
                "slug": "application",
                "features": ["001"],
                "rationale": "Monolithic",
                "communication": [],
            }
        ],
        "events": [],
    }
