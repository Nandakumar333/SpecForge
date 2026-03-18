"""Reads manifest and all per-service state files into a ProjectStatusSnapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.config import (
    EXECUTION_STATE_FILENAME,
    FEATURES_DIR,
    MANIFEST_PATH,
    ORCHESTRATION_STATE_FILENAME,
    PIPELINE_STATE_FILENAME,
    QUALITY_REPORT_FILENAME,
)
from specforge.core.graph_builder import build_dependency_graph
from specforge.core.metrics_calculator import (
    aggregate_quality,
    build_lifecycle,
    calculate_phase_progress,
    derive_service_status,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.status_models import (
    ProjectStatusSnapshot,
    ServiceStatusRecord,
)

# ── Internal intermediate types ───────────────────────────────────────


@dataclass(frozen=True)
class ManifestServiceEntry:
    """Single service entry from manifest.json."""

    slug: str
    display_name: str
    features: tuple[str, ...]


@dataclass(frozen=True)
class CommunicationEntry:
    """A directed communication link between two services."""

    source: str
    target: str


@dataclass(frozen=True)
class ManifestData:
    """Parsed manifest.json content."""

    project_name: str
    architecture: str
    services: tuple[ManifestServiceEntry, ...]
    communication: tuple[CommunicationEntry, ...]


@dataclass(frozen=True)
class ServiceRawState:
    """Raw state files for a single service before status derivation."""

    slug: str
    pipeline: Ok | Err | None = None
    execution: Ok | Err | None = None
    quality: Ok | Err | None = None
    orchestration_phase: int | None = None


# ── Manifest loading ──────────────────────────────────────────────────


def load_manifest(project_root: Path) -> Result[ManifestData, str]:
    """Read .specforge/manifest.json and return parsed ManifestData."""
    manifest_path = project_root / MANIFEST_PATH
    if not manifest_path.exists():
        return Err(f"Manifest not found: {manifest_path}")
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return Err(f"Failed to parse manifest: {exc}")
    return Ok(_parse_manifest(raw))


def _parse_manifest(raw: dict) -> ManifestData:
    """Convert raw JSON dict into ManifestData."""
    services = tuple(
        ManifestServiceEntry(
            slug=s.get("slug", ""),
            display_name=s.get("name", s.get("slug", "")),
            features=tuple(s.get("features", [])),
        )
        for s in raw.get("services", [])
    )
    comms: list[CommunicationEntry] = []
    for svc in raw.get("services", []):
        for link in svc.get("communication", []):
            comms.append(
                CommunicationEntry(
                    source=svc.get("slug", ""),
                    target=link.get("target", ""),
                )
            )
    return ManifestData(
        project_name=raw.get("project_name", ""),
        architecture=raw.get("architecture", ""),
        services=services,
        communication=tuple(comms),
    )


# ── Per-service state file reading ───────────────────────────────────


def _read_json_file(path: Path) -> Ok | Err | None:
    """Read a JSON file: Ok(dict) if valid, Err on corrupt, None if missing."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return Err(f"Corrupt file {path.name}: {exc}")
    return Ok(data)


def read_service_states(features_dir: Path, slug: str) -> ServiceRawState:
    """Read all 3 state files for a single service."""
    svc_dir = features_dir / slug
    pipeline = _read_json_file(svc_dir / PIPELINE_STATE_FILENAME)
    execution = _read_json_file(svc_dir / EXECUTION_STATE_FILENAME)
    quality = _read_json_file(svc_dir / QUALITY_REPORT_FILENAME)
    return ServiceRawState(
        slug=slug,
        pipeline=pipeline,
        execution=execution,
        quality=quality,
    )


# ── Orchestration state reading ──────────────────────────────────────


def read_orchestration_state(project_root: Path) -> Result[dict, str] | None:
    """Read .specforge/.orchestration-state.json (project-level)."""
    path = project_root / ORCHESTRATION_STATE_FILENAME
    return _read_json_file(path)


