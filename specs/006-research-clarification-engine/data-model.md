# Data Model — Research & Clarification Engine

**Feature**: 006-research-clarification-engine
**Date**: 2026-03-16

## Entities

### AmbiguityCategory (Enum)

| Value | Description |
|-------|-------------|
| domain | Business/domain concept ambiguity |
| technical | Technology/implementation choice ambiguity |
| service_boundary | Cross-service ownership ambiguity |
| communication | Service communication pattern ambiguity |

### FindingStatus (Enum)

| Value | Description |
|-------|-------------|
| RESOLVED | Verified via embedded knowledge |
| UNVERIFIED | Found but cannot confirm without external sources |
| BLOCKED | Requires human input to resolve |
| CONFLICTING | Multiple sources disagree; alternatives listed |

### AmbiguityPattern (Value Object)

| Field | Type | Description |
|-------|------|-------------|
| pattern_type | str | "vague_term", "undefined_concept", "missing_boundary", "unspecified_choice" |
| regex | str | Compiled regex pattern for matching |
| category | AmbiguityCategory | Which category this pattern detects |
| description | str | Human-readable description of what this pattern catches |

Immutable. Provided as a tuple to AmbiguityScanner via constructor injection.

### AmbiguityMatch (Value Object)

| Field | Type | Description |
|-------|------|-------------|
| text | str | Matched text from spec |
| line_number | int | Line number in spec.md |
| category | AmbiguityCategory | Categorization |
| pattern_type | str | Which pattern type triggered this |
| confidence | float | 0.0-1.0 match confidence score |

Immutable. Produced by AmbiguityScanner.scan() and BoundaryAnalyzer.analyze().

### SuggestedAnswer (Value Object)

| Field | Type | Description |
|-------|------|-------------|
| label | str | Option label: "A", "B", "C", "D" |
| text | str | Answer text |
| implications | str | What choosing this answer means for the project |

Immutable. 2-4 per ClarificationQuestion.

### ClarificationQuestion (Entity)

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique ID (e.g., "CQ-001") |
| category | AmbiguityCategory | Question category |
| context_excerpt | str | Relevant spec section excerpt |
| question_text | str | The question to ask |
| suggested_answers | tuple[SuggestedAnswer, ...] | 2-4 suggested options |
| source_match | AmbiguityMatch | The ambiguity that generated this |
| impact_rank | int | Priority (1 = highest impact) |

Identity: `id` field. Immutable after creation.

### ClarificationAnswer (Value Object)

| Field | Type | Description |
|-------|------|-------------|
| question_id | str | References ClarificationQuestion.id |
| answer_text | str | The user's selected or custom answer |
| is_custom | bool | True if user typed a custom answer |
| answered_at | str | ISO 8601 timestamp |

Immutable. Produced during interactive session.

### ClarificationSession (Aggregate)

| Field | Type | Description |
|-------|------|-------------|
| service_slug | str | Target service |
| questions | tuple[ClarificationQuestion, ...] | All generated questions |
| answers | tuple[ClarificationAnswer, ...] | User's answers (subset of questions) |
| skipped_ids | tuple[str, ...] | Question IDs the user skipped |
| is_report_mode | bool | True if --report flag was used |
| session_date | str | ISO date (YYYY-MM-DD) |

Aggregate root for one clarify run. Not persisted as JSON — answers are recorded directly into spec.md.

### ResearchFinding (Entity)

| Field | Type | Description |
|-------|------|-------------|
| topic | str | Research topic name |
| summary | str | Finding summary text |
| source | str | "embedded-knowledge", "spec-reference", "manifest-metadata" |
| status | FindingStatus | Resolution status |
| originating_marker | str | Spec text that triggered this finding |
| alternatives | tuple[str, ...] | Non-empty only for CONFLICTING status |

Identity: `topic` field (unique per research.md). Immutable.

### ResearchContext (Value Object)

| Field | Type | Description |
|-------|------|-------------|
| architecture | str | "monolithic", "microservice", "modular-monolith" |
| communication_patterns | tuple[str, ...] | From manifest service communication links |
| tech_references | tuple[str, ...] | Libraries/frameworks mentioned in spec/plan |
| clarification_markers | tuple[str, ...] | NEEDS CLARIFICATION text extracted from spec/plan |
| adapter_extras | tuple[dict, ...] | Architecture-specific research topics |

Immutable. Built by ResearchResolver from spec.md + plan.md + manifest.json.

## Relationships

```text
AmbiguityScanner ──uses──> AmbiguityPattern (1:N)
AmbiguityScanner ──produces──> AmbiguityMatch (1:N)
BoundaryAnalyzer ──produces──> AmbiguityMatch (1:N)
QuestionGenerator ──consumes──> AmbiguityMatch (N:1)
QuestionGenerator ──produces──> ClarificationQuestion (1:N)
ClarificationQuestion ──contains──> SuggestedAnswer (1:2..4)
ClarificationQuestion ──references──> AmbiguityMatch (1:1)
ClarificationSession ──contains──> ClarificationQuestion (1:N)
ClarificationSession ──contains──> ClarificationAnswer (1:N)
ClarificationAnswer ──references──> ClarificationQuestion (N:1)
ClarificationRecorder ──reads/writes──> spec.md
ResearchResolver ──produces──> ResearchFinding (1:N)
ResearchResolver ──uses──> ResearchContext (1:1)
```

## State Transitions

### ClarificationQuestion Lifecycle

```
[Generated] → [Presented] → [Answered] or [Skipped]
```

- Generated: QuestionGenerator creates from AmbiguityMatch
- Presented: Shown to user in interactive mode
- Answered: User selected option or provided custom answer → recorded in spec.md
- Skipped: User chose to skip → NOT recorded, will reappear on next run

### ResearchFinding Lifecycle

```
[New] → [RESOLVED] or [UNVERIFIED] or [BLOCKED] or [CONFLICTING]

On re-run:
[RESOLVED] → [RESOLVED] (preserved)
[BLOCKED] → re-evaluated → any status
[UNVERIFIED] → re-evaluated → any status
[CONFLICTING] → re-evaluated → any status
```
