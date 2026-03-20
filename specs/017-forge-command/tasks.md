# Tasks: Forge Command — Zero-Interaction Full Spec Generation

**Input**: Design documents from `/specs/017-forge-command/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD enforced — test files written BEFORE implementation for all new modules. Tests MUST fail before implementation code.

**Organization**: Tasks grouped by user story. Each story is independently implementable and testable.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths from `src/specforge/` and `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add forge-specific constants and API defaults to existing config module

- [ ] T001 Add forge constants to src/specforge/core/config.py — FORGE_STAGES tuple ("init", "decompose", "spec_generation", "validation", "report"), FORGE_STATE_FILE = "forge-state.json", FORGE_STATE_SCHEMA_VERSION = "1.0", FORGE_MAX_RETRIES = 3, FORGE_DEFAULT_WORKERS = 4, FORGE_LOCK_TIMEOUT_HOURS = 1, FORGE_REPORT_DIR = "reports", FORGE_REPORT_FILE = "forge-report.md", FORGE_DRAFT_SUFFIX = ".draft.md", FORGE_PROMPT_SUFFIX = ".prompt.md", FORGE_ARTIFACTS tuple of 7 filenames ("spec.md", "research.md", "data-model.md", "edge-cases.md", "plan.md", "checklist.md", "tasks.md"), FORGE_PHASE_TO_FILENAME dict mapping phase names to artifact filenames (e.g., "datamodel" → "data-model.md", "edgecase" → "edge-cases.md")

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All new building-block modules: ForgeState for persistence, ArtifactExtractor for structured context, EnrichedPromptBuilder for quality prompts

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### ForgeState (TDD pair)

- [ ] T002 Write unit tests for ForgeState and ServiceForgeStatus in tests/unit/test_forge_state.py — test create with default stage "init", test update_stage transitions through FORGE_STAGES, test mark_service_phase_complete increments phase (0→7), test mark_service_failed increments retry_count, test mark_service_permanently_failed after FORGE_MAX_RETRIES, test to_dict/from_dict round-trip JSON serialization, test load from valid JSON file returns Ok, test load from corrupt JSON returns Ok with fresh state + logs warning, test save uses atomic write (write to .tmp then os.replace), test is_locked with PID/timestamp, test clear_stale_lock after FORGE_LOCK_TIMEOUT_HOURS, test acquire_lock/release_lock cycle
- [ ] T003 Implement ForgeState + ServiceForgeStatus frozen dataclasses in src/specforge/core/forge_state.py — ForgeState fields: schema_version (str), stage (str), description (str), architecture (str), services (dict[str, ServiceForgeStatus]), started_at (str ISO), last_update (str ISO), status ("idle"/"running"), pid (int|None), lock_timestamp (str|None). ServiceForgeStatus fields: slug (str), last_completed_phase (int 0-7), status (str: pending/in_progress/complete/failed/permanently_failed), retry_count (int), error (str|None), last_update (str ISO). Methods: create() classmethod, update_stage(), mark_service_phase_complete(), mark_service_failed(), mark_service_permanently_failed(), incomplete_services() → list[str], to_dict(), from_dict(), save(path) with atomic os.replace, load(path) → Result[ForgeState, str], is_locked() → bool, acquire_lock(), release_lock(), clear_stale_lock()

### ArtifactExtractor (TDD pair — independent)

- [ ] T006 [P] Write unit tests for ArtifactExtractor in tests/unit/test_artifact_extractor.py — test extract_from_spec returns dict with "user_stories" (title+priority+scenario_count), "functional_requirements" (id+text), "success_criteria" (id+text), test extract_from_research returns "decisions" (topic+decision+rationale), test extract_from_data_model returns "entities" (name+field_count+relationships), test extract_from_edge_cases returns "edge_cases" (id+severity+description), test extract_from_plan returns "structure" and "phases", test format_for_prompt renders phase-appropriate markdown bullets, test missing artifact file returns Ok with empty dict (not error), test token count of format_for_prompt output is ≥30% less than raw text concatenation
- [ ] T007 [P] Implement ArtifactExtractor in src/specforge/core/artifact_extractor.py — stateless class. Methods: extract_from_spec(text) → dict, extract_from_research(text) → dict, extract_from_data_model(text) → dict, extract_from_edge_cases(text) → dict, extract_from_plan(text) → dict — all using regex-based markdown heading/bullet parsing. extract_all(service_dir, phase_name) → Result[dict, str] reads relevant prior artifacts from service_dir and calls appropriate extract methods. format_for_prompt(phase_name, extractions) → str renders extractions as labeled markdown sections with bullets. Missing files return Ok with empty dict.

