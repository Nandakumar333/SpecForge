# Tasks: Research & Clarification Engine

**Input**: Design documents from `/specs/006-research-clarification-engine/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD — all test tasks MUST be written and FAIL before implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/specforge/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Project initialization — new module files, constants, and config additions

- [X] T001 Add new constants to `src/specforge/core/config.py`: `AMBIGUITY_CATEGORIES` (tuple of "domain", "technical", "service_boundary", "communication"), `FINDING_STATUSES` (tuple of "RESOLVED", "UNVERIFIED", "BLOCKED", "CONFLICTING"), `VAGUE_TERM_PATTERNS` (tuple of regex strings with word-form variants: "appropriate(ly)?", "as needed", "suitable|suitably", "proper(ly)?", "relevant", "etc\\.", "various", "robust(ly|ness)?", "intuitive(ly)?", "flexible|flexibility"), `CLARIFICATION_SECTION_HEADING` = "## Clarifications", `SESSION_HEADING_PREFIX` = "### Session", `CLARIFICATION_REPORT_FILENAME` = "clarifications-report.md", `BOUNDARY_STOP_WORDS` (frozenset of common English stop words: "the", "a", "an", "and", "or", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "it", "its", "this", "that", "be", "has", "have", "had", "not", "will", "can", "should", "must", "each", "all", "any", "service", "system"), `ANSWER_TEMPLATES` (dict mapping AmbiguityCategory → tuple of template strings used by QuestionGenerator to generate suggested answers: domain → ("Define specific business rules for {concept}", "Use industry-standard definition of {concept}", "Defer to domain expert for {concept} requirements", "Split {concept} into sub-categories with separate rules"), technical → ("Use {concept} with default configuration", "Evaluate alternatives to {concept} before committing", "Use {concept} for MVP, revisit for production"), service_boundary → ("{concept} owned by {service_a}", "{concept} owned by {service_b}", "Extract {concept} into shared library", "Duplicate {concept} with eventual consistency"), communication → ("Synchronous (REST/gRPC) for {concept}", "Asynchronous (events/messages) for {concept}", "Hybrid: sync for queries, async for commands"))
- [X] T002 Create frozen dataclass models in `src/specforge/core/clarification_models.py`: `AmbiguityCategory` (Literal type), `FindingStatus` (Literal type), `AmbiguityPattern` (frozen dataclass with fields: pattern_type str, regex str, category AmbiguityCategory, description str), `AmbiguityMatch` (frozen dataclass with fields: text str, line_number int, category AmbiguityCategory, pattern_type str, confidence float), `SuggestedAnswer` (frozen dataclass with fields: label str, text str, implications str), `ClarificationQuestion` (frozen dataclass with fields: id str, category AmbiguityCategory, context_excerpt str, question_text str, suggested_answers tuple[SuggestedAnswer, ...], source_match AmbiguityMatch, impact_rank int), `ClarificationAnswer` (frozen dataclass with fields: question_id str, answer_text str, is_custom bool, answered_at str), `ClarificationSession` (frozen dataclass with fields: service_slug str, questions tuple[ClarificationQuestion, ...], answers tuple[ClarificationAnswer, ...], skipped_ids tuple[str, ...], is_report_mode bool, session_date str), `ResearchFinding` (frozen dataclass with fields: topic str, summary str, source str, status FindingStatus, originating_marker str, alternatives tuple[str, ...]), `ResearchContext` (frozen dataclass with fields: architecture str, communication_patterns tuple[str, ...], tech_references tuple[str, ...], clarification_markers tuple[str, ...], adapter_extras tuple[dict, ...])

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `default_patterns()` factory function in `src/specforge/core/clarification_analyzer.py` that returns `tuple[AmbiguityPattern, ...]` with patterns for all 4 pattern types: vague_term (regex matching word-form variants from VAGUE_TERM_PATTERNS in config.py — patterns already include adverb/adjective variants like `appropriate(ly)?`, case-insensitive, word-boundary aware), undefined_concept (regex matching capitalized multi-word terms or quoted terms not previously defined in the document), missing_boundary (regex matching "or"/"either" between options without resolution, and question marks in non-heading lines), unspecified_choice (regex matching phrases like "TBD", "to be determined", "not yet decided"). Each pattern must have category, description, and compiled regex string. Import constants from config.py — no magic strings.
- [X] T004 Create `clarifications-report.md.j2` template in `src/specforge/templates/base/features/clarifications-report.md.j2` using Jinja2 with generation header partial include. Template accepts context: `service` (dict with slug, name), `date` (str), `questions` (list of dicts with id, category, context_excerpt, question_text, suggested_answers list of dicts with label/text/implications), `architecture` (str). Render grouped by category with markdown table of suggested answers per question.

**Checkpoint**: Foundation ready — models, patterns, and templates available for all user stories

---

## Phase 3: User Story 1 — Clarify Service-Specific Ambiguities (Priority: P1) MVP

**Goal**: Run `specforge clarify <service>` to detect ambiguities in spec.md and generate structured clarification questions with categorized output

**Independent Test**: Run `specforge clarify ledger-service` against a spec.md containing known vague terms ("transactions should be processed appropriately") and verify categorized questions are generated, including cross-feature gaps for a 2-feature service (accounts + transactions)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [P] [US1] Unit tests for AmbiguityScanner in `tests/unit/test_clarification_analyzer.py`: test `scan()` detects vague terms ("appropriate", "as needed", "etc.") with correct line numbers and category=domain; test `scan()` detects unspecified choices ("either X or Y") with category=technical; test `scan()` detects missing boundaries with category=domain; test `scan()` returns empty tuple for spec text with no ambiguities; test `scan_for_category()` filters results correctly; test all matches are sorted by line_number; test confidence is between 0.0 and 1.0; test with PersonalFinance ledger-service spec containing "transactions should be processed appropriately" returns at least 1 domain match; test with multi-feature spec covering accounts AND transactions returns matches from both feature areas
- [X] T006 [P] [US1] Unit tests for QuestionGenerator in `tests/unit/test_question_generator.py`: test `generate()` creates ClarificationQuestion with 2-4 SuggestedAnswers per match; test deduplication removes overlapping matches on same line; test impact ranking orders service_boundary > domain > technical > communication; test question IDs are sequential ("CQ-001", "CQ-002"); test context_excerpt contains surrounding text from spec; test with empty matches tuple returns empty tuple; test with PersonalFinance ledger-service ServiceContext (2 features: accounts, transactions) generates questions mentioning both feature areas
- [X] T007 [P] [US1] Unit tests for ClarificationRecorder in `tests/unit/test_clarification_recorder.py`: test `record()` creates new `## Clarifications` section when none exists; test `record()` appends to existing Clarifications section without replacing; test `record()` creates `### Session YYYY-MM-DD` subsection; test `record()` writes `- Q: [{category}] {question_text} → A: {answer_text}` format per answered question (category tag required for mark_revalidation support); test `record()` uses atomic write (temp file + os.replace); test `record()` returns Ok(path) on success; test `record()` returns Err when spec_path doesn't exist; test skipped questions are NOT recorded; test with multiple answers all appear in correct session subsection; test existing Clarifications from prior session are preserved verbatim
- [X] T008 [P] [US1] Integration test for clarify command in `tests/integration/test_clarify_cmd.py`: test `specforge clarify ledger-service` with CliRunner against tmp_path containing manifest.json (PersonalFinance microservice with ledger-service mapping features 002-accounts + 003-transactions, and planning-service mapping features 004-budgets + 005-goals + 006-bills) and spec.md containing known vague terms exits 0; test missing manifest.json exits 1 with error message; test missing spec.md exits 1 with error message; test service slug not in manifest exits 1 listing available services; test "No ambiguities detected" message when spec has no patterns; test feature number resolution (e.g., "002" resolves to ledger-service); **test SC-004 duplicate suppression: first run answers questions, second run on unchanged spec produces zero new duplicate questions; test answer-introduces-ambiguity: first run records answer containing vague term "as needed", second run detects that term as new ambiguity**

