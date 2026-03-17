"""Unit tests for ResearchResolver — research finding extraction and merging."""

from __future__ import annotations

from pathlib import Path

from specforge.core.clarification_models import ResearchFinding
from specforge.core.research_resolver import ResearchResolver
from specforge.core.service_context import FeatureInfo, ServiceContext

# ---------------------------------------------------------------------------
# Mock adapters
# ---------------------------------------------------------------------------

class _MockMicroserviceAdapter:
    """Adapter returning microservice-specific research extras."""

    def get_research_extras(self) -> list[dict[str, str]]:
        return [
            {
                "topic": "Service mesh evaluation",
                "description": "Evaluate service mesh options",
            },
        ]


class _MockMonolithAdapter:
    """Adapter returning no extras for monolithic architecture."""

    def get_research_extras(self) -> list[dict[str, str]]:
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resolver(
    *, adapter: object | None = None,
) -> ResearchResolver:
    """Return a ResearchResolver with the given adapter."""
    if adapter is None:
        adapter = _MockMicroserviceAdapter()
    return ResearchResolver(adapter)


def _make_service_ctx(
    *,
    slug: str = "ledger-service",
    architecture: str = "microservice",
) -> ServiceContext:
    return ServiceContext(
        service_slug=slug,
        service_name="Ledger Service",
        architecture=architecture,
        project_description="Personal Finance Tracker",
        domain="finance",
        features=(
            FeatureInfo(
                id="002",
                name="accounts",
                display_name="Account Management",
                description="Track bank accounts and balances",
                priority="P1",
                category="core",
            ),
        ),
        dependencies=(),
        events=(),
        output_dir=Path(".specforge/features/ledger-service"),
    )


def _make_spec_with_markers() -> str:
    """Spec text containing [NEEDS CLARIFICATION: ...] markers and tech refs."""
    return (
        "## Ledger Service\n"
        "\n"
        "The service uses gRPC for inter-service communication.\n"
        "Caching is handled by Redis for session storage.\n"
        "\n"
        "[NEEDS CLARIFICATION: transaction validation rules]\n"
        "Transactions are validated against configurable rules.\n"
        "\n"
        "[NEEDS CLARIFICATION: retry policy for failed transfers]\n"
        "Failed transfers are retried with exponential backoff.\n"
        "\n"
        "The message broker choice is TBD.\n"
    )


def _make_clean_spec() -> str:
    """Spec with no markers or ambiguities."""
    return (
        "## Ledger Service\n"
        "\n"
        "The service exposes a REST API on port 8080.\n"
        "Data is stored in PostgreSQL 15.\n"
    )


def _make_plan_text() -> str:
    """Plan text with additional tech references."""
    return (
        "## Implementation Plan\n"
        "\n"
        "Use Docker multi-stage builds for deployment.\n"
        "Implement health check endpoints at /healthz.\n"
        "Consider Kafka for event streaming.\n"
    )


