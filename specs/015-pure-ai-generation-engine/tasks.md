# Tasks: Pure AI Content Generation Engine

**Input**: Design documents from `/specs/015-pure-ai-generation-engine/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, checklists/implementation.md

**Tests**: TDD enforced — test files BEFORE implementation files in every phase.

**Organization**: Tasks grouped by implementation phase (matching plan.md phases 1–7), with user story labels mapping to spec.md user stories. PureAIGenerator (LLMProvider + PromptAssembler + OutputValidator) built first, then each phase runner updated with `[P]` for independent phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US7)
- TDD: Test tasks appear BEFORE implementation tasks in each phase
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/specforge/` at repository root
- **Tests**: `tests/` at repository root (unit/, integration/, snapshots/)
- **Config**: `src/specforge/core/config.py` for all constants

---

## Phase 1: Setup — Config Constants

**Purpose**: Add all new constants to `config.py` that downstream modules depend on

- [x] T001 Add LLM constants to `src/specforge/core/config.py`: `LLM_DEFAULT_TIMEOUT`, `LLM_DEFAULT_MAX_RETRIES`, `LLM_DEFAULT_BACKOFF_BASE`, `LLM_DEFAULT_MAX_BACKOFF`, `MAX_OUTPUT_CHARS`, `MAX_CONTINUATIONS`, `CLEAN_MARKDOWN_INSTRUCTION`
- [x] T002 Add `GOVERNANCE_PHASE_MAP` constant to `src/specforge/core/config.py` mapping each pipeline phase to governance domain list per R6
- [x] T003 Add `PHASE_REQUIRED_SECTIONS` constant to `src/specforge/core/config.py` mapping each phase to required heading strings per R3
- [x] T004 Add `PREAMBLE_PATTERNS` constant to `src/specforge/core/config.py` with known LLM preamble prefixes per R9

---

## Phase 2: Foundation — LLM Provider Protocol + SubprocessProvider + ProviderFactory (US7)

**Goal**: Establish the LLM provider abstraction so any configured agent can be invoked via a uniform protocol

**Independent Test**: Mock `SubprocessProvider` with canned subprocess responses; verify `ProviderFactory` resolves agent names to providers and detects missing CLI tools

### Tests for Phase 2

- [x] T005 [US7] Write unit tests for `LLMProvider` protocol, `SubprocessProvider`, and `ProviderFactory` in `tests/unit/test_llm_provider.py` — cover: protocol conformance, `call()` with mocked subprocess, timeout handling, retry on transient errors, no retry on permanent errors, exponential backoff, `is_available()` with `shutil.which()` mock, `ProviderFactory.create()` with valid/invalid/generic agents, config override parsing

### Implementation for Phase 2

- [x] T006 [US7] Implement `LLMProvider` protocol with `call(system_prompt, user_prompt) -> Result[str, str]` in `src/specforge/core/llm_provider.py`
- [x] T007 [US7] Implement `SubprocessProvider` in `src/specforge/core/llm_provider.py` — `_call_once()` via `subprocess.run()`, `_classify_error()` per R5, `is_available()` via `shutil.which()`, retry loop with exponential backoff
- [x] T008 [US7] Implement `ProviderFactory.create(config_path) -> Result[LLMProvider, str]` in `src/specforge/core/llm_provider.py` — read config.json, map agent to command template per R8, apply `"llm"` overrides, resolve provider-specific config from environment variables (FR-037: API keys via `SPECFORGE_LLM_API_KEY`, custom endpoints via `SPECFORGE_LLM_ENDPOINT`, CLI paths via `SPECFORGE_LLM_CLI_PATH`), validate availability
- [x] T009 [US7] Add `_AGENT_COMMAND_TEMPLATES` mapping in `src/specforge/core/llm_provider.py` for `claude`, `copilot`, `gemini`, `codex` per R8

**Checkpoint**: `LLMProvider` protocol works end-to-end with mocked subprocess — all T005 tests pass