### Implementation for User Story 1

- [X] T009 [US1] Implement `AmbiguityScanner` class in `src/specforge/core/clarification_analyzer.py` with constructor `__init__(self, patterns: tuple[AmbiguityPattern, ...])` and methods: `scan(self, spec_text: str) -> tuple[AmbiguityMatch, ...]` iterates lines, applies each pattern's regex, creates AmbiguityMatch with line_number/category/confidence, returns sorted by line_number; `scan_for_category(self, spec_text: str, category: AmbiguityCategory) -> tuple[AmbiguityMatch, ...]` filters scan results. Functions ≤30 lines. Use Result type for any error paths. Import AmbiguityPattern/AmbiguityMatch from clarification_models.
- [X] T010 [US1] Implement `QuestionGenerator` class in `src/specforge/core/question_generator.py` with constructor `__init__(self)` and method: `generate(self, matches: tuple[AmbiguityMatch, ...], service_ctx: ServiceContext) -> tuple[ClarificationQuestion, ...]` that deduplicates matches by line proximity (within 3 lines), ranks by IMPACT_PRIORITY order (service_boundary=1, domain=2, technical=3, communication=4), generates 2-4 SuggestedAnswers per question **using ANSWER_TEMPLATES from config.py** — templates are per-category string patterns with `{concept}` and `{service_a}`/`{service_b}` placeholders filled from the matched text and service context, extracts context_excerpt (3 lines before/after match), assigns sequential IDs ("CQ-001", "CQ-002"). Functions ≤30 lines.
- [X] T011 [US1] Implement `ClarificationRecorder` class in `src/specforge/core/clarification_recorder.py` with constructor `__init__(self)` and method: `record(self, spec_path: Path, answers: tuple[ClarificationAnswer, ...], questions: tuple[ClarificationQuestion, ...]) -> Result[Path, str]` that reads spec_path, finds `## Clarifications` section (or inserts before `## Assumptions` if not found), finds or creates `### Session YYYY-MM-DD` subsection, appends `- Q: [{category}] {question_text} → A: {answer_text}` per answer (matching question_id to questions tuple for question_text and category; category tag is required so mark_revalidation can identify architecture-related entries), writes atomically via tempfile + os.replace(). Returns Ok(spec_path) or Err(message). Functions ≤30 lines.
- [X] T012 [US1] Implement `clarify` Click command in `src/specforge/cli/clarify_cmd.py`: `@click.command("clarify")` with `@click.argument("target")` and `@click.option("--report", is_flag=True)`. Command flow: resolve target via `resolve_target()` from spec_pipeline module, load manifest.json, validate spec.md exists, **acquire pipeline lock via `acquire_lock()` from pipeline_lock module (prevents concurrent clarify sessions and pipeline conflicts on the same service; release in finally block)**, create AmbiguityScanner with default_patterns(), run scan(), create QuestionGenerator and generate questions, if --report render clarifications-report.md.j2 via TemplateRenderer and write to service output dir, if no ambiguities print "No ambiguities detected" and exit 0, if interactive present questions via Rich Prompt.ask() one at a time (options A/B/C/D + "skip"), collect ClarificationAnswers, call ClarificationRecorder.record(), display summary. Use Rich Console for all output.
- [X] T013 [US1] Register `clarify` command in `src/specforge/cli/main.py`: import `clarify` from `clarify_cmd` and add `cli.add_command(clarify)` following existing pattern for specify/decompose commands