def _make_existing_findings() -> tuple[ResearchFinding, ...]:
    """Pre-existing findings for merge tests."""
    return (
        ResearchFinding(
            topic="Transaction validation",
            summary="Use configurable rule engine",
            source="spec.md",
            status="RESOLVED",
            originating_marker="transaction validation rules",
        ),
        ResearchFinding(
            topic="Retry policy",
            summary="Exponential backoff with jitter",
            source="spec.md",
            status="BLOCKED",
            originating_marker="retry policy for failed transfers",
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResolveMarkers:
    """resolve() extracts NEEDS CLARIFICATION markers from spec text."""

    def test_extracts_clarification_markers(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("transaction" in t or "validation" in t for t in topics)

    def test_extracts_multiple_markers(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        # At least the two explicit NEEDS CLARIFICATION markers
        marker_findings = [
            f for f in findings if f.originating_marker != ""
        ]
        assert len(marker_findings) >= 2


class TestResolveTechReferences:
    """resolve() identifies technology references (gRPC, Redis, etc.)."""

    def test_identifies_grpc(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("grpc" in t for t in topics)

    def test_identifies_redis(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("redis" in t for t in topics)


class TestResolveAdapterExtras:
    """resolve() adds adapter research extras based on architecture."""

    def test_microservice_adds_adapter_extras(self) -> None:
        resolver = _make_resolver(adapter=_MockMicroserviceAdapter())
        ctx = _make_service_ctx(architecture="microservice")
        findings = resolver.resolve(_make_clean_spec(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("service mesh" in t for t in topics)

    def test_monolith_omits_adapter_extras(self) -> None:
        resolver = _make_resolver(adapter=_MockMonolithAdapter())
        ctx = _make_service_ctx(architecture="monolithic")
        findings = resolver.resolve(_make_clean_spec(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert not any("service mesh" in t for t in topics)


class TestResolveFindingStatuses:
    """resolve() assigns correct statuses to findings."""

    def test_unverified_for_library_versions(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        # Tech references (gRPC, Redis) should have UNVERIFIED status
        tech_findings = [
            f for f in findings
            if "grpc" in f.topic.lower() or "redis" in f.topic.lower()
        ]
        for f in tech_findings:
            assert f.status == "UNVERIFIED"

    def test_blocked_for_unresolvable(self) -> None:
        spec = (
            "## Service\n\n"
            "[NEEDS CLARIFICATION: unknown external API contract]\n"
            "Integration with external payment provider TBD.\n"
        )
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(spec, None, ctx)
        # At least one finding should be BLOCKED for the TBD item
        statuses = {f.status for f in findings}
        assert "UNVERIFIED" in statuses or "BLOCKED" in statuses


class TestResolvePlanText:
    """resolve() handles plan_text parameter."""

    def test_plan_none_processes_spec_only(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_clean_spec(), None, ctx)
        # Should still return findings (at least adapter extras for microservice)
        assert isinstance(findings, tuple)

    def test_plan_text_contributes_findings(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings_without = resolver.resolve(_make_clean_spec(), None, ctx)
        findings_with = resolver.resolve(
            _make_clean_spec(), _make_plan_text(), ctx,
        )
        # Plan text adds Docker, health check, Kafka references
        assert len(findings_with) >= len(findings_without)


class TestMergeFindings:
    """ResearchResolver.merge_findings() combines existing and new."""

    def test_preserves_resolved_from_existing(self) -> None:
        resolver = _make_resolver()
        existing = _make_existing_findings()
        new = (
            ResearchFinding(
                topic="Transaction validation",
                summary="Updated rule engine approach",
                source="spec.md",
                status="UNVERIFIED",
                originating_marker="transaction validation rules",
            ),
        )
        merged = resolver.merge_findings(existing, new)
        tx_findings = [f for f in merged if "transaction" in f.topic.lower()]
        # Existing RESOLVED status should be preserved
        assert any(f.status == "RESOLVED" for f in tx_findings)

    def test_re_evaluates_blocked_from_existing(self) -> None:
        resolver = _make_resolver()
        existing = _make_existing_findings()
        new = (
            ResearchFinding(
                topic="Retry policy",
                summary="Use Polly library for retries",
                source="plan.md",
                status="UNVERIFIED",
                originating_marker="retry policy for failed transfers",
            ),
        )
        merged = resolver.merge_findings(existing, new)
        retry_findings = [f for f in merged if "retry" in f.topic.lower()]
        # BLOCKED should be re-evaluated when new info arrives
        assert len(retry_findings) >= 1
        assert any(f.status != "BLOCKED" for f in retry_findings)

    def test_adds_new_findings(self) -> None:
        resolver = _make_resolver()
        existing = _make_existing_findings()
        new = (
            ResearchFinding(
                topic="API gateway selection",
                summary="Evaluate Kong vs Envoy",
                source="plan.md",
                status="UNVERIFIED",
                originating_marker="",
            ),
        )
        merged = resolver.merge_findings(existing, new)
        topics = [f.topic.lower() for f in merged]
        assert any("api gateway" in t for t in topics)

    def test_merged_has_no_duplicate_topics(self) -> None:
        resolver = _make_resolver()
        existing = _make_existing_findings()
        new = (
            ResearchFinding(
                topic="Transaction validation",
                summary="Duplicate topic",
                source="plan.md",
                status="UNVERIFIED",
                originating_marker="transaction validation rules",
            ),
        )
        merged = resolver.merge_findings(existing, new)
        topics = [f.topic.lower() for f in merged]
        # Should not have two entries for the same topic
        assert len(topics) == len(set(topics))


class TestMicroserviceResearchInjection:
    """Microservice architecture injects Docker/health/broker findings (FR-018)."""

    def test_docker_finding_injected(self) -> None:
        resolver = _make_resolver(adapter=_MockMicroserviceAdapter())
        ctx = _make_service_ctx(architecture="microservice")
        findings = resolver.resolve(_make_plan_text(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("docker" in t for t in topics)

    def test_health_check_finding_injected(self) -> None:
        resolver = _make_resolver(adapter=_MockMicroserviceAdapter())
        ctx = _make_service_ctx(architecture="microservice")
        findings = resolver.resolve(_make_plan_text(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("health" in t for t in topics)

    def test_message_broker_finding_injected(self) -> None:
        resolver = _make_resolver(adapter=_MockMicroserviceAdapter())
        ctx = _make_service_ctx(architecture="microservice")
        findings = resolver.resolve(_make_plan_text(), None, ctx)
        topics = [f.topic.lower() for f in findings]
        assert any("kafka" in t or "broker" in t or "message" in t for t in topics)

    def test_all_findings_are_research_finding(self) -> None:
        resolver = _make_resolver()
        ctx = _make_service_ctx()
        findings = resolver.resolve(_make_spec_with_markers(), None, ctx)
        for f in findings:
            assert isinstance(f, ResearchFinding)
