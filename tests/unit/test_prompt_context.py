"""Unit tests for PromptContextBuilder — T056."""

from __future__ import annotations

from pathlib import Path

from specforge.core.config import GOVERNANCE_DOMAINS, PRECEDENCE_ORDER
from specforge.core.prompt_models import (
    PromptFile,
    PromptFileMeta,
    PromptRule,
    PromptSet,
    PromptThreshold,
)


def _make_prompt_file(domain: str, precedence: int) -> PromptFile:
    rule = PromptRule(
        rule_id=f"{domain[:4].upper()}-001",
        title="Test Rule",
        severity="ERROR",
        scope="all files",
        description=f"All code MUST comply with {domain} rules.",
        thresholds=(PromptThreshold("max_lines", "100"),),
        example_correct="correct",
        example_incorrect="incorrect",
    )
    meta = PromptFileMeta(
        domain=domain,
        stack="agnostic",
        version="1.0",
        precedence=precedence,
        checksum="abc123",
    )
    raw = f"# {domain.title()} Governance\n\n## Rules\n\n{domain} content here.\n"
    return PromptFile(
        path=Path(f"/tmp/{domain}.prompts.md"),
        meta=meta,
        rules=(rule,),
        raw_content=raw,
    )


def _make_full_prompt_set(task_domain: str | None = None) -> PromptSet:
    precedence_map = {
        "security": 1, "architecture": 2, "backend": 3,
        "frontend": 3, "database": 3, "testing": 4, "cicd": 5,
    }
    files = {
        d: _make_prompt_file(d, precedence_map[d])
        for d in GOVERNANCE_DOMAINS
    }
    return PromptSet(
        files=files,
        precedence=list(PRECEDENCE_ORDER),
        feature_id="feat-001",
    )


class TestPromptContextBuilder:
    def test_all_7_domains_present_in_output(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps)

        for domain in GOVERNANCE_DOMAINS:
            assert domain in output.lower() or domain.title() in output, (
                f"Domain '{domain}' not found in context output"
            )

    def test_output_ordered_by_precedence(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps)

        # security content should appear before architecture content
        sec_pos = output.find("security content here")
        arch_pos = output.find("architecture content here")
        assert sec_pos < arch_pos, "security should appear before architecture"

    def test_task_domain_appears_first(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps, task_domain="backend")

        backend_pos = output.find("backend content here")
        security_pos = output.find("security content here")
        assert backend_pos < security_pos, (
            "task_domain='backend' should appear before security in output"
        )

    def test_without_task_domain_uses_precedence_order(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps, task_domain=None)

        # Without task_domain, security (prec 1) comes first
        sec_pos = output.find("security content here")
        cicd_pos = output.find("cicd content here")
        assert sec_pos < cicd_pos, "security (prec 1) should appear before cicd (prec 5)"

    def test_output_is_string(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps)
        assert isinstance(output, str)

    def test_total_output_length_reasonable(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps)
        lines = output.splitlines()
        # With short fixture content, should be well under 500 * 7 = 3500 lines
        assert len(lines) <= 3500, f"Output has {len(lines)} lines (expected <= 3500)"

    def test_task_domain_not_duplicated(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        output = PromptContextBuilder.build(ps, task_domain="testing")

        # testing content should appear exactly once
        count = output.count("testing content here")
        assert count == 1, f"Expected 'testing content here' once, found {count} times"

    def test_invalid_task_domain_falls_back_gracefully(self) -> None:
        from specforge.core.prompt_context import PromptContextBuilder

        ps = _make_full_prompt_set()
        # Invalid task_domain — should not raise, should use precedence order
        output = PromptContextBuilder.build(ps, task_domain="nonexistent")
        assert len(output) > 0