**Checkpoint**: At this point, `specforge clarify <service>` works end-to-end with pattern detection, question generation, interactive flow, and spec.md recording

---

## Phase 4: User Story 2 — Research Technical Unknowns (Priority: P1)

**Goal**: Run `specforge research <service>` to scan spec.md/plan.md for unknowns and produce research.md with structured findings (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING)

**Independent Test**: Run `specforge research ledger-service` against a spec.md mentioning "gRPC for auth validation" and a manifest with architecture=microservice, verify research.md contains gRPC findings with status and microservice-specific topics

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [P] [US2] Unit tests for ResearchResolver in `tests/unit/test_research_resolver.py`: test `resolve()` extracts NEEDS CLARIFICATION markers via regex `\[NEEDS CLARIFICATION:.*?\]`; test `resolve()` identifies technology references (library names, protocol mentions); test `resolve()` adds adapter research extras for microservice architecture; test `resolve()` omits adapter extras for monolithic architecture; test `resolve()` assigns UNVERIFIED status for library version findings; test `resolve()` assigns BLOCKED status for unresolvable unknowns; test `resolve()` with plan_text=None processes spec_text only; test `merge_findings()` preserves RESOLVED from existing; test `merge_findings()` re-evaluates BLOCKED from existing; test `merge_findings()` adds new findings not in existing set; test with PersonalFinance ledger-service spec mentioning "gRPC for auth validation" returns finding with topic containing "gRPC"; **test microservice architecture injects container-level findings: Docker base image, health check endpoint, and message broker comparison findings are present when service_ctx.architecture="microservice" and async communication is declared (FR-018)**
- [X] T015 [P] [US2] Integration test for research command in `tests/integration/test_research_cmd.py`: test `specforge research ledger-service` with CliRunner against tmp_path containing PersonalFinance manifest.json (microservice, ledger-service with features 002+003) and spec.md mentioning technical unknowns exits 0 and creates research.md; test research.md contains structured findings with Status/Source/Triggered fields; test missing manifest exits 1; test missing spec.md exits 1; test with monolithic architecture omits microservice topics; test re-run merges with existing research.md preserving RESOLVED; test pipeline state updated to research=complete after successful run