### EnrichedPromptBuilder + Templates (TDD pair — parallel with above)

- [ ] T008 [P] Write unit tests for EnrichedPromptBuilder in tests/unit/test_enriched_prompts.py — test build_enrichment for each of 7 phases returns 50-100 rendered lines, test enrichment includes explicit output structure section, test enrichment includes architecture-specific guidance (different for microservice vs monolith), test enrichment includes governance rules when governance files exist, test enrichment gracefully omits governance when no prompt files present, test enrichment includes quality thresholds (30-line function limit, type hints, Result[T,E]), test enrichment includes anti-patterns section, test Jinja2 template rendering with service context variables, test enrichment includes example output section
- [ ] T009 [P] Implement EnrichedPromptBuilder in src/specforge/core/enriched_prompts.py — class with constructor injection: template_dir (Path), governance_loader (PromptLoader | None). Method: build_enrichment(phase_prompt: PhasePrompt, service_context: ServiceContext, arch_type: str) → Result[str, str] loads the phase's enrichment_template from template_dir, renders via Jinja2 with variables: service_name, service_description, arch_type, governance_rules (from loader or empty list), quality_thresholds (from config constants), output_structure (per-phase section list), anti_patterns (per-phase list), example_output. Returns rendered string of 50-100 lines.
- [ ] T010 [P] Create 8 enrichment Jinja2 templates in src/specforge/templates/base/enrichment/ — spec_enrichment.md.j2, research_enrichment.md.j2, datamodel_enrichment.md.j2, edgecase_enrichment.md.j2, plan_enrichment.md.j2, checklist_enrichment.md.j2, tasks_enrichment.md.j2, decompose_enrichment.md.j2. Each template includes: system role preamble, explicit output section headings with descriptions, architecture-specific conditional blocks ({% if arch_type == "microservice" %}), governance rules injection ({% if governance_rules %}), quality thresholds block, 5-10 line example of good output, anti-patterns list, cross-reference instructions for prior artifacts.

### Modifications to existing modules

- [ ] T011 Add enrichment_template field to PhasePrompt in src/specforge/core/phase_prompts.py — add optional enrichment_template: str | None = None field to PhasePrompt frozen dataclass. Update all 8 PhasePrompt constants (SPEC_PROMPT, RESEARCH_PROMPT, DATAMODEL_PROMPT, EDGECASE_PROMPT, PLAN_PROMPT, CHECKLIST_PROMPT, TASKS_PROMPT, DECOMPOSE_PROMPT) to set enrichment_template to the corresponding template filename (e.g., "spec_enrichment.md.j2", "decompose_enrichment.md.j2"). No changes to existing system_instructions or skeleton fields.
- [ ] T012 Modify PromptAssembler to use ArtifactExtractor in src/specforge/core/prompt_assembler.py — add optional artifact_extractor (ArtifactExtractor) and enriched_prompt_builder (EnrichedPromptBuilder) constructor parameters. In assemble(): if artifact_extractor is set, call extractor.format_for_prompt(phase, prior_artifacts) for structured context instead of raw text concatenation. If enriched_prompt_builder is set, call build_enrichment() and prepend to system prompt. If neither is set, preserve existing behavior for backward compatibility. Update existing tests to cover new code paths.
**Checkpoint**: Foundation ready — ForgeState, ArtifactExtractor, EnrichedPromptBuilder all tested and implemented. Existing modules updated. User story implementation can now begin.

---

## Phase 3: User Story 1 — Single Command Full Spec Generation (Priority: P1) 🎯 MVP

**Goal**: Run `specforge forge "description" --arch type` and get all spec artifacts for all services in a single unattended invocation with live progress display