---

## Phase 3: Prompt Construction — PhasePrompts + PromptAssembler + Adapter Serialization (US3, US5)

**Goal**: Build the prompt assembly pipeline that combines constitution, governance, architecture context, prior artifacts, and Spec-Kit skeletons into LLM-ready prompts with token budgeting

**Independent Test**: Assemble prompts for each phase with mock data; verify token budget enforcement truncates lowest-priority sections; snapshot-test assembled prompts

### Tests for Phase 3

- [x] T010 [P] [US3] Write unit tests for `PhasePrompt` dataclass and all 8 instances in `tests/unit/test_phase_prompts.py` — cover: frozen dataclass fields, skeleton content includes Spec-Kit section headers, required_sections match PHASE_REQUIRED_SECTIONS, all 8 definitions (7 pipeline + decompose)
- [x] T011 [P] [US5] Write unit tests for `PromptAssembler` in `tests/unit/test_prompt_assembler.py` — cover: `assemble()` returns `(system_prompt, user_prompt)`, constitution inclusion, governance filtering by GOVERNANCE_PHASE_MAP, prior artifact inclusion in pipeline order, token budget enforcement with priority trimming, `[TRUNCATED]` marker, architecture context serialization, budget override from config
- [x] T012 [P] [US3] Write unit tests for `serialize_for_prompt()` on all 3 architecture adapters in existing adapter test file — cover: Microservice includes Docker/health-check/gRPC terms, Monolith excludes container terms, ModularMonolith includes module boundaries + interface contracts
- [x] T013 [P] [US3] Create snapshot test directory `tests/snapshots/test_prompt_assembly/` and write snapshot tests for assembled prompts per phase × architecture type (spec+microservice, plan+monolith, tasks+microservice, decompose+microservice)

### Implementation for Phase 3

- [x] T014 [US3] Implement `PhasePrompt` frozen dataclass in `src/specforge/core/phase_prompts.py` with fields: `phase_name`, `system_instructions`, `skeleton`, `required_sections`, `clean_markdown_instruction`
- [x] T015 [US3] Define all 8 `PhasePrompt` instances in `src/specforge/core/phase_prompts.py` — spec, research, datamodel, edgecase, plan, checklist, tasks, decompose — each with exact Spec-Kit skeleton and required sections per FR-024/FR-045
- [x] T016 [US3] Add `serialize_for_prompt() -> str` to `ArchitectureAdapter` protocol in `src/specforge/core/architecture_adapter.py`
- [x] T017 [P] [US3] Implement `serialize_for_prompt()` in `MicroserviceAdapter` in `src/specforge/core/architecture_adapter.py` — Docker, health checks, gRPC/REST, service discovery per R7
- [x] T018 [P] [US3] Implement `serialize_for_prompt()` in `MonolithAdapter` in `src/specforge/core/architecture_adapter.py` — shared DB, module boundaries, no containers per R7
- [x] T019 [P] [US3] Implement `serialize_for_prompt()` in `ModularMonolithAdapter` in `src/specforge/core/architecture_adapter.py` — module boundaries + interface contracts per R7
- [x] T020 [US5] Implement `PromptAssembler` in `src/specforge/core/prompt_assembler.py` — `assemble()`, `_load_constitution()`, `_load_governance()`, `_serialize_artifacts()`, `_apply_budget()` with priority-based trimming per R2

**Checkpoint**: Prompt assembly produces correct system+user prompt pairs for all phases; token budget enforced; snapshots match — all T010–T013 tests pass

---

## Phase 4: Output Validation + Post-Processing (US6)

**Goal**: Build the output validation and post-processing pipeline that ensures LLM output meets structural requirements and handles preamble/truncation

**Independent Test**: Feed mock LLM output (valid, incomplete, with preamble, truncated) through validator and postprocessor; verify section detection, preamble stripping, truncation detection, continuation prompt construction