def _find_service_phase(
    orch_data: dict,
    slug: str,
) -> int | None:
    """Find which orchestration phase a service belongs to."""
    for phase in orch_data.get("phases", []):
        for svc in phase.get("services", []):
            if svc.get("slug") == slug:
                return phase.get("index")
    return None


# ── Top-level collector ──────────────────────────────────────────────


def collect_project_status(
    project_root: Path,
) -> Result[ProjectStatusSnapshot, str]:
    """Collect full project status from all state files."""
    manifest_result = load_manifest(project_root)
    if not manifest_result.ok:
        return Err(manifest_result.error)

    manifest: ManifestData = manifest_result.value
    features_dir = project_root / FEATURES_DIR
    orch_result = read_orchestration_state(project_root)
    orch_data = _extract_orch_data(orch_result)

    services, warnings, raw_map = _build_service_records(
        manifest, features_dir, orch_data,
    )
    svc_tuple = tuple(services)
    status_map = {s.slug: s for s in services}
    phases = calculate_phase_progress(orch_data, status_map)
    quality = aggregate_quality(svc_tuple, manifest.architecture, raw_map)
    has_failures = any(s.overall_status == "FAILED" for s in services)
    service_statuses = {s.slug: s.overall_status for s in services}
    graph = build_dependency_graph(manifest, service_statuses)

    return Ok(ProjectStatusSnapshot(
        project_name=manifest.project_name,
        architecture=manifest.architecture,
        services=svc_tuple,
        phases=phases,
        quality=quality,
        graph=graph,
        warnings=tuple(warnings),
        timestamp=datetime.now(UTC).isoformat(),
        has_failures=has_failures,
    ))


def _extract_orch_data(orch_result: Result | None) -> dict | None:
    """Safely extract orchestration dict or None."""
    if orch_result is None:
        return None
    if isinstance(orch_result, Ok):
        return orch_result.value
    return None


def _build_service_records(
    manifest: ManifestData,
    features_dir: Path,
    orch_data: dict | None,
) -> tuple[list[ServiceStatusRecord], list[str], dict[str, ServiceRawState]]:
    """Build service records, collect warnings, and return raw states."""
    services: list[ServiceStatusRecord] = []
    warnings: list[str] = []
    raw_map: dict[str, ServiceRawState] = {}
    for entry in manifest.services:
        raw = _enrich_raw_state(features_dir, entry.slug, orch_data)
        raw_map[entry.slug] = raw
        _collect_warnings(raw, warnings)
        services.append(_build_one_record(entry, raw, manifest.architecture))
    return services, warnings, raw_map


def _enrich_raw_state(
    features_dir: Path, slug: str, orch_data: dict | None,
) -> ServiceRawState:
    """Read state files and attach orchestration phase index."""
    raw = read_service_states(features_dir, slug)
    phase_idx = _find_service_phase(orch_data, slug) if orch_data else None
    return ServiceRawState(
        slug=raw.slug,
        pipeline=raw.pipeline,
        execution=raw.execution,
        quality=raw.quality,
        orchestration_phase=phase_idx,
    )


def _build_one_record(
    entry: ManifestServiceEntry,
    raw: ServiceRawState,
    architecture: str,
) -> ServiceStatusRecord:
    """Derive status + lifecycle for a single service."""
    return ServiceStatusRecord(
        slug=entry.slug,
        display_name=entry.display_name,
        features=entry.features,
        lifecycle=build_lifecycle(raw, architecture),
        overall_status=derive_service_status(raw, dependencies_met=True),
        phase_index=raw.orchestration_phase,
    )


def _collect_warnings(raw: ServiceRawState, warnings: list[str]) -> None:
    """Append warnings for corrupt state files."""
    if isinstance(raw.pipeline, Err):
        warnings.append(f"{raw.slug}: {raw.pipeline.error}")
    if isinstance(raw.execution, Err):
        warnings.append(f"{raw.slug}: {raw.execution.error}")
    if isinstance(raw.quality, Err):
        warnings.append(f"{raw.slug}: {raw.quality.error}")