**Independent Test**: Run `specforge forge "Create a PersonalFinance webapp" --arch microservice` on an initialized project and verify manifest.json is created, all service directories contain 7 artifacts, and forge-report.md is generated

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Write unit tests for ForgeProgress in tests/unit/test_forge_progress.py — test create dashboard with stage name, test update_service_phase updates table row, test update_stage changes header, test progress_bar advances correctly, test elapsed_time formats as MM:SS, test thread-safe queue consumption for progress callbacks from worker threads, test dashboard renders Rich Table with columns (Service, Phase, Status), test dashboard handles zero services gracefully
- [ ] T015 [P] [US1] Write unit tests for ForgeOrchestrator happy-path in tests/unit/test_forge_orchestrator.py — test run_forge executes stages in order (init→decompose→spec_gen→validate→report) with mock LLMProvider, test decompose_stage calls LLM and parses manifest JSON, test decompose_stage falls back to DomainAnalyzer on invalid JSON after 3 retries, test spec_generation_stage delegates to ParallelPipelineRunner with correct service list, test validation_stage checks FORGE_ARTIFACTS (all 7) per service, test report_stage generates forge-report.md via Jinja2, test --arch enforcement overrides LLM decompose response, test ForgeState updated after each stage, test Ok result on success and Err on total failure, test exit codes (0=success, 1=partial, 2=total failure)

### Implementation for User Story 1

- [ ] T016 [US1] Implement ForgeProgress in src/specforge/core/forge_progress.py — class with Rich Live context manager. Constructor: console (Console). Methods: start() enters Live context, stop() exits cleanly, update_stage(name) sets current stage Panel header, update_service(slug, phase, status) updates row in Rich Table (columns: Service, Phase 1/7, Status), advance_progress(amount) increments overall ProgressBar, render() builds layout: Panel(stage) + Table(services) + Progress + elapsed Text. Thread-safe: worker threads enqueue ProgressEvent tuples via queue.Queue, dashboard refresh loop dequeues and applies. Refresh ≤5 seconds per SC-004.
- [ ] T017 [US1] Implement ForgeOrchestrator in src/specforge/core/forge_orchestrator.py — class with constructor injection: project_dir (Path), llm_provider (LLMProvider), pipeline_runner (ParallelPipelineRunner), progress (ForgeProgress), enriched_builder (EnrichedPromptBuilder), artifact_extractor (ArtifactExtractor), assembler (PromptAssembler). Method: run_forge(description, arch_type, stack, max_parallel, dry_run, resume, force, skip_init) → Result[ForgeReport, str]. Stages: (1) _decompose_stage: LLM call with enriched prompt → parse manifest JSON → enforce arch_type → fallback to DomainAnalyzer; (2) _spec_generation_stage: build per-service pipeline configs → delegate to ParallelPipelineRunner with progress callbacks; (3) _validation_stage: verify FORGE_ARTIFACTS per service → collect missing; (4) _report_stage: render forge_report.md.j2 with timing data. Update ForgeState.save() after each stage. Return ForgeReport with per-service results + timing.
- [ ] T018 [US1] Create forge_report.md.j2 template in src/specforge/templates/base/forge_report.md.j2 — template receives: project_description, arch_type, services (list: slug+status+artifacts+timing), failed_services (list: slug+error+retry_count), total_elapsed, stage_timings (dict stage→duration). Renders: header (description + arch), per-service table (artifact inventory), failed services section (diagnostic detail), timing breakdown table, overall status line.
- [ ] T019 [US1] Implement forge Click command in src/specforge/cli/forge_cmd.py — @click.command("forge"), @click.argument("description", default=""), @click.option("--arch", type=click.Choice(VALID_ARCHITECTURES), default="monolithic"), @click.option("--stack", type=click.Choice(SUPPORTED_STACKS + ["auto"]), default="auto"), @click.option("--max-parallel", type=click.IntRange(min=1), default=FORGE_DEFAULT_WORKERS), @click.option("--dry-run", is_flag=True), @click.option("--resume", is_flag=True), @click.option("--skip-init", is_flag=True), @click.option("--force", is_flag=True). Validate: empty description → Rich error + exit 2; --resume + --force → Click error "mutually exclusive". Construct ForgeOrchestrator, call run_forge, map Result → sys.exit(0/1/2).
- [ ] T020 [US1] Register forge command in src/specforge/cli/main.py — import forge from specforge.cli.forge_cmd, add cli.add_command(forge) in the registration block alongside existing init, decompose, specify, implement, status commands.