### Tests for Phase 4

- [x] T021 [P] [US6] Write unit tests for `OutputValidator` in `tests/unit/test_output_validator.py` — cover: `validate()` passes with all required sections, fails with missing sections returns list, `build_correction_prompt()` includes missing section names, per-phase validation rules match PHASE_REQUIRED_SECTIONS, case-insensitive heading matching
- [x] T022 [P] [US6] Write unit tests for `OutputPostprocessor` in `tests/unit/test_output_postprocessor.py` — cover: `strip_preamble()` removes text before first `#` heading, preserves content from heading onward, no-op when no preamble; `normalize_headings()` converts `###` to `##` when expected top level is 2, preserves relative hierarchy, no-op when headings correct; `detect_truncation()` detects missing sections + incomplete trailing content; `build_continuation_prompt()` constructs correct system+user pair; `cap_output()` enforces MAX_OUTPUT_CHARS

### Implementation for Phase 4

- [x] T023 [US6] Implement `OutputValidator` in `src/specforge/core/output_validator.py` — `validate(phase, content) -> Result[str, list[str]]` checking required sections via regex, `build_correction_prompt(phase, missing, original_output) -> str`
- [x] T024 [US6] Implement `OutputPostprocessor` in `src/specforge/core/output_postprocessor.py` — `strip_preamble()` per R9, `normalize_headings()` to fix LLM heading-level drift (edge case #1), `detect_truncation()` per R4 heuristics, `build_continuation_prompt()`, `cap_output()`

**Checkpoint**: Validator catches missing sections, postprocessor strips preamble and detects truncation — all T021–T022 tests pass

---

## Phase 5: Pipeline Integration — Dual-Mode BasePhase + Phase Runners (US2)

**Goal**: Extend `BasePhase.run()` with LLM execution path and implement `_build_prompt()` in all 7 phase subclasses; update `PipelineOrchestrator` to pass LLM dependencies

**Independent Test**: Run full pipeline with mock `LLMProvider` returning canned phase outputs; verify all 7 artifacts written, prior artifacts passed to each phase, parallel datamodel+edgecase preserved

### Tests for Phase 5

- [x] T025 [US2] Write unit tests for dual-mode `BasePhase.run()` in `tests/unit/test_base_phase_dual.py` — cover: LLM mode calls `_build_prompt()` → `assembler.assemble()` → `provider.call()` → `postprocessor.strip_preamble()` → `validator.validate()` → writes artifact; template mode uses existing path; dry-run mode writes `.prompt.md` and returns; retry loop on validation failure; `.draft.md` saved on max retries; continuation loop on truncation
- [x] T026 [US2] Write integration tests for full LLM pipeline in `tests/integration/test_specify_llm_mode.py` — cover: all 7 phases execute with mock provider, each phase receives prior artifacts, parallel datamodel+edgecase, PersonalFinance manifest in microservice mode, PersonalFinance manifest in monolith mode
- [x] T026b [US2] Write output quality snapshot tests in `tests/snapshots/test_llm_output_quality/` — compare generated artifacts (from mock LLM returning rich canned content) against old Jinja2 template output for the same input; verify LLM output contains substantive prose (not placeholder text like `[TODO]` or `{{ variable }}`), architecture-specific terms (Docker/health-check for microservice, shared-DB for monolith), and cross-artifact references (plan.md referencing entities from data-model.md)

### Implementation for Phase 5

- [x] T027 [US2] Extend `BasePhase.run()` with LLM execution path in `src/specforge/core/phases/base_phase.py` — add optional `provider`, `assembler`, `validator`, `postprocessor`, `dry_run_prompt` params; implement mode selection logic, retry loop, continuation loop, `.draft.md` fallback
- [x] T028 [US2] Add abstract `_build_prompt()` method to `BasePhase` in `src/specforge/core/phases/base_phase.py` returning `dict[str, str]` with service-specific context for user prompt
- [x] T029 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/specify_phase.py` — return feature description, service name, acceptance criteria context
- [x] T030 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/research_phase.py` — return tech stack questions, integration concerns context
- [x] T031 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/datamodel_phase.py` — return entity extraction context from spec
- [x] T032 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/edgecase_phase.py` — return error scenarios, security concerns context
- [x] T033 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/plan_phase.py` — return implementation strategy, file structure context
- [x] T034 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/checklist_phase.py` — return quality gate criteria context
- [x] T035 [P] [US2] Implement `_build_prompt()` in `src/specforge/core/phases/tasks_phase.py` — return task generation context with user story mapping
- [x] T036 [US2] Modify `PipelineOrchestrator.__init__()` in `src/specforge/core/spec_pipeline.py` to accept optional `LLMProvider`, `PromptAssembler`, `OutputValidator`, `OutputPostprocessor`
- [x] T037 [US2] Modify `PipelineOrchestrator._run_phases()` in `src/specforge/core/spec_pipeline.py` to pass mode + LLM dependencies to `phase.run()`, preserving parallel datamodel+edgecase execution

**Checkpoint**: Full 7-phase pipeline runs end-to-end with mock LLM provider; PersonalFinance in both microservice and monolith modes — all T025–T026 tests pass

---

## Phase 6: Decompose Integration (US1)

**Goal**: Add LLM decompose path with fallback to `DomainAnalyzer` and CLI flags

**Independent Test**: Run `specforge decompose "Personal Finance App"` with mock LLM; verify `manifest.json` has 3+ features with service mappings; verify fallback on LLM failure; test both `--arch microservice` and `--arch monolithic`

### Tests for Phase 6

- [x] T038 [US1] Write integration tests for LLM decompose in `tests/integration/test_decompose_llm_mode.py` — cover: LLM decompose produces valid manifest.json with 3+ features, architecture-specific prompt content for microservice and monolith, fallback to DomainAnalyzer on LLM failure with warning, JSON parsing with minor deviations, retry on parse failure then fallback, PersonalFinance manifest in microservice mode, PersonalFinance manifest in monolith mode

### Implementation for Phase 6

- [x] T039 [US1] Add `--template-mode` and `--dry-run-prompt` flags to `decompose` command in `src/specforge/cli/decompose_cmd.py`
- [x] T040 [US1] Implement LLM decompose path in `src/specforge/cli/decompose_cmd.py` — construct prompt via `PromptAssembler` with decompose `PhasePrompt`, call provider, parse JSON response, feed to `ManifestWriter`
- [x] T041 [US1] Implement fallback logic in `src/specforge/cli/decompose_cmd.py` — on LLM failure or parse failure after retry, fall back to `DomainAnalyzer` with Rich warning

**Checkpoint**: `specforge decompose "Personal Finance App"` produces intelligent feature decomposition with mock LLM; fallback works — all T038 tests pass

---

## Phase 7: CLI Integration — Specify Command (US4)

**Goal**: Wire `--template-mode` and `--dry-run-prompt` flags into `specforge specify`; resolve LLM provider from config; auto-fallback to template mode when no provider available

**Independent Test**: Run `specforge specify --template-mode` and verify identical output to pre-Feature-015; run `--dry-run-prompt` and verify `.prompt.md` files written without LLM calls; verify mutual exclusion error

### Tests for Phase 7

- [x] T042 [P] [US4] Write integration tests for `--template-mode` flag in `tests/integration/test_template_mode_flag.py` — cover: template mode uses TemplateRenderer with no LLM calls, auto-fallback when no provider configured (agent="generic"), auto-fallback when agent CLI not on PATH, warning emitted on fallback
- [x] T043 [P] [US4] Write integration tests for `--dry-run-prompt` flag in `tests/integration/test_dry_run_prompt.py` — cover: writes `.prompt.md` files for all phases without LLM calls, mutual exclusion with `--template-mode` rejected, prompt files contain Spec-Kit skeleton + governance + prior artifacts

### Implementation for Phase 7

- [x] T044 [US4] Add `--template-mode` and `--dry-run-prompt` flags to `specify` command in `src/specforge/cli/specify_cmd.py`
- [x] T045 [US4] Implement provider resolution in `src/specforge/cli/specify_cmd.py` — call `ProviderFactory.create()`, auto-fallback to template mode if `Err`, validate mutual exclusion of `--dry-run-prompt` + `--template-mode`
- [x] T046 [US4] Wire `PromptAssembler`, `OutputValidator`, `OutputPostprocessor` into `PipelineOrchestrator` construction in `src/specforge/cli/specify_cmd.py`

**Checkpoint**: CLI flags work correctly; auto-fallback triggers on missing provider; mutual exclusion enforced — all T042–T043 tests pass

---

## Phase 8: Polish — Continuation Loop, Config Overrides, Template Updates

**Purpose**: Finalize continuation loop in BasePhase, add config.json override parsing, update Jinja2 templates for Spec-Kit alignment

- [x] T047 [US6] Implement continuation loop in `BasePhase.run()` LLM path in `src/specforge/core/phases/base_phase.py` — call `postprocessor.detect_truncation()`, issue up to `MAX_CONTINUATIONS` continuation calls, cap combined output per FR-040/FR-041/FR-042
- [x] T048 [US5] Implement `config.json` `"governance_phase_map"` override loading in `src/specforge/core/prompt_assembler.py` — merge user overrides with default `GOVERNANCE_PHASE_MAP` per FR-044
- [x] T049 [US7] Implement `config.json` `"llm"` object parsing in `src/specforge/core/llm_provider.py` ProviderFactory — extract `token_budget`, `timeout_seconds`, `max_retries`, `model`, `max_output_chars` per FR-036
- [x] T050 Update `constitution.md` Jinja2 template in `src/specforge/templates/base/constitution.md.j2` to match Spec-Kit constitution-template format per FR-047
- [x] T051 Update agent-file Jinja2 template (CLAUDE.md) in `src/specforge/templates/base/` to match Spec-Kit agent-file-template format per FR-048
- [x] T052 Run `uv run pytest --snapshot-update` to update all snapshot files in `tests/snapshots/test_prompt_assembly/`
- [x] T053 Run full test suite `uv run pytest --cov=specforge --cov-report=term-missing` and verify all tests pass with ≥80% coverage on new modules. Note: SC-010 (10-minute timing) cannot be verified via mocks — manual validation with a real LLM provider is required post-implementation
- [x] T054 Run `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/` — fix any lint/format issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundation)**: Depends on Phase 1 (constants in config.py)
- **Phase 3 (Prompt Construction)**: Depends on Phase 2 (LLMProvider protocol for type refs)
- **Phase 4 (Output Validation)**: Depends on Phase 1 (PHASE_REQUIRED_SECTIONS constant); can run in parallel with Phase 3
- **Phase 5 (Pipeline Integration)**: Depends on Phases 2, 3, 4 (all core modules)
- **Phase 6 (Decompose)**: Depends on Phases 2, 3, 4 (provider + assembler + validator)
- **Phase 7 (CLI Specify)**: Depends on Phase 5 (pipeline integration)
- **Phase 8 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US7** (LLM Provider Abstraction): Phase 2 — no dependencies on other stories
- **US3** (Architecture-Aware Prompts): Phase 3 — depends on US7 for provider types
- **US5** (Token Budgeting): Phase 3 — depends on US7 for provider types
- **US6** (Output Validation): Phase 4 — can start after Phase 1 (parallel with Phase 3)
- **US2** (LLM-Powered Specify): Phase 5 — depends on US7, US3, US5, US6
- **US1** (LLM-Powered Decompose): Phase 6 — depends on US7, US3, US5, US6
- **US4** (Template Mode Fallback): Phase 7 — depends on US2

