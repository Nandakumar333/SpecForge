"""Unit tests for QuestionGenerator — question creation from ambiguity matches."""

from __future__ import annotations

from pathlib import Path

from specforge.core.clarification_models import (
    AmbiguityMatch,
    ClarificationQuestion,
    SuggestedAnswer,
)
from specforge.core.question_generator import QuestionGenerator
from specforge.core.service_context import FeatureInfo, ServiceContext


def _make_generator() -> QuestionGenerator:
    """Return a default QuestionGenerator."""
    return QuestionGenerator()


def _make_match(
    *,
    text: str = "appropriately",
    line_number: int = 5,
    category: str = "domain",
    pattern_type: str = "vague_term",
    confidence: float = 1.0,
) -> AmbiguityMatch:
    return AmbiguityMatch(
        text=text,
        line_number=line_number,
        category=category,
        pattern_type=pattern_type,
        confidence=confidence,
    )


def _make_service_ctx(
    *,
    slug: str = "ledger-service",
    architecture: str = "microservice",
) -> ServiceContext:
    """Build a minimal ServiceContext for the ledger service."""
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
            FeatureInfo(
                id="003",
                name="transactions",
                display_name="Transaction Tracking",
                description="Record income and expenses",
                priority="P1",
                category="core",
            ),
        ),
        dependencies=(),
        events=(),
        output_dir=Path(".specforge/features/ledger-service"),
    )


def _make_spec_text_with_match() -> str:
    """Spec text where line 5 contains a vague term for context extraction."""
    return (
        "## Ledger Service\n"            # line 1
        "\n"                               # line 2
        "The service manages accounts.\n"  # line 3
        "\n"                               # line 4
        "Transactions are handled appropriately.\n"  # line 5
        "\n"                               # line 6
        "Each account has a balance.\n"    # line 7
        "\n"                               # line 8
    )


class TestGenerateBasic:
    """QuestionGenerator.generate() basic behaviour."""

    def test_returns_tuple_of_questions(self) -> None:
        gen = _make_generator()
        matches = (_make_match(),)
        ctx = _make_service_ctx()
        result = gen.generate(matches, ctx)
        assert isinstance(result, tuple)
        assert len(result) >= 1
        assert isinstance(result[0], ClarificationQuestion)

    def test_empty_matches_returns_empty(self) -> None:
        gen = _make_generator()
        result = gen.generate((), _make_service_ctx())
        assert result == ()

    def test_question_has_suggested_answers(self) -> None:
        gen = _make_generator()
        matches = (_make_match(),)
        questions = gen.generate(matches, _make_service_ctx())
        q = questions[0]
        assert len(q.suggested_answers) >= 2
        assert len(q.suggested_answers) <= 4

    def test_suggested_answer_fields(self) -> None:
        gen = _make_generator()
        questions = gen.generate((_make_match(),), _make_service_ctx())
        for ans in questions[0].suggested_answers:
            assert isinstance(ans, SuggestedAnswer)
            assert ans.label
            assert ans.text
            assert ans.implications


class TestQuestionIDs:
    """Question IDs must be sequential: CQ-001, CQ-002, etc."""

    def test_single_question_id(self) -> None:
        gen = _make_generator()
        questions = gen.generate((_make_match(),), _make_service_ctx())
        assert questions[0].id == "CQ-001"

    def test_multiple_sequential_ids(self) -> None:
        gen = _make_generator()
        matches = (
            _make_match(line_number=1),
            _make_match(text="TBD", line_number=10, category="technical",
                        pattern_type="unspecified_choice"),
            _make_match(text="as needed", line_number=20),
        )
        questions = gen.generate(matches, _make_service_ctx())
        ids = [q.id for q in questions]
        for i, qid in enumerate(ids, start=1):
            assert qid == f"CQ-{i:03d}"


class TestDeduplication:
    """Overlapping matches within 3 lines should be deduplicated."""

    def test_same_line_deduplicated(self) -> None:
        gen = _make_generator()
        m1 = _make_match(text="appropriately", line_number=5)
        m2 = _make_match(text="as needed", line_number=5)
        questions = gen.generate((m1, m2), _make_service_ctx())
        # Two matches on same line should collapse to one question
        assert len(questions) == 1

    def test_adjacent_lines_deduplicated(self) -> None:
        gen = _make_generator()
        m1 = _make_match(line_number=5)
        m2 = _make_match(text="proper", line_number=7)  # within 3 lines
        questions = gen.generate((m1, m2), _make_service_ctx())
        assert len(questions) == 1

    def test_distant_lines_not_deduplicated(self) -> None:
        gen = _make_generator()
        m1 = _make_match(line_number=1)
        m2 = _make_match(line_number=20)
        questions = gen.generate((m1, m2), _make_service_ctx())
        assert len(questions) == 2


