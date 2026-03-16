"""QuestionGenerator — creates ClarificationQuestions from ambiguity matches."""

from __future__ import annotations

from specforge.core.clarification_models import (
    AmbiguityMatch,
    ClarificationQuestion,
    SuggestedAnswer,
)
from specforge.core.config import ANSWER_TEMPLATES, IMPACT_PRIORITY

_DEDUP_PROXIMITY = 3
_LABELS = ("A", "B", "C", "D")


class QuestionGenerator:
    """Generates ranked clarification questions from ambiguity matches."""

    def generate(
        self,
        matches: tuple[AmbiguityMatch, ...],
        service_ctx: object,
    ) -> tuple[ClarificationQuestion, ...]:
        """Deduplicate, rank, and convert matches to questions."""
        if not matches:
            return ()
        deduped = _deduplicate(matches)
        ranked = sorted(deduped, key=lambda m: IMPACT_PRIORITY.get(
            m.category, 99,
        ))
        spec_lines = _get_spec_lines(service_ctx)
        questions: list[ClarificationQuestion] = []
        for idx, match in enumerate(ranked):
            questions.append(_build_question(
                idx, match, spec_lines, service_ctx,
            ))
        return tuple(questions)


def _deduplicate(
    matches: tuple[AmbiguityMatch, ...],
) -> list[AmbiguityMatch]:
    """Remove matches within DEDUP_PROXIMITY lines of each other."""
    if not matches:
        return []
    by_line = sorted(matches, key=lambda m: m.line_number)
    result: list[AmbiguityMatch] = [by_line[0]]
    for m in by_line[1:]:
        if m.line_number - result[-1].line_number > _DEDUP_PROXIMITY:
            result.append(m)
        elif IMPACT_PRIORITY.get(m.category, 99) < IMPACT_PRIORITY.get(
            result[-1].category, 99,
        ):
            result[-1] = m
    return result


def _get_spec_lines(service_ctx: object) -> list[str]:
    """Extract spec lines from service context output_dir if available."""
    try:
        output_dir = getattr(service_ctx, "output_dir", None)
        if output_dir is not None:
            spec_path = output_dir / "spec.md"
            if spec_path.exists():
                return spec_path.read_text(encoding="utf-8").splitlines()
    except (OSError, AttributeError):
        pass
    return []


def _build_question(
    idx: int,
    match: AmbiguityMatch,
    spec_lines: list[str],
    service_ctx: object,
) -> ClarificationQuestion:
    """Build a single ClarificationQuestion from an AmbiguityMatch."""
    qid = f"CQ-{idx + 1:03d}"
    excerpt = _extract_context(match.line_number, spec_lines)
    question_text = _question_for_match(match)
    answers = _build_answers(match, service_ctx)
    return ClarificationQuestion(
        id=qid,
        category=match.category,
        context_excerpt=excerpt,
        question_text=question_text,
        suggested_answers=answers,
        source_match=match,
        impact_rank=IMPACT_PRIORITY.get(match.category, 99),
    )


def _extract_context(
    line_num: int, spec_lines: list[str],
) -> str:
    """Extract 3 lines before/after the match for context."""
    if not spec_lines:
        return ""
    start = max(0, line_num - 4)
    end = min(len(spec_lines), line_num + 3)
    return "\n".join(spec_lines[start:end]).strip()


def _question_for_match(match: AmbiguityMatch) -> str:
    """Generate a human-readable question from an ambiguity match."""
    text = match.text.strip('"').strip("'")
    prompts = {
        "vague_term": f'What does "{text}" specifically mean in this context?',
        "undefined_concept": f'How is "{text}" defined for this project?',
        "missing_boundary": f'What is the intended resolution for: "{text}"?',
        "unspecified_choice": f'What decision has been made regarding: "{text}"?',
    }
    return prompts.get(match.pattern_type, f'Clarify: "{text}"')


def _build_answers(
    match: AmbiguityMatch, service_ctx: object,
) -> tuple[SuggestedAnswer, ...]:
    """Build suggested answers from ANSWER_TEMPLATES for the category."""
    templates = ANSWER_TEMPLATES.get(match.category, ())
    concept = match.text.strip('"').strip("'")
    slug_a = getattr(service_ctx, "service_slug", "this-service")
    slug_b = "other-service"
    try:
        deps = getattr(service_ctx, "dependencies", ())
        if deps:
            slug_b = deps[0].target_slug
    except (AttributeError, IndexError):
        pass

    answers: list[SuggestedAnswer] = []
    for i, tmpl in enumerate(templates[:4]):
        text = tmpl.format(
            concept=concept, service_a=slug_a, service_b=slug_b,
        )
        answers.append(SuggestedAnswer(
            label=_LABELS[i],
            text=text,
            implications=f"Choosing this affects how {concept} is handled",
        ))
    return tuple(answers)
