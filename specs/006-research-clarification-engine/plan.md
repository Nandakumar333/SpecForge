# Implementation Plan: Research & Clarification Engine

**Branch**: `006-research-clarification-engine` | **Date**: 2026-03-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-research-clarification-engine/spec.md`

## Summary

Build two standalone CLI commands (`specforge clarify` and `specforge research`) that resolve unknowns in service specs before planning begins. The clarification engine uses pattern-based ambiguity detection with boundary analysis for microservice architectures. The research engine enhances the existing Phase 2 research pipeline with structured finding statuses (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING). Both commands integrate with Feature 004 manifest.json for service resolution and Feature 005 pipeline state tracking.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (interactive prompts + terminal output), Jinja2 3.x (template rendering) — all existing
**Storage**: File system — `.specforge/features/<slug>/` directories; spec.md (read/write), research.md (write), clarifications-report.md (write), manifest.json (read-only)
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting) — all existing
**Target Platform**: Cross-platform (Windows, macOS, Linux) CLI tool
**Project Type**: CLI tool (extension of existing SpecForge)
**Performance Goals**: Clarify session completes pattern scan in <2s for typical spec; research generation in <5s
**Constraints**: No external network calls; all analysis uses embedded heuristics and pattern matching
**Scale/Scope**: Typical service spec is 200-500 lines; manifest.json contains 5-15 services

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | PASS | spec.md and plan.md exist before implementation |
| II. Architecture | PASS | All new modules in `core/`; templates use Jinja2; no string concat for output |
| III. Code Quality | PASS | Strict type hints; functions ≤30 lines; Result[T] for errors; constructor injection; constants in config.py |
| IV. Testing | PASS | TDD — tests written before implementation; unit + integration + snapshot coverage |
| V. Commit Strategy | PASS | Conventional Commits; one commit per task |
| VI. File Structure | PASS | New modules in `src/specforge/core/`; CLI in `cli/`; templates in `templates/base/features/` |
| VII. Governance | PASS | Constitution supersedes; no conflicts with governance prompts |

## Project Structure

### Documentation (this feature)

```text
specs/006-research-clarification-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── clarify-cmd.md   # CLI contract for specforge clarify
│   └── research-cmd.md  # CLI contract for specforge research
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── clarify_cmd.py           # specforge clarify <service> [--report]
│   └── research_cmd.py          # specforge research <service>
├── core/
│   ├── clarification_analyzer.py # AmbiguityScanner — pattern-based detection
│   ├── question_generator.py     # QuestionGenerator — creates ClarificationQuestions
│   ├── research_resolver.py      # ResearchResolver — resolves NEEDS CLARIFICATION
│   ├── boundary_analyzer.py      # BoundaryAnalyzer — cross-service entity detection
│   ├── clarification_recorder.py # ClarificationRecorder — appends Q&A to spec.md
│   └── clarification_models.py   # Frozen dataclasses: AmbiguityPattern, ClarificationQuestion, etc.
├── templates/base/features/
│   ├── clarifications-report.md.j2  # Report-mode template
│   └── research.md.j2              # Enhanced research template (existing, modified)

tests/
├── unit/
│   ├── test_clarification_analyzer.py
│   ├── test_question_generator.py
│   ├── test_research_resolver.py
│   ├── test_boundary_analyzer.py
│   └── test_clarification_recorder.py
├── integration/
│   ├── test_clarify_cmd.py
│   └── test_research_cmd.py
└── snapshots/
    └── test_clarification_templates.py
```

**Structure Decision**: Single project structure. New modules follow existing `core/` + `cli/` separation. The clarify and research commands are standalone CLI commands (not pipeline phases) — they run independently before `specforge specify`, enhancing spec.md and research.md in-place.

## Complexity Tracking

No constitution violations to justify.

## Design Decisions

### D1: Standalone Commands vs Pipeline Phases

The `clarify` and `research` commands are standalone CLI commands, NOT pipeline phases. Rationale:
- Clarify is interactive and should be run ad-hoc before pipeline execution
- Research as a command allows running research independently of the full pipeline
- The existing `ResearchPhase` in the pipeline remains unchanged — `specforge research` is a separate enhanced entry point that produces compatible research.md
- Both commands share the service resolution logic from Feature 005 (`resolve_target`)

### D2: Ambiguity Detection Architecture

Three-layer detection:
1. **AmbiguityScanner** (`clarification_analyzer.py`): Regex + keyword matching against spec.md text. Returns raw ambiguity hits with location and category.
2. **BoundaryAnalyzer** (`boundary_analyzer.py`): Reads manifest.json to find entities/concepts referenced across multiple services. Returns service-boundary ambiguities.
3. **QuestionGenerator** (`question_generator.py`): Takes raw ambiguity hits + boundary hits, deduplicates, ranks by impact, and generates ClarificationQuestions with suggested answers.

### D3: Research Resolver Strategy

`ResearchResolver` scans spec.md (required) and plan.md (optional) for:
- Explicit `NEEDS CLARIFICATION` markers (regex: `\[NEEDS CLARIFICATION:.*?\]`)
- Technology references (library names, protocol mentions, framework references)
- Architecture-specific topics (from ArchitectureAdapter.get_research_extras())

Produces structured ResearchFinding objects with 4 statuses:
- RESOLVED: Verified via embedded knowledge
- UNVERIFIED: Found but cannot confirm without external sources
- BLOCKED: Requires human input
- CONFLICTING: Multiple sources disagree; lists alternatives

### D4: Interactive Flow

Uses Rich `Prompt.ask` with numbered options (consistent with Feature 004's decompose flow). Questions presented one at a time. User can: select option letter, type custom answer, or type "skip". Session tracks answered/skipped state. On completion, ClarificationRecorder writes to spec.md.

### D5: Spec.md Modification Strategy

ClarificationRecorder uses append-only strategy:
1. Parse spec.md to find existing `## Clarifications` section (or determine insertion point)
2. Find or create `### Session YYYY-MM-DD` subsection
3. Append `- Q: [{category}] {question_text} → A: {answer_text}` bullet per answered question (category tag enables mark_revalidation to identify architecture-related entries)
4. Write atomically via temp file + `os.replace()` (consistent with manifest_writer pattern)
5. Clarify command acquires pipeline lock before writing to prevent data loss from concurrent sessions