class TestImpactRanking:
    """Questions must be ranked by IMPACT_PRIORITY order."""

    def test_service_boundary_before_domain(self) -> None:
        gen = _make_generator()
        domain = _make_match(line_number=1, category="domain")
        boundary = _make_match(
            text="categories",
            line_number=20,
            category="service_boundary",
            pattern_type="missing_boundary",
            confidence=0.7,
        )
        questions = gen.generate((domain, boundary), _make_service_ctx())
        assert len(questions) == 2
        assert questions[0].category == "service_boundary"
        assert questions[1].category == "domain"

    def test_domain_before_technical(self) -> None:
        gen = _make_generator()
        technical = _make_match(
            text="TBD", line_number=1, category="technical",
            pattern_type="unspecified_choice",
        )
        domain = _make_match(line_number=20, category="domain")
        questions = gen.generate((technical, domain), _make_service_ctx())
        assert questions[0].category == "domain"
        assert questions[1].category == "technical"

    def test_technical_before_communication(self) -> None:
        gen = _make_generator()
        comm = _make_match(
            text="protocol",
            line_number=1,
            category="communication",
            pattern_type="missing_boundary",
            confidence=0.7,
        )
        tech = _make_match(
            text="TBD", line_number=20, category="technical",
            pattern_type="unspecified_choice",
        )
        questions = gen.generate((comm, tech), _make_service_ctx())
        assert questions[0].category == "technical"
        assert questions[1].category == "communication"

    def test_impact_rank_values_ascending(self) -> None:
        gen = _make_generator()
        matches = (
            _make_match(line_number=1, category="communication",
                        pattern_type="missing_boundary", confidence=0.7),
            _make_match(line_number=20, category="domain"),
            _make_match(text="TBD", line_number=40, category="technical",
                        pattern_type="unspecified_choice"),
        )
        questions = gen.generate(matches, _make_service_ctx())
        ranks = [q.impact_rank for q in questions]
        assert ranks == sorted(ranks)


class TestContextExcerpt:
    """context_excerpt is extracted from spec.md at output_dir when present."""

    def test_excerpt_empty_without_spec_file(self) -> None:
        gen = _make_generator()
        questions = gen.generate((_make_match(),), _make_service_ctx())
        # No spec file at output_dir → excerpt is empty
        assert questions[0].context_excerpt == ""

    def test_excerpt_nonempty_with_spec_file(self, tmp_path: Path) -> None:
        gen = _make_generator()
        out_dir = tmp_path / ".specforge" / "features" / "ledger-service"
        out_dir.mkdir(parents=True)
        spec_file = out_dir / "spec.md"
        spec_file.write_text(_make_spec_text_with_match(), encoding="utf-8")
        ctx = ServiceContext(
            service_slug="ledger-service",
            service_name="Ledger Service",
            architecture="microservice",
            project_description="Personal Finance Tracker",
            domain="finance",
            features=(),
            dependencies=(),
            events=(),
            output_dir=out_dir,
        )
        m = _make_match(text="appropriately", line_number=5)
        questions = gen.generate((m,), ctx)
        assert questions[0].context_excerpt != ""


class TestPersonalFinanceLedger:
    """End-to-end: PersonalFinance ledger-service with 2 features."""

    def test_generates_questions_for_ledger(self) -> None:
        gen = _make_generator()
        matches = (
            _make_match(text="appropriately", line_number=5, category="domain"),
            _make_match(
                text="TBD", line_number=15, category="technical",
                pattern_type="unspecified_choice",
            ),
        )
        ctx = _make_service_ctx()
        questions = gen.generate(matches, ctx)
        assert len(questions) >= 1

    def test_all_questions_reference_source_match(self) -> None:
        gen = _make_generator()
        m = _make_match()
        questions = gen.generate((m,), _make_service_ctx())
        assert questions[0].source_match == m