### Within Each Phase

- Tests MUST be written and FAIL before implementation (TDD)
- Protocol/dataclass definitions before implementations
- Abstract methods before concrete implementations
- Core modules before CLI integration

### Parallel Opportunities

- **Phase 3**: T010, T011, T012, T013 (tests) can all run in parallel; T017, T018, T019 (adapter `serialize_for_prompt()` impls) can run in parallel
- **Phase 3 + Phase 4**: Phase 4 tests (T021, T022) can start in parallel with Phase 3 implementation once Phase 1 is done
- **Phase 5**: T029–T035 (all 7 `_build_prompt()` implementations) can run in parallel — each is an independent phase file
- **Phase 6 + Phase 7**: Phase 6 (decompose) and Phase 7 (specify CLI) can run in parallel after Phase 5
- **Phase 7**: T042, T043 (integration tests) can run in parallel

---

## Parallel Example: Phase 5 — _build_prompt() Implementations

```bash
# After T027–T028 (BasePhase dual-mode + abstract method) are complete:

# Launch all 7 _build_prompt() implementations in parallel:
T029: "Implement _build_prompt() in specify_phase.py"
T030: "Implement _build_prompt() in research_phase.py"
T031: "Implement _build_prompt() in datamodel_phase.py"
T032: "Implement _build_prompt() in edgecase_phase.py"
T033: "Implement _build_prompt() in plan_phase.py"
T034: "Implement _build_prompt() in checklist_phase.py"
T035: "Implement _build_prompt() in tasks_phase.py"
```

