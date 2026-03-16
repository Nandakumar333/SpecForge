"""ResearchResolver — resolves technical unknowns into structured findings."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specforge.core.clarification_models import ResearchContext, ResearchFinding
from specforge.core.config import MICROSERVICE_RESEARCH_TOPICS

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext

_NEEDS_CLARIFICATION_RE = re.compile(
    r"\[NEEDS CLARIFICATION:\s*(.*?)\]", re.IGNORECASE,
)
_TECH_REFERENCE_RE = re.compile(
    r"\b(?:gRPC|Redis|Kafka|RabbitMQ|PostgreSQL|MongoDB|MySQL"
    r"|Docker|Express|FastAPI|Flask|Django|Spring|"
    r"React|Vue|Angular|GraphQL|REST|WebSocket|"
    r"JWT|OAuth|OIDC|Celery|Sidekiq|"
    r"CockroachDB|SQLite|DynamoDB|Elasticsearch)\b",
    re.IGNORECASE,
)


class ResearchResolver:
    """Generates research findings from spec and plan analysis."""

    def __init__(self, adapter: ArchitectureAdapter) -> None:
        self._adapter = adapter

    def resolve(
        self,
        spec_text: str,
        plan_text: str | None,
        service_ctx: ServiceContext,
    ) -> tuple[ResearchFinding, ...]:
        """Scan spec/plan for unknowns and produce findings."""
        findings: list[ResearchFinding] = []
        findings.extend(_extract_clarification_markers(spec_text))
        if plan_text:
            findings.extend(_extract_clarification_markers(plan_text))
        findings.extend(_extract_tech_references(spec_text))
        if plan_text:
            findings.extend(_extract_tech_references(plan_text))
        findings.extend(self._adapter_findings())
        if service_ctx.architecture == "microservice":
            findings.extend(_microservice_findings(spec_text, service_ctx))
        return _deduplicate_findings(tuple(findings))

    def merge_findings(
        self,
        existing: tuple[ResearchFinding, ...],
        new: tuple[ResearchFinding, ...],
    ) -> tuple[ResearchFinding, ...]:
        """Merge new findings with existing, preserving RESOLVED."""
        merged: dict[str, ResearchFinding] = {}
        for f in existing:
            if f.status == "RESOLVED":
                merged[f.topic] = f
        for f in new:
            if f.topic not in merged:
                merged[f.topic] = f
        return tuple(merged.values())

    def _adapter_findings(self) -> list[ResearchFinding]:
        """Convert adapter research extras into ResearchFindings."""
        findings: list[ResearchFinding] = []
        for extra in self._adapter.get_research_extras():
            findings.append(ResearchFinding(
                topic=extra.get("topic", ""),
                summary=extra.get("description", ""),
                source="manifest-metadata",
                status="UNVERIFIED",
                originating_marker="architecture adapter",
            ))
        return findings


def _extract_clarification_markers(
    text: str,
) -> list[ResearchFinding]:
    """Find [NEEDS CLARIFICATION: ...] markers in text."""
    findings: list[ResearchFinding] = []
    for match in _NEEDS_CLARIFICATION_RE.finditer(text):
        topic = match.group(1).strip()
        findings.append(ResearchFinding(
            topic=topic,
            summary=f"Requires clarification: {topic}",
            source="spec-reference",
            status="BLOCKED",
            originating_marker=match.group(0),
        ))
    return findings


def _extract_tech_references(text: str) -> list[ResearchFinding]:
    """Find technology/library references in text."""
    seen: set[str] = set()
    findings: list[ResearchFinding] = []
    for match in _TECH_REFERENCE_RE.finditer(text):
        tech = match.group(0)
        key = tech.lower()
        if key in seen:
            continue
        seen.add(key)
        findings.append(ResearchFinding(
            topic=f"{tech} integration",
            summary=f"Technology reference: {tech}. Version and "
            "compatibility information should be verified.",
            source="spec-reference",
            status="UNVERIFIED",
            originating_marker=tech,
        ))
    return findings


def _microservice_findings(
    spec_text: str,
    service_ctx: ServiceContext,
) -> list[ResearchFinding]:
    """Add container-level findings for microservice architectures."""
    findings: list[ResearchFinding] = []
    for topic_dict in MICROSERVICE_RESEARCH_TOPICS:
        findings.append(ResearchFinding(
            topic=topic_dict["topic"],
            summary=topic_dict["description"],
            source="embedded-knowledge",
            status="UNVERIFIED",
            originating_marker="microservice architecture",
        ))
    # Add gRPC-specific finding if referenced
    if re.search(r"\bgrpc\b", spec_text, re.IGNORECASE):
        findings.append(ResearchFinding(
            topic="gRPC service setup",
            summary="gRPC proto file conventions, code generation, "
            "and inter-service communication setup",
            source="embedded-knowledge",
            status="UNVERIFIED",
            originating_marker="gRPC reference in spec",
        ))
    return findings


def _deduplicate_findings(
    findings: tuple[ResearchFinding, ...],
) -> tuple[ResearchFinding, ...]:
    """Remove duplicate findings by topic (keep first occurrence)."""
    seen: set[str] = set()
    result: list[ResearchFinding] = []
    for f in findings:
        key = f.topic.lower()
        if key not in seen:
            seen.add(key)
            result.append(f)
    return tuple(result)


def build_research_context(
    spec_text: str,
    plan_text: str | None,
    service_ctx: ServiceContext,
    adapter: ArchitectureAdapter,
) -> ResearchContext:
    """Build a ResearchContext from spec, plan, and manifest data."""
    markers = [m.group(1) for m in _NEEDS_CLARIFICATION_RE.finditer(spec_text)]
    if plan_text:
        markers.extend(
            m.group(1) for m in _NEEDS_CLARIFICATION_RE.finditer(plan_text)
        )
    techs = list({
        m.group(0) for m in _TECH_REFERENCE_RE.finditer(spec_text)
    })
    comm_patterns = tuple(
        d.pattern for d in service_ctx.dependencies
    )
    return ResearchContext(
        architecture=service_ctx.architecture,
        communication_patterns=comm_patterns,
        tech_references=tuple(sorted(techs)),
        clarification_markers=tuple(markers),
        adapter_extras=tuple(adapter.get_research_extras()),
    )
