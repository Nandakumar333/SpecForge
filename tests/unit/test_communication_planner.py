"""Unit tests for CommunicationPlanner (UT-009)."""

from __future__ import annotations

from specforge.core.communication_planner import (
    CommunicationLink,
    CommunicationPlanner,
)
from specforge.core.service_mapper import Service


def _svc(
    name: str,
    slug: str,
    feature_ids: tuple[str, ...] = ("001",),
    communication: tuple = (),
) -> Service:
    return Service(
        name=name,
        slug=slug,
        feature_ids=feature_ids,
        rationale="test",
        communication=communication,
    )


class TestHeuristicRules:
    """UT-009: test all 5 heuristic communication pattern rules."""

    def test_notification_gets_async(self) -> None:
        planner = CommunicationPlanner()
        notif = _svc("Notifications Service", "notifications-service")
        core = _svc("Core Service", "core-service", ("002",))
        services, _events = planner.plan([notif, core])
        links = _all_links_to(services, "notifications-service")
        for link in links:
            assert link.pattern == "async-event"

    def test_auth_gets_sync_rest(self) -> None:
        planner = CommunicationPlanner()
        auth = _svc("Authentication Service", "authentication-service")
        core = _svc("Core Service", "core-service", ("002",))
        services, _ = planner.plan([auth, core])
        links = _all_links_to(services, "authentication-service")
        for link in links:
            assert link.pattern == "sync-rest"

    def test_default_is_sync_rest(self) -> None:
        planner = CommunicationPlanner()
        svc_a = _svc("Ledger Service", "ledger-service")
        svc_b = _svc("Budget Service", "budget-service", ("002",))
        services, _ = planner.plan([svc_a, svc_b])
        all_links = []
        for s in services:
            all_links.extend(s.communication)
        if all_links:
            assert all_links[0].pattern in ("sync-rest", "sync-grpc")


class TestMermaidGeneration:
    """Test Mermaid diagram generation."""

    def test_mermaid_has_graph_directive(self) -> None:
        planner = CommunicationPlanner()
        svc = _svc(
            "Auth Service",
            "auth-service",
            communication=(
                CommunicationLink(
                    target="core-service",
                    pattern="sync-rest",
                    required=True,
                    description="test",
                ),
            ),
        )
        diagram = planner.generate_mermaid([svc], [])
        assert "graph" in diagram.lower() or "flowchart" in diagram.lower()

    def test_mermaid_has_solid_arrows(self) -> None:
        planner = CommunicationPlanner()
        link = CommunicationLink(
            target="core",
            pattern="sync-rest",
            required=True,
            description="test",
        )
        svc = _svc("Auth", "auth", communication=(link,))
        diagram = planner.generate_mermaid([svc], [])
        assert "-->" in diagram

    def test_mermaid_has_dashed_arrows(self) -> None:
        planner = CommunicationPlanner()
        link = CommunicationLink(
            target="core",
            pattern="async-event",
            required=False,
            description="test",
        )
        svc = _svc("Notif", "notif", communication=(link,))
        diagram = planner.generate_mermaid([svc], [])
        assert "-.->" in diagram or "-.>" in diagram


class TestCycleDetection:
    """Test DFS-based cycle detection."""

    def test_no_cycle_returns_empty(self) -> None:
        planner = CommunicationPlanner()
        link_ab = CommunicationLink(
            target="b", pattern="sync-rest", required=True, description=""
        )
        svc_a = _svc("A", "a", communication=(link_ab,))
        svc_b = _svc("B", "b", ("002",))
        cycles = planner.detect_cycles([svc_a, svc_b])
        assert len(cycles) == 0

    def test_cycle_detected(self) -> None:
        planner = CommunicationPlanner()
        link_ab = CommunicationLink(
            target="b", pattern="sync-rest", required=True, description=""
        )
        link_ba = CommunicationLink(
            target="a", pattern="sync-rest", required=True, description=""
        )
        svc_a = _svc("A", "a", communication=(link_ab,))
        svc_b = _svc("B", "b", ("002",), communication=(link_ba,))
        cycles = planner.detect_cycles([svc_a, svc_b])
        assert len(cycles) > 0


def _all_links_to(services: list, target_slug: str) -> list:
    """Collect all communication links targeting a specific service."""
    links = []
    for svc in services:
        for link in svc.communication:
            if link.target == target_slug:
                links.append(link)
    return links