**Checkpoint**: `specforge forge "My App" --arch monolithic` runs full 5-stage pipeline with live dashboard and generates forge-report.md — MVP complete

---

## Phase 4: User Story 2 — Auto-Initialization for New Projects (Priority: P2)

**Goal**: If `.specforge/` does not exist, forge auto-creates it with detected agent and stack before proceeding

**Independent Test**: Run `specforge forge "Build a TODO app"` in an empty directory → `.specforge/` created with auto-detected agent and stack, then full pipeline proceeds

- [ ] T021 [US2] Write auto-init scenario tests in tests/unit/test_forge_orchestrator.py — test no .specforge/ triggers non-interactive init with auto-detected agent (mock agent_detector) and stack (mock stack_detector), test existing .specforge/ with config.json skips init entirely, test --skip-init + missing .specforge/ returns Err with message "Project not initialized", test --stack flag value is passed to init when provided
- [ ] T022 [US2] Implement _init_stage() in src/specforge/core/forge_orchestrator.py — at start of run_forge: if .specforge/ exists → skip + update ForgeState. If not exists and not skip_init → call existing ScaffoldBuilder + ScaffoldWriter in non-interactive mode with auto-detected agent, pass --stack value if provided. If not exists and skip_init → return Err. Update ForgeState stage to init_complete on success.

**Checkpoint**: Forge works on completely fresh directories with zero prior setup

---

## Phase 5: User Story 3 — Resume After Interruption (Priority: P3)

**Goal**: `--resume` skips completed stages, retries only incomplete/failed services (3 retries per invocation). Ctrl+C saves .draft.md and forge-state.json.

**Independent Test**: Interrupt forge after 3/8 services complete, run `specforge forge --resume` → only 5 incomplete services re-processed

- [ ] T023 [US3] Write resume scenario tests in tests/unit/test_forge_orchestrator.py — test partial completion (3/8 done) resumes only 5 services, test 3 consecutive failures marks permanently_failed, test corrupt forge-state.json logs warning + starts fresh, test .draft.md files trigger retry from that phase, test retry_count resets to 0 on new --resume invocation, test completed stages (init/decompose) are skipped
- [ ] T024 [US3] Implement _load_or_create_state() and resume logic in src/specforge/core/forge_orchestrator.py — at start of run_forge: if resume → load ForgeState → skip completed stages → filter to incomplete_services() → reset retry_counts to 0. If force → create fresh state. If neither and state exists → return StateExists signal. In _spec_generation_stage: retry failed services up to FORGE_MAX_RETRIES → mark permanently_failed after limit. Detect .draft.md → resume from phase that produced draft. Save state after each service phase completion.
- [ ] T025 [US3] Implement Ctrl+C handler in src/specforge/core/forge_orchestrator.py — register signal handler or try/except KeyboardInterrupt around run_forge. On interrupt: save in-progress LLM output as {artifact_name}.draft.md via atomic write, update ForgeState with current stage + per-service progress, save forge-state.json, print via console: "Forge interrupted. Resume with: specforge forge --resume", sys.exit(130).
- [ ] T026 [US3] Add state detection prompt in src/specforge/cli/forge_cmd.py — if ForgeOrchestrator signals StateExists (no --resume, no --force): Rich Prompt.ask("Previous forge run detected. [O]verwrite / [R]esume / [A]bort?", choices=["o","r","a"]) → map to force=True / resume=True / sys.exit(0). Enforce --resume/--force mutual exclusion via Click callback.

**Checkpoint**: Forge survives interruptions and resumes cleanly

---

## Phase 6: User Story 4 — Enriched, Detailed Spec Artifacts (Priority: P4)

**Goal**: Phase prompts produce substantive, domain-specific artifacts (≥1500 words for spec.md/plan.md) via structured artifact context and 50-100 line enriched system instructions

**Independent Test**: Run forge, inspect generated spec.md → contains detailed user stories, specific FRs, measurable SCs, not placeholder text

