"""Tests for edge-cases template rendering — enriched & fallback paths (T022)."""

from __future__ import annotations

import re
from typing import Any

import yaml

from specforge.core.template_models import TemplateType
from specforge.core.template_registry import TemplateRegistry
from specforge.core.template_renderer import TemplateRenderer

# ── Helpers ──────────────────────────────────────────────────────────────

_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)

_REQUIRED_YAML_KEYS = {
    "id",
    "category",
    "severity",
    "affected_services",
    "handling_strategy",
    "test_suggestion",
}


def _make_renderer() -> TemplateRenderer:
    """Create a renderer with discovered built-in templates."""
    registry = TemplateRegistry()
    registry.discover()
    return TemplateRenderer(registry)


def _render(ctx: dict[str, Any]) -> str:
    """Render edge-cases template and return the output string."""
    renderer = _make_renderer()
    result = renderer.render("edge-cases", TemplateType.feature, ctx)
    assert result.ok, f"Render failed: {result.error}"
    return result.value


def _extract_yaml_blocks(text: str) -> list[dict[str, Any]]:
    """Extract and parse all ```yaml``` fenced blocks from rendered output."""
    raw_blocks = _YAML_BLOCK_RE.findall(text)
    parsed: list[dict[str, Any]] = []
    for block in raw_blocks:
        loaded = yaml.safe_load(block)
        if isinstance(loaded, dict):
            parsed.append(loaded)
    return parsed


# ── Shared context data ──────────────────────────────────────────────────

_BASE_CTX: dict[str, Any] = {
    "project_name": "PersonalFinance",
    "date": "2026-01-01",
    "feature_name": "ledger-service",
    "service": {"slug": "ledger-service", "name": "Ledger Service"},
    "architecture": "microservice",
    "features": [
        {"display_name": "Transaction Recording", "description": "Record income/expense"},
        {"display_name": "Balance Calculation", "description": "Compute running balance"},
    ],
    "adapter_edge_cases": [],
    "input_artifacts": {},
}

_SAMPLE_EDGE_CASES: list[dict[str, Any]] = [
    {
        "id": "EC-001",
        "category": "service_unavailability",
        "severity": "critical",
        "scenario": "identity-service returns 503 when ledger-service validates token",
        "trigger": "identity-service down or overloaded",
        "affected_services": ["ledger-service", "identity-service"],
        "handling_strategy": "circuit_breaker, retry_with_backoff",
        "test_suggestion": "Stub identity-service to return 503, verify circuit opens",
    },
    {
        "id": "EC-002",
        "category": "eventual_consistency",
        "severity": "high",
        "scenario": "Analytics processes transaction 5s after ledger publishes event",
        "trigger": "Event bus propagation delay",
        "affected_services": ["ledger-service", "analytics-service"],
        "handling_strategy": "stale_data_warning, cache_invalidation",
        "test_suggestion": "Delay event delivery, verify analytics shows warning",
    },
]


def _enriched_ctx(
    edge_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build context with enriched edge_cases list."""
    ctx = dict(_BASE_CTX)
    ctx["edge_cases"] = edge_cases if edge_cases is not None else list(_SAMPLE_EDGE_CASES)
    return ctx


def _fallback_ctx() -> dict[str, Any]:
    """Build context without edge_cases — triggers fallback path."""
    return dict(_BASE_CTX)


# ── Tests ────────────────────────────────────────────────────────────────


class TestEdgeCaseTemplate:
    """Template rendering tests for the edge-cases feature template."""

    # 1. Enriched path renders YAML blocks
    def test_enriched_renders_yaml_blocks(self) -> None:
        output = _render(_enriched_ctx())
        assert "```yaml" in output
        blocks = _YAML_BLOCK_RE.findall(output)
        assert len(blocks) == len(_SAMPLE_EDGE_CASES)

    # 2. Each YAML block is valid and contains required keys
    def test_each_yaml_block_is_valid_yaml(self) -> None:
        output = _render(_enriched_ctx())
        parsed = _extract_yaml_blocks(output)
        assert len(parsed) == len(_SAMPLE_EDGE_CASES)
        for block in parsed:
            missing = _REQUIRED_YAML_KEYS - set(block.keys())
            assert not missing, f"YAML block missing keys: {missing}"

    # 3. affected_services is a YAML list
    def test_affected_services_is_yaml_list(self) -> None:
        output = _render(_enriched_ctx())
        parsed = _extract_yaml_blocks(output)
        for block in parsed:
            assert isinstance(
                block["affected_services"], list
            ), f"Expected list, got {type(block['affected_services'])}"
            assert len(block["affected_services"]) > 0

    # 4. Fallback renders adapter_edge_cases loop (no edge_cases in context)
    def test_fallback_renders_adapter_edge_cases(self) -> None:
        ctx = _fallback_ctx()
        ctx["adapter_edge_cases"] = [
            {"name": "Network Timeout", "description": "Upstream service times out"},
        ]
        output = _render(ctx)
        # Enriched YAML blocks should NOT appear
        assert "```yaml" not in output
        # Fallback adapter section should appear
        assert "Architecture-Specific Edge Cases" in output
        assert "EC-A1: Network Timeout" in output

    # 5. Empty edge_cases list falls back to old format
    def test_empty_edge_cases_falls_back(self) -> None:
        output = _render(_enriched_ctx(edge_cases=[]))
        # No YAML blocks when list is empty
        assert "```yaml" not in output
        # Fallback generates per-feature edge cases
        assert "EC-1: Transaction Recording" in output
        assert "EC-2: Balance Calculation" in output

    # 6. Enriched path shows **Scenario** and **Trigger**
    def test_enriched_shows_scenario_and_trigger(self) -> None:
        output = _render(_enriched_ctx())
        for ec in _SAMPLE_EDGE_CASES:
            assert f"**Scenario**: {ec['scenario']}" in output
            assert f"**Trigger**: {ec['trigger']}" in output

    # 7. Category title is properly formatted
    def test_category_title_formatted(self) -> None:
        output = _render(_enriched_ctx())
        assert "### EC-001: Service Unavailability" in output
        assert "### EC-002: Eventual Consistency" in output

    # 8. Heading shows edge case count
    def test_edge_case_count_in_heading(self) -> None:
        output = _render(_enriched_ctx())
        assert "## Edge Cases (2)" in output

    # Bonus: count updates with different list sizes
    def test_edge_case_count_scales_with_list(self) -> None:
        five_cases = _SAMPLE_EDGE_CASES * 2 + _SAMPLE_EDGE_CASES[:1]
        output = _render(_enriched_ctx(edge_cases=five_cases))
        assert "## Edge Cases (5)" in output
