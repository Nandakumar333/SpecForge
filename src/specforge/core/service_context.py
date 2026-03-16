"""ServiceContext — resolved service data from manifest.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from specforge.core.config import FEATURES_DIR, MANIFEST_PATH
from specforge.core.result import Err, Ok, Result


@dataclass(frozen=True)
class FeatureInfo:
    """Lightweight feature data extracted from manifest.json."""

    id: str
    name: str
    display_name: str
    description: str
    priority: str
    category: str


@dataclass(frozen=True)
class ServiceDependency:
    """A dependency on another service."""

    target_slug: str
    target_name: str
    pattern: str
    required: bool
    description: str


@dataclass(frozen=True)
class EventInfo:
    """Event metadata for inter-service communication."""

    name: str
    producer: str
    consumers: tuple[str, ...]
    payload_summary: str


@dataclass(frozen=True)
class ServiceContext:
    """Resolved context for a target service."""

    service_slug: str
    service_name: str
    architecture: str
    project_description: str
    domain: str
    features: tuple[FeatureInfo, ...]
    dependencies: tuple[ServiceDependency, ...]
    events: tuple[EventInfo, ...]
    output_dir: Path


def resolve_target(target: str, project_root: Path) -> Result:
    """Resolve a target (slug or feature number) to a service slug."""
    manifest_result = _load_manifest(project_root)
    if not manifest_result.ok:
        return manifest_result
    data = manifest_result.value
    return _resolve_slug_or_number(target, data)


def load_service_context(
    service_slug: str, project_root: Path
) -> Result:
    """Load a ServiceContext from manifest.json for a service."""
    manifest_result = _load_manifest(project_root)
    if not manifest_result.ok:
        return manifest_result
    data = manifest_result.value
    return _build_context(service_slug, data, project_root)


def _load_manifest(project_root: Path) -> Result:
    """Read and parse manifest.json."""
    path = project_root / MANIFEST_PATH
    if not path.exists():
        return Err(
            f"manifest.json not found at '{path}'. "
            "Run 'specforge decompose' first."
        )
    try:
        raw = path.read_text(encoding="utf-8")
        return Ok(json.loads(raw))
    except (json.JSONDecodeError, OSError) as exc:
        return Err(f"Invalid manifest.json: {exc}")


def _resolve_slug_or_number(target: str, data: dict) -> Result:
    """Try slug match, then feature number match."""
    services = data.get("services", [])
    for svc in services:
        if svc["slug"] == target:
            return Ok(target)
    features = data.get("features", [])
    for feat in features:
        if feat["id"] == target:
            svc_slug = feat.get("service", "")
            if svc_slug:
                return Ok(svc_slug)
    slugs = [s["slug"] for s in services]
    return Err(
        f"Target '{target}' not found in manifest. "
        f"Available services: {', '.join(slugs)}"
    )


def _build_context(
    slug: str, data: dict, project_root: Path
) -> Result:
    """Build ServiceContext from manifest data."""
    services = data.get("services", [])
    svc_data = _find_service(slug, services)
    if svc_data is None:
        slugs = [s["slug"] for s in services]
        return Err(
            f"Service '{slug}' not found in manifest. "
            f"Available: {', '.join(slugs)}"
        )
    features = _extract_features(svc_data, data.get("features", []))
    deps = _extract_dependencies(svc_data, services)
    events = _extract_events(slug, data.get("events", []))
    output_dir = project_root / FEATURES_DIR / slug
    return Ok(
        ServiceContext(
            service_slug=slug,
            service_name=svc_data["name"],
            architecture=data.get("architecture", "monolithic"),
            project_description=data.get("project_description", ""),
            domain=data.get("domain", ""),
            features=tuple(features),
            dependencies=tuple(deps),
            events=tuple(events),
            output_dir=output_dir,
        )
    )


def _find_service(slug: str, services: list) -> dict | None:
    """Find a service by slug."""
    for svc in services:
        if svc["slug"] == slug:
            return svc
    return None


def _extract_features(
    svc_data: dict, all_features: list
) -> list[FeatureInfo]:
    """Filter features belonging to a service."""
    svc_feat_ids = set(svc_data.get("features", []))
    return [
        FeatureInfo(
            id=f["id"],
            name=f["name"],
            display_name=f["display_name"],
            description=f["description"],
            priority=f["priority"],
            category=f["category"],
        )
        for f in all_features
        if f["id"] in svc_feat_ids
    ]


def _extract_dependencies(
    svc_data: dict, all_services: list
) -> list[ServiceDependency]:
    """Extract service dependencies from communication links."""
    name_map = {s["slug"]: s["name"] for s in all_services}
    return [
        ServiceDependency(
            target_slug=link["target"],
            target_name=name_map.get(link["target"], link["target"]),
            pattern=link["pattern"],
            required=link["required"],
            description=link["description"],
        )
        for link in svc_data.get("communication", [])
    ]


def _extract_events(
    slug: str, all_events: list
) -> list[EventInfo]:
    """Extract events produced or consumed by a service."""
    return [
        EventInfo(
            name=e["name"],
            producer=e["producer"],
            consumers=tuple(e.get("consumers", [])),
            payload_summary=e.get("payload_summary", ""),
        )
        for e in all_events
        if e["producer"] == slug or slug in e.get("consumers", [])
    ]