- [ ] T027 [P] [US4] Add enrichment quality validation tests in tests/unit/test_enriched_prompts.py — verify rendered enrichment for each of 7 phases contains architecture-specific guidance (monolithic vs microservice variants), governance rules when files exist, output structure specification, quality thresholds, good/bad example sections. Verify rendered output is 50-100 lines per phase.
- [ ] T028 [P] [US4] Add token reduction comparison test in tests/unit/test_artifact_extractor.py — assemble prompt context via format_for_prompt() vs raw text concatenation using 3 sample artifacts → structured version is ≥30% smaller measured as len(text)/4
- [ ] T029 [US4] Wire enriched prompts into pipeline in src/specforge/core/forge_orchestrator.py — in _spec_generation_stage, construct PromptAssembler with artifact_extractor and enriched_prompt_builder injected. Ensure each service's 7-phase pipeline receives the assembler configured for structured extraction + enriched system instructions. Verify enrichment_template from PhasePrompt is resolved and rendered for each phase.

**Checkpoint**: Generated artifacts are substantive and domain-specific. Token usage reduced ≥30% vs raw concatenation.

---

## Phase 7: User Story 5 — Dry Run for Prompt Preview (Priority: P5)

**Goal**: `--dry-run` generates `.prompt.md` files for all phases/services with zero LLM calls and reports estimated token usage

**Independent Test**: Run `specforge forge "My App" --dry-run` → .prompt.md files exist per service, zero LLM calls, summary shows estimated tokens