### Implementation for User Story 2

- [X] T016 [US2] Implement `ResearchResolver` class in `src/specforge/core/research_resolver.py` with constructor `__init__(self, adapter: ArchitectureAdapter)` and methods: `resolve(self, spec_text: str, plan_text: str | None, service_ctx: ServiceContext) -> tuple[ResearchFinding, ...]` that scans for NEEDS CLARIFICATION markers (regex), scans for technology/library references (regex matching common lib name patterns), adds adapter.get_research_extras() as findings, **additionally for microservice architecture injects container-level findings (Docker base image recommendations, health check endpoints, gRPC library setup if gRPC referenced in spec/plan, message broker comparison if async communication declared in service context) per FR-018 — these supplement the adapter's generic research extras**, assigns status per finding (UNVERIFIED for version info, BLOCKED for unresolvable, RESOLVED for embedded-knowledge confirmations, CONFLICTING when multiple options exist); `merge_findings(self, existing: tuple[ResearchFinding, ...], new: tuple[ResearchFinding, ...]) -> tuple[ResearchFinding, ...]` that preserves RESOLVED from existing by topic, re-adds BLOCKED/UNVERIFIED from new, adds genuinely new topics. Functions ≤30 lines. Use Result type.
- [X] T017 [US2] Enhance existing `src/specforge/templates/base/features/research.md.j2` template to support CONFLICTING status: add conditional block for findings with status=CONFLICTING that renders `**Alternative A/B/C**: ...` lines from the alternatives list. Ensure template accepts `findings` context variable (list of dicts with topic, summary, source, status, originating_marker, alternatives). Keep backward compatibility with existing adapter_research_extras rendering.
- [X] T018 [US2] Implement `research` Click command in `src/specforge/cli/research_cmd.py`: `@click.command("research")` with `@click.argument("target")`. Command flow: resolve target via resolve_target(), load manifest.json, validate spec.md exists, load spec.md text + plan.md text (optional), get ArchitectureAdapter via architecture from manifest, create ResearchResolver(adapter), run resolve(), if existing research.md exists parse and merge_findings(), render research.md.j2 via TemplateRenderer with findings context, write research.md atomically, update .pipeline-state.json research phase to "complete" via pipeline_state functions, display Rich summary with finding status counts. Gracefully load PromptContextBuilder (try/except, same as specify_cmd.py).
- [X] T019 [US2] Register `research` command in `src/specforge/cli/main.py`: import `research` from `research_cmd` and add `cli.add_command(research)`