### D6: Architecture-Change Detection

Manifest.json metadata is checked for a `previous_architecture` field (added by `--remap`). If present and differs from current `architecture`, the engine generates additional questions about service boundaries, communication patterns, and data ownership. Only architecture-related clarifications from previous sessions are flagged for re-validation.

### D7: Template Integration

- `clarifications-report.md.j2`: New template for `--report` mode output
- `research.md.j2`: Existing template enhanced with CONFLICTING status support and structured finding format
- Both use TemplateRegistry discovery (built-in + user overrides)

## Module Design

### clarification_models.py (Frozen Dataclasses)

```
AmbiguityMatch
├── text: str              # Matched text from spec
├── line_number: int       # Location in spec.md
├── category: AmbiguityCategory  # domain | technical | service_boundary | communication
├── pattern_type: str      # vague_term | undefined_concept | missing_boundary | arch_change
└── confidence: float      # 0.0-1.0 match confidence

ClarificationQuestion
├── id: str                # Unique question ID (e.g., "CQ-001")
├── category: AmbiguityCategory
├── context_excerpt: str   # Relevant spec section excerpt
├── question_text: str     # The actual question
├── suggested_answers: tuple[SuggestedAnswer, ...]  # 2-4 options
├── source_match: AmbiguityMatch
└── impact_rank: int       # 1 = highest impact

SuggestedAnswer
├── label: str             # "A", "B", "C", "D"
├── text: str              # Answer text
└── implications: str      # What this choice means

ClarificationAnswer
├── question_id: str
├── answer_text: str
├── is_custom: bool        # True if user typed custom answer
└── answered_at: str       # ISO timestamp

ResearchFinding
├── topic: str
├── summary: str
├── source: str            # "embedded-knowledge" | "spec-reference" | "manifest-metadata"
├── status: FindingStatus  # RESOLVED | UNVERIFIED | BLOCKED | CONFLICTING
├── originating_marker: str  # The spec text that triggered this finding
└── alternatives: tuple[str, ...]  # Non-empty only for CONFLICTING status

AmbiguityCategory = Literal["domain", "technical", "service_boundary", "communication"]
FindingStatus = Literal["RESOLVED", "UNVERIFIED", "BLOCKED", "CONFLICTING"]
```

### clarification_analyzer.py (AmbiguityScanner)

Constructor injection: `AmbiguityScanner(patterns: tuple[AmbiguityPattern, ...])`

Default patterns provided by factory function `default_patterns() -> tuple[AmbiguityPattern, ...]` covering:
- **Vague terms**: "appropriate", "as needed", "suitable", "proper", "relevant", "etc.", "various", "robust", "intuitive", "flexible"
- **Undefined concepts**: Domain terms without prior definition (detected via first-occurrence heuristic)
- **Missing boundaries**: Sections mentioning features without explicit scope limits
- **Unspecified choices**: "or" / "either" without resolution; questions in spec text

Methods:
- `scan(spec_text: str) -> tuple[AmbiguityMatch, ...]` — Returns all matches sorted by line number
- `scan_for_category(spec_text: str, category: AmbiguityCategory) -> tuple[AmbiguityMatch, ...]` — Filtered scan

### boundary_analyzer.py (BoundaryAnalyzer)

Constructor injection: `BoundaryAnalyzer(manifest: dict)` — receives parsed manifest.json

Methods:
- `analyze(service_slug: str) -> tuple[AmbiguityMatch, ...]` — Finds concepts shared across service boundaries
- `detect_remap(manifest: dict) -> bool` — Checks for `previous_architecture` field
- `get_remap_questions(service_slug: str) -> tuple[AmbiguityMatch, ...]` — Architecture-change-specific ambiguities

Logic:
1. Extract all feature keywords/entities from each service's feature descriptions
2. For target service, find keywords that also appear in other services' features
3. Generate service-boundary AmbiguityMatch for each shared concept
4. If remap detected, add data-ownership and communication-pattern questions