- [ ] T030 [US5] Write dry-run scenario tests in tests/unit/test_forge_orchestrator.py — test .prompt.md files created for each service×phase, test zero LLM calls via mock call_count == 0, test token estimation matches sum of len(prompt)//4, test --dry-run + --force overwrites existing .prompt.md, test --dry-run + --resume generates prompts only for incomplete services, test dry-run exits code 0
- [ ] T031 [US5] Implement --dry-run path in src/specforge/core/forge_orchestrator.py — when dry_run=True: run init stage + decompose stage normally (discover services), in _spec_generation_stage: for each service × phase, assemble full prompt via PromptAssembler → write to {service_dir}/{phase_name}.prompt.md → skip LLM call. Collect prompt paths + estimated tokens (len(prompt)//4). Skip validation stage. In report stage: generate dry-run summary.
- [ ] T032 [US5] Add --dry-run summary output in src/specforge/cli/forge_cmd.py — if dry_run result: print Rich Panel with services discovered count, total prompts generated (services × 7), estimated total token usage, Rich Table of prompt file paths grouped by service. Exit code 0.

**Checkpoint**: Developers can preview all prompts and estimated cost before committing to a real forge run

---

## Phase 8: US6 + Polish & Cross-Cutting Concerns

**Purpose**: Provider-agnostic validation, concurrent lock protection, end-to-end integration, final quality gates

- [ ] T033 [P] [US6] Add provider-agnostic tests in tests/unit/test_forge_orchestrator.py — test ForgeOrchestrator works with mock LLMProvider implementing call() protocol for all 3 agent types (claude/copilot/gemini), test no provider-specific logic in orchestrator, test provider is constructor-injected and never instantiated internally
- [ ] T034 [P] Write end-to-end integration test in tests/integration/test_forge_end_to_end.py — test via CliRunner with mock SubprocessProvider: (1) fresh dir auto-inits + produces all artifacts, (2) --resume skips completed services, (3) --dry-run produces .prompt.md with zero LLM calls, (4) --force overwrites existing state, (5) --skip-init on uninitialized dir → exit code 2, (6) all services fail → error report + exit code 2, (7) partial failure → exit code 1
- [ ] T035 [P] Snapshot tests for forge-report template in tests/snapshots/ — render forge_report.md.j2 with fixture data (mix of successful + failed services), snapshot via syrupy, verify valid markdown with all required sections
- [ ] T036 Run `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`, run `uv run pytest --cov=specforge --cov-report=term-missing`, verify all new modules ≥90% line coverage
- [ ] T037 [P] Write concurrent lock integration test in tests/integration/test_forge_lock.py — test two concurrent ForgeOrchestrator instances detect lock conflict via forge-state.json status="running" + PID, test stale lock (>FORGE_LOCK_TIMEOUT_HOURS) is automatically cleared, test acquire_lock/release_lock lifecycle end-to-end with tmp_path
- [ ] T038 [P] Add token-budget compression fallback test in tests/unit/test_artifact_extractor.py — test ArtifactExtractor switches from full structured extraction to compressed summaries (key-value pairs, bullet lists) when format_for_prompt output exceeds a configurable token budget, verify compressed output preserves critical information (FR IDs, entity names, edge case severities)
- [ ] T039 [P] Add word-count validation test in tests/unit/test_forge_orchestrator.py — test _validation_stage checks generated spec.md and plan.md contain ≥1500 words, test missing word-count threshold logs warning in forge-report but does not fail the service (advisory gate per SC-002)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (config constants) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (ForgeState, ArtifactExtractor, EnrichedPromptBuilder)
- **US2 (Phase 4)**: Depends on Phase 3 (needs ForgeOrchestrator base)
- **US3 (Phase 5)**: Depends on Phase 3 (needs ForgeOrchestrator + ForgeState integration)
- **US4 (Phase 6)**: Depends on Phase 3 (wires enrichment into orchestrator pipeline)
- **US5 (Phase 7)**: Depends on Phase 3 (adds dry-run branch to orchestrator)
- **US6 + Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Requires all foundational building blocks — no dependencies on other stories
- **US2 (P2)**: Extends ForgeOrchestrator init stage — independent of US3-US6
- **US3 (P3)**: Extends ForgeOrchestrator state management — independent of US2, US4-US6
- **US4 (P4)**: Validates enrichment quality from Phase 2 — independent of US2, US3, US5-US6
- **US5 (P5)**: Adds dry-run code path — independent of US2-US4, US6
- **US6 (P6)**: Validates provider-agnostic behavior — independent of US2-US5

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Dataclasses and models before logic modules
- Core modules before orchestrator
- Orchestrator before CLI command
- CLI command before main.py registration
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Phase 2 — maximum parallelism (three independent TDD pairs + templates):**
```
T002→T003: ForgeState (sequential TDD pair)
T006→T007: [P] ArtifactExtractor (different file, parallel with ForgeState)
T008→T009: [P] EnrichedPromptBuilder (parallel with above)
T010:      [P] Enrichment templates (different directory, parallel)
Then sequential: T011 (phase_prompts) → T012 (prompt_assembler)
```

**Phase 3 — test files in parallel, then sequential chain:**
```
T014 ─┐ (parallel test files, different files)
T015 ─┘
Then: T016 → T017 → T018 → T019 → T020 (sequential implementation chain)
```

**Phase 6 — parallel test tasks:**
```
T027 ─┐ (all parallel, different test files)
T028 ─┘
```

**Phase 8 — parallel tests:**
```
T033 ─┐
T034 ─┤ (all parallel, different test files)
T035 ─┤
T037 ─┤
T038 ─┤
T039 ─┘
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T012)
3. Complete Phase 3: US1 core flow (T014-T020)
4. **STOP and VALIDATE**: `specforge forge "Test App" --arch monolithic` produces all artifacts
5. This is a functional MVP — single command produces all specs

### Incremental Delivery

1. Setup + Foundational → All 4 building blocks verified with unit tests
2. Add US1 → Test end-to-end → **MVP** (single command works)
3. Add US2 → Test on fresh directory → Auto-init works
4. Add US3 → Test interrupt + resume → Recovery works
5. Add US4 → Test artifact quality → Enriched prompts wired
6. Add US5 → Test dry-run → Prompt preview works
7. Add US6 + Polish → Integration tests pass → Feature complete

### Suggested MVP Scope

**US1 alone** (Phases 1-3, tasks T001-T020) delivers the core value: a single `specforge forge` command that produces all spec artifacts for all services with live progress. This is independently testable and deployable.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] labels map tasks to user stories from spec.md for traceability
- All LLM calls use the existing SubprocessProvider — no new external dependencies in core
- Tests follow TDD: write test → verify it fails → implement → verify it passes
- Commit after each task using conventional commits (e.g., `feat(forge): add ForgeState dataclass`)
- Constitution: ≤30 line functions, ≤200 line classes, Result[T,E] for error paths, type hints everywhere, constructor injection
- pathlib.Path exclusively — no os.path
- All constants in config.py — no magic strings
- All 8 enrichment templates use Jinja2 with conditional blocks for arch_type, governance, and quality thresholds
- FORGE_PHASE_TO_FILENAME maps phase names ("datamodel", "edgecase") to artifact filenames ("data-model.md", "edge-cases.md") for validation