**Checkpoint**: At this point, `specforge research <service>` works end-to-end with finding generation, merging, template rendering, and pipeline state updates

---

## Phase 5: User Story 3 — Detect Architecture-Change Ambiguities (Priority: P2)

**Goal**: After `--remap`, clarification engine generates additional service-boundary/data-ownership questions and marks prior architecture-related clarifications for re-validation

**Independent Test**: Create a manifest with `previous_architecture: "monolithic"` and `architecture: "microservice"`, run `specforge clarify ledger-service`, verify remap-specific questions appear about service boundaries, data ownership, and communication patterns

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [P] [US3] Unit tests for BoundaryAnalyzer in `tests/unit/test_boundary_analyzer.py`: test `analyze()` with PersonalFinance manifest (ledger-service has features for accounts+transactions, planning-service has budgets+goals+bills) detects "categories" as shared concept between ledger and planning (including plural→singular stemming); test `analyze()` returns AmbiguityMatch with category=service_boundary; test `analyze()` with single-service manifest returns empty tuple; test `detect_remap()` returns True when manifest has `previous_architecture` differing from `architecture`; test `detect_remap()` returns False when no `previous_architecture` field; test `detect_remap()` returns False when previous equals current; test `get_remap_questions()` generates questions covering **all 5 topics from FR-013**: service boundaries, communication patterns, data ownership, shared state, eventual consistency; test `get_remap_questions()` returns at least 5 questions per service (one per FR-013 topic); test `analyze()` with 3+ services sharing a concept includes all boundary pairs; test with manifest where feature descriptions contain "categories" in both ledger and planning services returns service_boundary match; test keyword extraction filters BOUNDARY_STOP_WORDS and applies basic stemming
- [X] T021 [P] [US3] Unit tests for ClarificationRecorder.mark_revalidation in `tests/unit/test_clarification_recorder.py` (append to existing test file): test `mark_revalidation()` adds `[NEEDS RE-VALIDATION]` tag to service_boundary entries; test `mark_revalidation()` adds tag to communication entries; test `mark_revalidation()` preserves domain entries unchanged; test `mark_revalidation()` returns Ok when successful; test `mark_revalidation()` with no existing Clarifications section returns Ok with no changes

### Implementation for User Story 3

- [X] T022 [US3] Implement `BoundaryAnalyzer` class in `src/specforge/core/boundary_analyzer.py` with constructor `__init__(self, manifest: dict)` and methods: `analyze(self, service_slug: str) -> tuple[AmbiguityMatch, ...]` that extracts keywords from each service's feature descriptions (split on spaces, filter using BOUNDARY_STOP_WORDS from config.py, lowercase, **apply basic stemming: strip trailing 's'/'es', normalize 'ies'→'y' to match singular/plural variants**), finds keywords in target service that also appear in other services, creates AmbiguityMatch per shared concept with category=service_boundary and pattern_type="missing_boundary"; `detect_remap(self, manifest: dict) -> bool` checks for `previous_architecture` field differing from `architecture`; `get_remap_questions(self, service_slug: str) -> tuple[AmbiguityMatch, ...]` generates architecture-change AmbiguityMatch entries for **all 5 FR-013 topics**: service boundaries, communication patterns, data ownership, shared state, and eventual consistency (pattern_type="arch_change", category varies). Functions ≤30 lines.
- [X] T023 [US3] Implement `mark_revalidation()` method on ClarificationRecorder in `src/specforge/core/clarification_recorder.py`: `mark_revalidation(self, spec_path: Path, categories: tuple[AmbiguityCategory, ...]) -> Result[Path, str]` that reads spec_path, finds `## Clarifications` section, for each `- Q: [{category}]` line whose bracketed category tag matches a value in the provided categories tuple, appends ` [NEEDS RE-VALIDATION]` if not already present, writes atomically. Only affects entries with categories in the provided tuple (service_boundary, communication). Depends on T011 writing category tags in the `- Q: [{category}] ...` format.
- [X] T024 [US3] Wire BoundaryAnalyzer into clarify command in `src/specforge/cli/clarify_cmd.py`: after AmbiguityScanner.scan(), create BoundaryAnalyzer(manifest), call analyze(service_slug) to get boundary matches, call detect_remap() and if True call get_remap_questions() and mark_revalidation() on existing spec, combine all matches before passing to QuestionGenerator.generate()