### question_generator.py (QuestionGenerator)

Constructor injection: `QuestionGenerator()`

Methods:
- `generate(matches: tuple[AmbiguityMatch, ...], service_ctx: ServiceContext) -> tuple[ClarificationQuestion, ...]`
  - Deduplicates overlapping matches
  - Ranks by impact: service_boundary > domain > technical > communication
  - Generates 2-4 suggested answers per question based on category
  - Returns questions sorted by impact_rank

### research_resolver.py (ResearchResolver)

Constructor injection: `ResearchResolver(adapter: ArchitectureAdapter)`

Methods:
- `resolve(spec_text: str, plan_text: str | None, service_ctx: ServiceContext) -> tuple[ResearchFinding, ...]`
  - Scans for NEEDS CLARIFICATION markers
  - Scans for technology/library references
  - Adds architecture-specific topics from adapter
  - Returns findings with appropriate status

- `merge_findings(existing: tuple[ResearchFinding, ...], new: tuple[ResearchFinding, ...]) -> tuple[ResearchFinding, ...]`
  - Preserves RESOLVED findings from existing
  - Re-evaluates BLOCKED findings
  - Adds new findings not in existing set

### clarification_recorder.py (ClarificationRecorder)

Constructor injection: `ClarificationRecorder()`

Methods:
- `record(spec_path: Path, answers: tuple[ClarificationAnswer, ...], questions: tuple[ClarificationQuestion, ...]) -> Result[Path, str]`
  - Reads spec.md
  - Finds or creates `## Clarifications` section
  - Finds or creates `### Session YYYY-MM-DD` subsection
  - Appends Q&A bullets
  - Writes atomically via temp file + os.replace()
  - Returns Ok(spec_path) or Err(error_message)

- `mark_revalidation(spec_path: Path, categories: tuple[AmbiguityCategory, ...]) -> Result[Path, str]`
  - After remap, marks architecture-related clarifications as needing re-validation
  - Adds `[NEEDS RE-VALIDATION]` tag to affected entries

### CLI Commands

**clarify_cmd.py**:
```
specforge clarify <target> [--report]

1. Resolve target → service_slug via manifest.json
2. Load spec.md from .specforge/features/<slug>/
3. Load manifest.json for boundary analysis
4. Run AmbiguityScanner.scan(spec_text)
5. Run BoundaryAnalyzer.analyze(service_slug)
6. If remap detected: add BoundaryAnalyzer.get_remap_questions()
7. Run QuestionGenerator.generate(all_matches, service_ctx)
8. If --report: render clarifications-report.md.j2 → write file → exit
9. If interactive: present questions via Rich prompts → collect answers
10. Run ClarificationRecorder.record(spec_path, answers, questions)
11. Display summary
```

**research_cmd.py**:
```
specforge research <target>

1. Resolve target → service_slug via manifest.json
2. Load spec.md (required) and plan.md (optional)
3. Get ArchitectureAdapter for service architecture
4. Run ResearchResolver.resolve(spec_text, plan_text, service_ctx)
5. If existing research.md: merge_findings(existing, new)
6. Render research.md.j2 with findings context
7. Write research.md to .specforge/features/<slug>/
8. Update .pipeline-state.json research phase status
9. Display summary with finding status counts
```

## Integration Points

### With Feature 004 (manifest.json)

- Read-only access to `.specforge/manifest.json`
- Uses `resolve_target()` from Feature 005 for service slug resolution
- BoundaryAnalyzer reads `services[].features[]` and `services[].communication[]`
- Remap detection checks for `previous_architecture` field in manifest metadata

### With Feature 005 (Pipeline)

- `specforge research` writes research.md compatible with ResearchPhase output
- Updates `.pipeline-state.json` research phase to "complete" after successful run
- `specforge clarify` modifies spec.md which is Phase 1 input — does NOT update pipeline state
- Both commands acquire `.pipeline-lock` via `acquire_lock()` to prevent concurrent modification (covers both pipeline-vs-clarify and clarify-vs-clarify conflicts)

### With Feature 003 (PromptContextBuilder)

- Research command optionally uses PromptContextBuilder to add tech-stack-specific research topics
- Graceful fallback if governance prompt files don't exist (same pattern as specify_cmd.py)

### With Feature 002 (TemplateRegistry)

- Both commands use TemplateRegistry for template discovery
- User template overrides supported via `.specforge/templates/features/`

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | PASS | Spec and plan complete before implementation |
| II. Architecture | PASS | Core modules in `core/`; Jinja2 templates for output; no string concat |
| III. Code Quality | PASS | All functions ≤30 lines; Result[T] errors; constructor injection; frozen dataclasses |
| IV. Testing | PASS | TDD with unit (5 modules), integration (2 commands), snapshot (1 template) |
| V. Commit Strategy | PASS | Conventional commits per task |
| VI. File Structure | PASS | `core/` for domain logic, `cli/` for commands, `templates/` for Jinja2 |
| VII. Governance | PASS | No conflicts |