## Parallel Example: Phase 3 — Adapter Serialization

```bash
# After T016 (protocol method added) is complete:

# Launch all 3 serialize_for_prompt() implementations in parallel:
T017: "MicroserviceAdapter.serialize_for_prompt()"
T018: "MonolithAdapter.serialize_for_prompt()"
T019: "ModularMonolithAdapter.serialize_for_prompt()"
```

---

## Implementation Strategy

### MVP First (Phase 1–5 = Core LLM Pipeline)

1. Complete Phase 1: Setup constants
2. Complete Phase 2: LLM provider abstraction (US7)
3. Complete Phases 3 + 4: Prompt assembly + output validation (US3, US5, US6) — partially parallel
4. Complete Phase 5: Pipeline integration (US2)
5. **STOP and VALIDATE**: Run `specforge specify ledger-service` with mock LLM provider against PersonalFinance manifest — verify all 7 artifacts generated correctly for both microservice and monolith architectures

### Incremental Delivery

1. Phases 1–2 → LLM provider callable standalone
2. Phase 3 → Prompts assemblable, snapshots validate format
3. Phase 4 → Output validation works in isolation
4. Phase 5 → Full specify pipeline operational with LLM (**MVP**)
5. Phase 6 → Decompose also uses LLM
6. Phase 7 → CLI flags for backward compatibility
7. Phase 8 → Continuation, config overrides, template alignment

### Test Data

- **PersonalFinance manifest**: Use as primary test fixture for both microservice and monolith modes
- **Mock LLMProvider**: Return canned markdown responses with correct Spec-Kit structure for unit tests
- **Snapshot tests**: Captured prompts per phase × architecture type in `tests/snapshots/test_prompt_assembly/`

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [US*] label maps task to specific user story for traceability
- TDD: Write test file FIRST → verify tests FAIL → implement → verify tests PASS
- All new modules in `src/specforge/core/` — zero external dependencies (subprocess is stdlib)
- Total: 54 tasks across 8 phases
- New test files: 10 (6 unit + 4 integration)
- New source files: 5 (llm_provider, prompt_assembler, output_validator, phase_prompts, output_postprocessor)
- Modified source files: 11 (config, architecture_adapter, base_phase, 7 phase files, spec_pipeline, specify_cmd, decompose_cmd)