**Checkpoint**: At this point, architecture-change detection is fully functional — remap triggers extra questions and marks prior answers for re-validation

---

## Phase 6: User Story 4 — Interactive Clarification Flow (Priority: P2)

**Goal**: Present questions interactively with Rich prompts, showing context excerpts and suggested answers with implications, supporting option selection, custom answers, and skip

**Independent Test**: Run clarify interactively, select option B for one question, type custom answer for another, skip a third — verify spec.md contains only answered questions with correct format

### Tests for User Story 4

- [X] T025 [P] [US4] Integration tests for interactive flow in `tests/integration/test_clarify_cmd.py` (append to existing file): test with simulated Rich input selecting option "A" records answer in spec.md; test with input "skip" does NOT record question in spec.md; test with custom text input records custom answer with is_custom=True; test summary output shows count of answered vs skipped; test spec.md Clarifications section has correct `- Q: ... → A: ...` format after interactive session

### Implementation for User Story 4

- [X] T026 [US4] Enhance interactive presentation in `src/specforge/cli/clarify_cmd.py`: for each ClarificationQuestion, display Rich-formatted output showing `Q{n} [{category}] ({n}/{total})` header, `Context: "{context_excerpt}"` in dim style, question_text in bold, numbered suggested answers with implications in a Rich table (`| Label | Answer | Implications |`), prompt with `Rich.Prompt.ask("Your choice", choices=[labels + "skip"])`, handle "skip" response by adding to skipped_ids, handle letter selection by creating ClarificationAnswer with is_custom=False, handle other text as custom answer with is_custom=True. Display final summary: "Clarification complete: {answered} answered, {skipped} skipped".

**Checkpoint**: Interactive flow with Rich formatting, option selection, custom answers, and skip is complete

---

## Phase 7: User Story 5 — Non-Interactive Report Mode (Priority: P3)

**Goal**: `specforge clarify <service> --report` generates clarifications-report.md without modifying spec.md

**Independent Test**: Run `specforge clarify ledger-service --report`, verify clarifications-report.md is created in service directory and spec.md is unchanged

### Tests for User Story 5

- [X] T027 [P] [US5] Integration tests for report mode in `tests/integration/test_clarify_cmd.py` (append to existing file): test `--report` flag creates clarifications-report.md in service output dir; test `--report` does NOT modify spec.md (compare content before/after); test report contains all detected questions with categories and suggested answers; test report renders via Jinja2 template (not string concatenation)

### Implementation for User Story 5

- [X] T028 [US5] Implement report mode branch in `src/specforge/cli/clarify_cmd.py`: when `--report` flag is True, skip interactive flow, build template context with questions grouped by category (dict of category→list of question dicts), render `clarifications-report.md.j2` via TemplateRenderer with context (service, date, questions, architecture), write rendered output to `{output_dir}/clarifications-report.md`, print path to report file, exit without modifying spec.md.

**Checkpoint**: Report mode generates shareable report — all 5 user stories are complete

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Snapshot tests, edge cases, and final validation

