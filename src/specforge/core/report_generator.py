"""Generates status.json and status.md report files."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from jinja2 import BaseLoader, Environment, TemplateNotFound

from specforge.core.config import (
    STATUS_JSON_FILENAME,
    STATUS_MD_FILENAME,
    STATUS_SCHEMA_VERSION,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.status_models import ProjectStatusSnapshot

# ── Template Loader ──────────────────────────────────────────────────


class _StatusTemplateLoader(BaseLoader):
    """Load status report templates from the specforge package."""

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str | None, None]:
        from importlib.resources import files

        parts = template.split("/")
        resource = files("specforge.templates")
        for part in parts:
            resource = resource.joinpath(part)
        try:
            source = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError) as exc:
            raise TemplateNotFound(template) from exc
        return source, template, None


_JINJA_ENV = Environment(
    loader=_StatusTemplateLoader(),
    keep_trailing_newline=True,
    autoescape=False,
)


# ── Snapshot → Dict ──────────────────────────────────────────────────


def _lifecycle_to_dict(lifecycle: object) -> dict:
    """Convert a LifecyclePhases dataclass to a plain dict."""
    return asdict(lifecycle)  # type: ignore[arg-type]


def _service_to_dict(svc: object) -> dict:
    """Convert ServiceStatusRecord to JSON-schema-compatible dict."""
    d = asdict(svc)  # type: ignore[arg-type]
    d["status"] = d.pop("overall_status")
    lc = d["lifecycle"]
    d["implementation_percent"] = lc.get("impl_percent") or 0
    d["features"] = list(d["features"])
    d["lifecycle"] = lc
    return d


def _phase_to_dict(phase: object) -> dict:
    """Convert PhaseProgressRecord to dict."""
    d = asdict(phase)  # type: ignore[arg-type]
    d["services"] = list(d["services"])
    d["service_details"] = [
        {k: v for k, v in sd.items()} for sd in d["service_details"]
    ]
    return d


def _snapshot_to_dict(snapshot: ProjectStatusSnapshot) -> dict:
    """Convert the full snapshot to a JSON-serialisable dict."""
    services = [_service_to_dict(s) for s in snapshot.services]
    phases = sorted(
        [_phase_to_dict(p) for p in snapshot.phases],
        key=lambda p: p["index"],
    )
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "project_name": snapshot.project_name,
        "architecture": snapshot.architecture,
        "timestamp": snapshot.timestamp,
        "has_failures": snapshot.has_failures,
        "services": services,
        "phases": phases,
        "quality": asdict(snapshot.quality),
        "warnings": list(snapshot.warnings),
    }


# ── Atomic Write ─────────────────────────────────────────────────────


def _atomic_write(path: Path, content: bytes) -> None:
    """Write *content* to *path* via tempfile + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f"{path.name}.",
        suffix=".tmp",
    )
    tmp = Path(tmp_str)
    try:
        os.write(fd, content)
        os.fsync(fd)
        os.close(fd)
        tmp.replace(path)
    except BaseException:
        os.close(fd) if not _fd_closed(fd) else None
        tmp.unlink(missing_ok=True)
        raise


def _fd_closed(fd: int) -> bool:
    """Check whether a file descriptor is already closed."""
    try:
        os.fstat(fd)
    except OSError:
        return True
    return False


# ── Public API ───────────────────────────────────────────────────────


def generate_json_report(
    snapshot: ProjectStatusSnapshot,
    output_dir: Path,
) -> Result[Path, str]:
    """Serialize *snapshot* to ``status.json`` in *output_dir*.

    Returns ``Ok(path)`` on success, ``Err(msg)`` on failure.
    """
    data = _snapshot_to_dict(snapshot)
    content = json.dumps(data, indent=2).encode("utf-8")
    path = output_dir / STATUS_JSON_FILENAME
    try:
        _atomic_write(path, content)
    except OSError as exc:
        return Err(f"Failed to write {path}: {exc}")
    return Ok(path)


def generate_markdown_report(
    snapshot: ProjectStatusSnapshot,
    output_dir: Path,
) -> Result[Path, str]:
    """Render *snapshot* to ``status.md`` via Jinja2 template.

    Returns ``Ok(path)`` on success, ``Err(msg)`` on failure.
    """
    data = _snapshot_to_dict(snapshot)
    try:
        tmpl = _JINJA_ENV.get_template(
            "base/features/status-report.md.j2",
        )
        rendered = tmpl.render(**data)
    except Exception as exc:
        return Err(f"Template rendering failed: {exc}")
    path = output_dir / STATUS_MD_FILENAME
    try:
        _atomic_write(path, rendered.encode("utf-8"))
    except OSError as exc:
        return Err(f"Failed to write {path}: {exc}")
    return Ok(path)
