"""Manifest JSON generation, atomic write, and post-write validation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from specforge.core.config import SCHEMA_VERSION, VALID_ARCHITECTURES
from specforge.core.result import Err, Ok, Result


class ManifestWriter:
    """Builds, writes, and validates manifest.json."""

    def build_manifest(
        self,
        arch: str,
        domain: str,
        features: list,
        services: list,
        events: list,
        description: str,
    ) -> dict[str, Any]:
        """Build manifest dict from domain objects."""
        svc_slug_map = _build_service_slug_map(features, services)
        return {
            "schema_version": SCHEMA_VERSION,
            "architecture": arch,
            "project_description": description,
            "domain": domain,
            "features": [
                _feature_to_dict(f, svc_slug_map) for f in features
            ],
            "services": [_service_to_dict(s) for s in services],
            "events": [_event_to_dict(e) for e in events],
        }

    def write(self, path: Path, manifest: dict) -> Result:
        """Write manifest atomically to disk."""
        return _atomic_write_json(path, manifest)

    def validate(self, path: Path) -> Result:
        """Validate a written manifest file (FR-053)."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            return Err(f"Cannot read manifest: {exc}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return Err("manifest.json is not valid JSON")
        return _validate_manifest(data)


def _validate_manifest(data: dict) -> Result:
    """Run all 10 validation rules on manifest data."""
    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        return Err(f"Missing or invalid schema_version: {sv}")
    arch = data.get("architecture")
    if arch not in VALID_ARCHITECTURES:
        return Err(f"Invalid architecture value: '{arch}'")
    return _validate_references(data)


def _validate_references(data: dict) -> Result:
    """Validate feature IDs, service refs, and cross-references."""
    features = data.get("features", [])
    services = data.get("services", [])
    service_slugs = {s["slug"] for s in services}

    seen_ids: set[str] = set()
    for f in features:
        fid = f["id"]
        if fid in seen_ids:
            return Err(f"Duplicate feature ID: '{fid}'")
        seen_ids.add(fid)
        svc_ref = f.get("service", "")
        if svc_ref and svc_ref not in service_slugs:
            return Err(
                f"Feature '{fid}' references unknown service '{svc_ref}'"
            )

    svc_feat_ids: dict[str, list[str]] = {}
    for s in services:
        for fid in s.get("features", []):
            svc_feat_ids.setdefault(fid, []).append(s["slug"])
    for fid, slugs in svc_feat_ids.items():
        if len(slugs) > 1:
            return Err(f"Feature '{fid}' appears in multiple services")

    return Ok(None)


def _feature_to_dict(feature: object, slug_map: dict) -> dict:
    """Convert Feature to manifest dict entry."""
    return {
        "id": feature.id,
        "name": feature.name,
        "display_name": feature.display_name,
        "description": feature.description,
        "priority": feature.priority,
        "category": feature.category,
        "service": slug_map.get(feature.id, ""),
    }


def _service_to_dict(service: object) -> dict:
    """Convert Service to manifest dict entry."""
    return {
        "name": service.name,
        "slug": service.slug,
        "features": list(service.feature_ids),
        "rationale": service.rationale,
        "communication": [
            {
                "target": link.target,
                "pattern": link.pattern,
                "required": link.required,
                "description": link.description,
            }
            for link in service.communication
        ],
    }


def _event_to_dict(event: object) -> dict:
    """Convert Event to manifest dict entry."""
    return {
        "name": event.name,
        "producer": event.producer,
        "consumers": list(event.consumers),
        "payload_summary": event.payload_summary,
    }


def _build_service_slug_map(
    features: list, services: list
) -> dict[str, str]:
    """Map feature IDs to service slugs."""
    slug_map: dict[str, str] = {}
    for svc in services:
        for fid in svc.feature_ids:
            slug_map[fid] = svc.slug
    return slug_map


def _atomic_write_json(path: Path, data: dict) -> Result:
    """Write JSON atomically: temp file + fsync + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    fd: int | None = None
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)
        os.write(fd, content)
        os.fsync(fd)
        os.close(fd)
        fd = None
        tmp_path.replace(path)
        tmp_path = None
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write manifest '{path}': {exc}")
    finally:
        if fd is not None:
            import contextlib

            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