- [X] T029 [P] Snapshot tests for clarifications-report template in `tests/snapshots/test_clarification_templates.py`: render clarifications-report.md.j2 with known PersonalFinance ledger-service context (4 questions across domain/technical/service_boundary categories) and assert snapshot matches; render with zero questions and assert "No ambiguities" message
- [X] T030 [P] Add edge case handling across all modules: AmbiguityScanner returns empty tuple for empty spec_text; BoundaryAnalyzer handles manifest with zero services; ClarificationRecorder handles spec.md with malformed Clarifications section (falls back to creating new section); ResearchResolver handles empty spec_text; **clarify command acquires pipeline lock (via `acquire_lock()`) before modifying spec.md and releases in finally block — prevents both pipeline-vs-clarify and concurrent clarify-vs-clarify data loss**; research command checks pipeline lock before writing research.md
- [X] T031 Run full E2E validation per `specs/006-research-clarification-engine/quickstart.md`: create tmp PersonalFinance project with manifest.json (microservice, 5 services), generate spec.md for ledger-service via specify command, run `specforge clarify ledger-service` with simulated input, run `specforge research ledger-service`, verify all output files exist and contain expected content

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — core clarify flow
- **US2 (Phase 4)**: Depends on Phase 2 — independent of US1
- **US3 (Phase 5)**: Depends on Phase 3 (extends clarify command with BoundaryAnalyzer)
- **US4 (Phase 6)**: Depends on Phase 3 (enhances interactive presentation in clarify_cmd)
- **US5 (Phase 7)**: Depends on Phase 3 (adds --report branch to clarify_cmd)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — No dependencies on other stories
- **US2 (P1)**: Can start after Foundational — Independent of US1 (different command)
- **US3 (P2)**: Depends on US1 (extends clarify_cmd with BoundaryAnalyzer wiring)
- **US4 (P2)**: Depends on US1 (enhances interactive flow in clarify_cmd)
- **US5 (P3)**: Depends on US1 (adds --report branch to clarify_cmd)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/dataclasses before services
- Services before CLI commands
- Core implementation before integration wiring

### Parallel Opportunities

- T001 + T002 can run in parallel (config vs models — different files)
- T003 + T004 can run in parallel (patterns vs templates — different files)
- T005 + T006 + T007 + T008 can ALL run in parallel (different test files)
- T014 + T015 can run in parallel (different test files)
- T020 + T021 can run in parallel (different test files)
- US1 + US2 can run in parallel after Foundational (different CLI commands)
- US3 + US4 + US5 can run in parallel after US1 (different aspects of clarify_cmd)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel (TDD — write first, ensure FAIL):
Task T005: "Unit tests for AmbiguityScanner in tests/unit/test_clarification_analyzer.py"
Task T006: "Unit tests for QuestionGenerator in tests/unit/test_question_generator.py"
Task T007: "Unit tests for ClarificationRecorder in tests/unit/test_clarification_recorder.py"
Task T008: "Integration test for clarify command in tests/integration/test_clarify_cmd.py"

# Then implement sequentially:
Task T009: "AmbiguityScanner in src/specforge/core/clarification_analyzer.py"
Task T010: "QuestionGenerator in src/specforge/core/question_generator.py"
Task T011: "ClarificationRecorder in src/specforge/core/clarification_recorder.py"
Task T012: "clarify CLI command in src/specforge/cli/clarify_cmd.py"
Task T013: "Register clarify command in src/specforge/cli/main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T013)
4. **STOP and VALIDATE**: Run `specforge clarify ledger-service` against PersonalFinance test data
5. Delivers: pattern-based ambiguity detection + question generation + spec.md recording

### Incremental Delivery

1. Setup + Foundational → models and patterns ready
2. Add US1 → `specforge clarify` works with basic interactive flow (MVP)
3. Add US2 → `specforge research` works independently (parallel with US1)
4. Add US3 → BoundaryAnalyzer enhances clarify with cross-service + remap detection
5. Add US4 → Rich-formatted interactive presentation polish
6. Add US5 → Report mode for team-shareable output
7. Polish → Snapshots, edge cases, E2E validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD enforced: all test tasks (T005–T008, T014–T015, T020–T021, T025, T027) must FAIL before implementation
- PersonalFinance test data: ledger-service (features 002-accounts + 003-transactions), planning-service (features 004-budgets + 005-goals + 006-bills)
- BoundaryAnalyzer depends on manifest.json from Feature 004 — test fixtures must include valid PersonalFinance manifest structure
- All functions ≤30 lines per constitution
- All recoverable errors use Result[T, E] — no raise for control flow
- Constants in config.py — no magic strings
- Constructor injection for all dependencies
