# Tasks: Spec Generation Pipeline

**Input**: Design documents from `/specs/005-spec-generation-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/
**Tests**: TDD enforced — test files BEFORE implementation files (Constitution Principle IV)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- Each task = one conventional commit

---

## Phase 1: Setup (Constants & Configuration)

**Purpose**: Add pipeline constants to config.py and create the phases package

- [x] T001 Add pipeline constants to `src/specforge/core/config.py`: PIPELINE_STATE_FILENAME, PIPELINE_LOCK_FILENAME, LOCK_STALE_THRESHOLD_MINUTES, PIPELINE_PHASE_STATUSES, PIPELINE_PHASES, SHARED_ENTITIES_PATH, CONTRACTS_DIR, STUB_CONTRACT_SUFFIX
  - **Commit**: `feat(005): add pipeline constants to config.py`
- [x] T002 Create empty `src/specforge/core/phases/__init__.py` package with PhaseDefinition frozen dataclass and PHASE_DEFINITIONS registry tuple
  - **Commit**: `feat(005): create phases package with PhaseDefinition registry`

---

## Phase 2: Foundational (Core Data Models + State)

**Purpose**: ServiceContext, PipelineState, PipelineLock — MUST complete before any phase runner or orchestrator

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

- [x] T003 [P] Write unit tests for ServiceContext in `tests/unit/test_service_context.py`: load_from_manifest() with microservice manifest, monolith manifest; resolve_target() for slug and feature number; error cases (missing service, missing manifest, zero features); FeatureInfo/ServiceDependency/EventInfo dataclass construction
  - **Commit**: `test(005): add unit tests for ServiceContext and target resolution`
- [x] T004 [P] Write unit tests for PipelineState in `tests/unit/test_pipeline_state.py`: create_initial_state(), save_state()/load_state() round-trip, mark_in_progress()/mark_complete()/mark_failed() transitions, detect_interrupted() recovery, is_phase_complete(), get_next_phase(), --force reset logic
  - **Commit**: `test(005): add unit tests for PipelineState transitions`
- [x] T005 [P] Write unit tests for PipelineLock in `tests/unit/test_pipeline_lock.py`: acquire_lock() creates file atomically, release_lock() removes file, acquire fails when lock exists, is_stale() with old timestamp, stale lock override, concurrent lock for different services succeeds
  - **Commit**: `test(005): add unit tests for PipelineLock acquire/release/stale`

### Implementation for Foundational

- [x] T006 Implement ServiceContext, FeatureInfo, ServiceDependency, EventInfo frozen dataclasses and load_from_manifest()/resolve_target() in `src/specforge/core/service_context.py`
  - **Commit**: `feat(005): implement ServiceContext with manifest loading and target resolution`
- [x] T007 Implement PipelineState, PhaseStatus frozen dataclasses and save_state()/load_state()/create_initial_state()/mark_in_progress()/mark_complete()/mark_failed()/detect_interrupted()/get_next_phase() in `src/specforge/core/pipeline_state.py`
  - **Commit**: `feat(005): implement PipelineState with atomic save/load and transitions`
- [x] T008 Implement PipelineLock with acquire_lock() (O_CREAT|O_EXCL), release_lock(), is_stale() in `src/specforge/core/pipeline_lock.py`
  - **Commit**: `feat(005): implement PipelineLock with cross-platform atomic locking`

**Checkpoint**: All data models, state management, and locking are functional. Run `uv run pytest tests/unit/test_service_context.py tests/unit/test_pipeline_state.py tests/unit/test_pipeline_lock.py`

---

## Phase 3: Architecture Adapters

**Purpose**: ArchitectureAdapter Protocol + 3 implementations that inject architecture-specific content

### Tests for Architecture Adapters

- [x] T009 Write unit tests for ArchitectureAdapter in `tests/unit/test_architecture_adapter.py`: MicroserviceAdapter.get_plan_sections() returns 5 deployment sections (Docker, health checks, service registration, circuit breakers, API gateway); get_task_extras() includes container/registration/contract tasks; get_edge_case_extras() includes service-down/network-partition/eventual-consistency/timeout; get_datamodel_context() returns isolated scope with api_contract refs; get_research_extras() returns service mesh/API versioning/distributed tracing questions; MonolithAdapter.get_plan_sections() returns shared DB/auth; get_datamodel_context() returns module scope with shared_table refs; get_research_extras() returns contention/dependency questions; ModularMonolithAdapter inherits monolith + adds boundary enforcement/interface checks; get_datamodel_context() returns strict_module scope with no_cross_module_db=True; get_research_extras() adds boundary enforcement/interface versioning questions; create_adapter() factory returns correct type; get_context() returns correct template vars per architecture
  - **Commit**: `test(005): add unit tests for 3 ArchitectureAdapter implementations`

### Implementation for Architecture Adapters

- [x] T010 Implement ArchitectureAdapter Protocol, MicroserviceAdapter, MonolithAdapter, ModularMonolithAdapter, and create_adapter() factory in `src/specforge/core/architecture_adapter.py`
  - **Commit**: `feat(005): implement ArchitectureAdapter protocol with 3 adapters`

**Checkpoint**: All adapters produce correct context dicts. Run `uv run pytest tests/unit/test_architecture_adapter.py`

---

## Phase 4: User Story 1 — Single Service Specification Generation (Priority: P1) 🎯 MVP

**Goal**: `specforge specify <service>` generates spec.md for a service, reading manifest.json and organizing user stories by domain capability

**Independent Test**: Run `specforge specify identity-service` against a test manifest → spec.md created in `.specforge/features/identity-service/`

### Tests for US1

- [x] T011 Write unit tests for BasePhase in `tests/unit/test_phases/test_base_phase.py`: run() validates prerequisites, calls _build_context(), renders template, writes artifact; _post_render() hook is optional; returns Result with artifact path
  - **Commit**: `test(005): add unit tests for BasePhase template method`
- [x] T012 [P] [US1] Write unit tests for SpecifyPhase in `tests/unit/test_phases/test_specify_phase.py`: groups features by category into domain capabilities; adds "Service Dependencies" section for microservice; omits dependencies section for monolith; handles 1-feature service (no sub-sections); handles 4+ feature service (sub-sections); includes module context for monolith/modular-monolith
  - **Commit**: `test(005): add unit tests for SpecifyPhase domain capability grouping`

### Implementation for US1

- [x] T013 Implement BasePhase with run() template method, _build_context() abstract method, _post_render() hook in `src/specforge/core/phases/base_phase.py`
  - **Commit**: `feat(005): implement BasePhase with template method pattern`
- [x] T014 [US1] Implement SpecifyPhase in `src/specforge/core/phases/specify_phase.py`: _build_context() groups features into domain capabilities, adds service dependencies for microservice, adds module context for monolith
  - **Commit**: `feat(005): implement SpecifyPhase with domain capability grouping`
- [x] T015 [US1] Enhance `src/specforge/templates/base/features/spec.md.j2` with service context: `{% if service %}` guard, `{% for capability in capabilities %}` loop for user stories, `{% if architecture == 'microservice' %}` for Service Dependencies section, backward-compatible with existing usage
  - **Commit**: `feat(005): enhance spec.md.j2 with service context and architecture blocks`

**Checkpoint**: SpecifyPhase generates correct spec.md for microservice and monolith. Run `uv run pytest tests/unit/test_phases/`

---

## Phase 5: User Story 2 — Full Pipeline Execution with Phase Tracking (Priority: P1)

**Goal**: All 6 phases execute in order with state tracking, skip completed phases, resume from interrupts

**Independent Test**: Run full pipeline, verify 7 artifacts exist, delete one, re-run → only missing phase executes

### Tests for US2

- [x] T016 [P] [US2] Write unit tests for ResearchPhase in `tests/unit/test_phases/test_research_phase.py`: uses spec.md content as input context, generates research.md; includes adapter research extras via get_research_extras(); microservice includes service mesh/API versioning questions; modular-monolith includes boundary enforcement questions; monolith includes contention questions
  - **Commit**: `test(005): add unit tests for ResearchPhase`
- [x] T017 [P] [US2] Write unit tests for PlanPhase in `tests/unit/test_phases/test_plan_phase.py`: uses spec+research+datamodel as input; injects PromptContextBuilder output; adds adapter plan sections for microservice; omits deployment sections for monolith; adds module boundary enforcement for modular-monolith; gracefully degrades when governance prompt files do not exist (FR-065) — plan.md generated without prompt context, no error raised
  - **Commit**: `test(005): add unit tests for PlanPhase with prompt injection`
- [x] T018 [P] [US2] Write unit tests for ChecklistPhase in `tests/unit/test_phases/test_checklist_phase.py`: validates previous artifacts exist; adds adapter checklist items; adds boundary check for modular-monolith
  - **Commit**: `test(005): add unit tests for ChecklistPhase`
- [x] T019 [P] [US2] Write unit tests for TasksPhase in `tests/unit/test_phases/test_tasks_phase.py`: generates ordered tasks; adds container/registration tasks for microservice; omits Docker tasks for monolith
  - **Commit**: `test(005): add unit tests for TasksPhase`
- [x] T020 [US2] Write unit tests for PipelineOrchestrator in `tests/unit/test_spec_pipeline.py`: executes phases in order; skips completed phases; --force resets all; --from validates prerequisites; acquires/releases lock; detects interrupted phases; saves state after each phase; handles phase failure gracefully
  - **Commit**: `test(005): add unit tests for PipelineOrchestrator phase ordering and skip logic`

### Implementation for US2

- [x] T021 [P] [US2] Implement ResearchPhase in `src/specforge/core/phases/research_phase.py`
  - **Commit**: `feat(005): implement ResearchPhase`
- [x] T022 [P] [US2] Implement PlanPhase in `src/specforge/core/phases/plan_phase.py` with PromptContextBuilder integration
  - **Commit**: `feat(005): implement PlanPhase with prompt context injection`
- [x] T023 [P] [US2] Implement ChecklistPhase in `src/specforge/core/phases/checklist_phase.py`
  - **Commit**: `feat(005): implement ChecklistPhase with adapter extras`
- [x] T024 [P] [US2] Implement TasksPhase in `src/specforge/core/phases/tasks_phase.py`
  - **Commit**: `feat(005): implement TasksPhase with architecture-conditional tasks`
- [x] T025 [US2] Implement PipelineOrchestrator in `src/specforge/core/spec_pipeline.py`: constructor injection of TemplateRegistry + TemplateRenderer + PromptContextBuilder; run() method with lock acquire, state load, phase execution loop, parallel phase 3 via ThreadPoolExecutor, state save, lock release in finally
  - **Commit**: `feat(005): implement PipelineOrchestrator with state tracking and parallel phase 3`
- [x] T026 [P] [US2] Enhance `src/specforge/templates/base/features/research.md.j2` with service context blocks
  - **Commit**: `feat(005): enhance research.md.j2 with service context`
- [x] T027 [P] [US2] Enhance `src/specforge/templates/base/features/plan.md.j2` with `{% for section in adapter_sections %}` loop and architecture conditionals
  - **Commit**: `feat(005): enhance plan.md.j2 with adapter section loops`
- [x] T028 [P] [US2] Enhance `src/specforge/templates/base/features/checklist.md.j2` with adapter checklist items
  - **Commit**: `feat(005): enhance checklist.md.j2 with adapter checklist items`
- [x] T029 [P] [US2] Enhance `src/specforge/templates/base/features/tasks.md.j2` with adapter task loops
  - **Commit**: `feat(005): enhance tasks.md.j2 with adapter task loops`

**Checkpoint**: Full pipeline runs end-to-end with state tracking. Run `uv run pytest tests/unit/test_spec_pipeline.py tests/unit/test_phases/`

---

## Phase 6: User Story 3 — Architecture-Conditional Artifact Generation (Priority: P2)

**Goal**: Microservice artifacts include deployment concerns; monolith artifacts reference shared infrastructure; modular-monolith adds interface definitions

**Independent Test**: Generate plan.md for same service under microservice vs monolith → compare sections present

### Tests for US3

- [x] T030 [P] [US3] Write unit tests for DatamodelPhase in `tests/unit/test_phases/test_datamodel_phase.py`: uses get_datamodel_context() from adapter for entity scoping; builds entity list scoped to service; creates shared_entities.md for monolith and modular-monolith; creates API contract references for microservice; applies strict module boundary constraints for modular-monolith (no_cross_module_db=True); covers all features in unified schema
  - **Commit**: `test(005): add unit tests for DatamodelPhase boundary scoping`
- [x] T031 [P] [US3] Write unit tests for EdgecasePhase in `tests/unit/test_phases/test_edgecase_phase.py`: base edge cases + adapter extras; microservice includes service-down/network-partition/eventual-consistency; monolith includes module boundary violations; modular-monolith includes interface contract violations
  - **Commit**: `test(005): add unit tests for EdgecasePhase architecture-specific scenarios`

### Implementation for US3

- [x] T032 [P] [US3] Implement DatamodelPhase in `src/specforge/core/phases/datamodel_phase.py` with _post_render() hook for shared_entities.md creation
  - **Commit**: `feat(005): implement DatamodelPhase with service boundary scoping`
- [x] T033 [P] [US3] Implement EdgecasePhase in `src/specforge/core/phases/edgecase_phase.py`
  - **Commit**: `feat(005): implement EdgecasePhase with architecture extras`
- [x] T034 [P] [US3] Enhance `src/specforge/templates/base/features/datamodel.md.j2` with entity loops, architecture conditionals, and API contract reference blocks
  - **Commit**: `feat(005): enhance datamodel.md.j2 with entity loops and arch conditionals`
- [x] T035 [P] [US3] Enhance `src/specforge/templates/base/features/edge-cases.md.j2` with adapter edge case loops
  - **Commit**: `feat(005): enhance edge-cases.md.j2 with adapter edge case loops`

**Checkpoint**: Architecture-specific artifacts generate correctly. Run `uv run pytest tests/unit/test_phases/test_datamodel_phase.py tests/unit/test_phases/test_edgecase_phase.py`

---

## Phase 7: User Story 4 — Data Model Scoping by Service Boundary (Priority: P2)

**Goal**: Microservice data models are isolated; monolith modules share entities via shared_entities.md

**Independent Test**: Generate data-model.md for ledger-service in microservice mode → contains only account/transaction entities

This story's implementation is covered by T030-T032 (DatamodelPhase). This phase adds the shared_entities.md cross-module behavior.

- [x] T036 [US4] Write unit tests for shared_entities.md generation in `tests/unit/test_phases/test_datamodel_phase.py` (append to existing): create new shared_entities.md; update existing shared_entities.md; no shared_entities.md for microservice
  - **Commit**: `test(005): add unit tests for shared_entities.md generation`
- [x] T037 [US4] Extend DatamodelPhase._post_render() in `src/specforge/core/phases/datamodel_phase.py` to create/update `.specforge/shared_entities.md` for monolith and modular-monolith architectures
  - **Commit**: `feat(005): implement shared_entities.md for monolith data model scoping`

**Checkpoint**: Monolith data-model.md references shared entities correctly. Run `uv run pytest tests/unit/test_phases/test_datamodel_phase.py`

---

## Phase 8: User Story 7 — Dependency Stub Contract Generation (Priority: P3)

**Goal**: Generate stub api-spec.stub.json for unspecified dependent services so planning can proceed

**Independent Test**: Run pipeline for ledger-service before identity-service → stub contract generated

- [x] T038 [US7] Write unit tests for stub contract generation in `tests/unit/test_spec_pipeline.py` (append): stub generated when dependent service has no contracts/; stub not generated when real contract exists; warning when real contract deviates from stub
  - **Commit**: `test(005): add unit tests for stub contract generation`
- [x] T039 [US7] Implement stub contract generation in PipelineOrchestrator plan phase hook in `src/specforge/core/spec_pipeline.py`: check dependent service contracts/ dir, generate api-spec.stub.json from manifest communication patterns
  - **Commit**: `feat(005): implement stub contract generation for unspecified dependencies`
- [x] T040 [US7] Implement api-spec.json generation in DatamodelPhase._post_render() for microservice architecture in `src/specforge/core/phases/datamodel_phase.py`: simplified JSON schema from data model entities and communication patterns
  - **Commit**: `feat(005): implement api-spec.json contract generation for microservices`

**Checkpoint**: Stub and real contracts generate correctly. Run `uv run pytest tests/unit/test_spec_pipeline.py -k stub`

---

## Phase 9: CLI Commands

**Purpose**: Wire pipeline into Click CLI commands

- [x] T041 [US1] Write integration tests for specify command in `tests/integration/test_specify_cmd.py`: `specforge specify <slug>` runs pipeline; `specforge specify <number>` resolves to service; `--force` flag works; `--from` flag validates prerequisites; error on missing manifest; error on unknown service
  - **Commit**: `test(005): add integration tests for specforge specify command`
- [x] T042 [US1] Implement specify command in `src/specforge/cli/specify_cmd.py`: Click command with target argument, --force flag, --from option; Rich console output with phase progress; delegates to PipelineOrchestrator
  - **Commit**: `feat(005): implement specforge specify CLI command`
- [x] T043 Write integration tests for pipeline-status command in `tests/integration/test_pipeline_status_cmd.py`: shows all services; shows single service phases; handles no pipeline state
  - **Commit**: `test(005): add integration tests for specforge pipeline-status command`
- [x] T044 Implement pipeline-status command in `src/specforge/cli/pipeline_status_cmd.py`: Click command with optional target; Rich table output showing phase status
  - **Commit**: `feat(005): implement specforge pipeline-status CLI command`
- [x] T045 Register specify and pipeline-status commands in `src/specforge/cli/main.py` via cli.add_command()
  - **Commit**: `feat(005): register specify and pipeline-status commands in CLI`

**Checkpoint**: CLI commands work end-to-end. Run `uv run pytest tests/integration/test_specify_cmd.py tests/integration/test_pipeline_status_cmd.py`

---

## Phase 10: Integration Tests & Snapshots

**Purpose**: Full end-to-end pipeline validation for both architecture types

- [x] T046 [P] Write microservice E2E integration test in `tests/integration/test_pipeline_microservice.py`: create mock manifest (microservice, 2 services with 3+2 features), run pipeline for ledger-service, verify all 7 artifacts + contracts/ + api-spec.json, verify spec.md has Service Dependencies section, verify plan.md has Docker/health-check/circuit-breaker sections, verify data-model.md has no cross-service entities
  - **Commit**: `test(005): add microservice E2E integration test`
- [x] T047[P] Write monolith E2E integration test in `tests/integration/test_pipeline_monolith.py`: create mock manifest (monolithic, 3 modules), run pipeline for auth module, verify all 7 artifacts, verify NO contracts/ dir, verify plan.md references shared infrastructure, verify data-model.md references shared_entities.md
  - **Commit**: `test(005): add monolith E2E integration test`
- [x] T047b [P] Write modular-monolith E2E integration test in `tests/integration/test_pipeline_modular_monolith.py`: create mock manifest (modular-monolith, 3 modules with 2+1+2 features), run pipeline for payments module, verify all 7 artifacts + interfaces.md generated, verify NO contracts/ dir, verify plan.md has module boundary enforcement rules, verify checklist.md has no cross-module DB access check, verify edge-cases.md has interface contract violation scenarios, verify data-model.md has strict module boundary constraints, verify shared_entities.md created at project level
  - **Commit**: `test(005): add modular-monolith E2E integration test`
- [x] T047c [P] Write single-feature service E2E integration test in `tests/integration/test_pipeline_single_feature.py`: create mock manifest (microservice, 1 service with 1 feature), run pipeline, verify all 7 artifacts generated, verify spec.md has NO domain capability sub-sections (sub-sections only for 4+ features), verify data-model.md contains only that feature's entities
  - **Commit**: `test(005): add single-feature service E2E integration test`
- [x] T048 [P] Write pipeline resume integration test in `tests/integration/test_pipeline_resume.py`: run pipeline partially (interrupt after phase 2), re-run and verify phases 1-2 skipped, verify --force resets all, verify stale lock detection
  - **Commit**: `test(005): add pipeline resume and state recovery integration test`
- [x] T049 [P] Create snapshot golden files in `tests/snapshots/`: spec_microservice.md, spec_monolith.md, spec_modular_monolith.md, plan_microservice.md, plan_monolith.md, plan_modular_monolith.md, datamodel_modular_monolith.md for template rendering output validation
  - **Commit**: `test(005): add snapshot golden files for pipeline template output`

**Checkpoint**: All integration tests pass. Run `uv run pytest tests/integration/test_pipeline_*.py`

---

## Phase 11: Polish & Cross-Cutting Concerns

- [x] T050 Run `uv run ruff check src/specforge/core/phases/ src/specforge/core/spec_pipeline.py src/specforge/core/service_context.py src/specforge/core/pipeline_state.py src/specforge/core/pipeline_lock.py src/specforge/core/architecture_adapter.py src/specforge/cli/specify_cmd.py src/specforge/cli/pipeline_status_cmd.py` and fix all lint errors
  - **Commit**: `chore(005): fix ruff lint errors`
- [x] T051 Run `uv run pytest --cov=specforge --cov-report=term-missing` and verify coverage for new modules meets 100% on core domain logic
  - **Commit**: `test(005): verify test coverage for pipeline modules`
- [x] T052 Verify existing Feature 001-004 tests still pass with `uv run pytest tests/` — no regressions from template modifications or config.py additions
  - **Commit**: `test(005): verify no regressions in Features 001-004`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (Adapters)**: Depends on Phase 1 (config constants)
- **Phase 4 (US1 - Specify)**: Depends on Phase 2 + Phase 3
- **Phase 5 (US2 - Pipeline)**: Depends on Phase 4 (needs BasePhase + SpecifyPhase)
- **Phase 6 (US3 - Architecture)**: Depends on Phase 3 (adapters) + Phase 4 (BasePhase)
- **Phase 7 (US4 - Data Scoping)**: Depends on Phase 6 (DatamodelPhase)
- **Phase 8 (US7 - Stubs)**: Depends on Phase 5 (orchestrator) + Phase 6 (datamodel)
- **Phase 9 (CLI)**: Depends on Phase 5 (orchestrator)
- **Phase 10 (Integration)**: Depends on Phase 9 (CLI commands)
- **Phase 11 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1 - Specify)**: Needs foundational + adapters → can start after Phase 3
- **US2 (P1 - Pipeline)**: Needs US1 (BasePhase) → sequential after Phase 4
- **US3 (P2 - Architecture)**: Needs adapters + BasePhase → can run in parallel with US2 after Phase 4
- **US4 (P2 - Data Scoping)**: Needs DatamodelPhase from US3 → sequential after Phase 6
- **US7 (P3 - Stubs)**: Needs orchestrator + datamodel → after Phase 5 + 6

### Within Each Phase

- Tests MUST be written FIRST and FAIL before implementation
- Frozen dataclasses before functions that use them
- Base classes before subclasses
- Core modules before CLI integration

### Parallel Opportunities

Within Phase 2: T003, T004, T005 (tests) can run in parallel; T006, T007, T008 (implementations) are independent files
Within Phase 5: T016-T019 (phase runner tests) can run in parallel; T021-T024 (implementations) can run in parallel; T026-T029 (templates) can run in parallel
Within Phase 6: T030-T031 (tests) parallel; T032-T035 (implementations + templates) parallel
Within Phase 10: T046-T049 (integration tests) can all run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all foundational tests in parallel:
T003: "Unit tests for ServiceContext in tests/unit/test_service_context.py"
T004: "Unit tests for PipelineState in tests/unit/test_pipeline_state.py"
T005: "Unit tests for PipelineLock in tests/unit/test_pipeline_lock.py"

# After tests written, launch implementations in parallel:
T006: "ServiceContext in src/specforge/core/service_context.py"
T007: "PipelineState in src/specforge/core/pipeline_state.py"
T008: "PipelineLock in src/specforge/core/pipeline_lock.py"
```

## Parallel Example: Phase 5 (Pipeline Phase Runners)

```bash
# Launch all phase runner tests in parallel:
T016: "ResearchPhase tests"
T017: "PlanPhase tests"
T018: "ChecklistPhase tests"
T019: "TasksPhase tests"

# After tests, launch implementations in parallel:
T021: "ResearchPhase implementation"
T022: "PlanPhase implementation"
T023: "ChecklistPhase implementation"
T024: "TasksPhase implementation"

# Templates in parallel:
T026: "research.md.j2"  T027: "plan.md.j2"  T028: "checklist.md.j2"  T029: "tasks.md.j2"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T008)
3. Complete Phase 3: Adapters (T009-T010)
4. Complete Phase 4: US1 - SpecifyPhase (T011-T015)
5. **STOP and VALIDATE**: `specforge specify identity-service` generates correct spec.md
6. This alone delivers value — developers can generate unified service specs

### Incremental Delivery

1. Setup + Foundational + Adapters → Foundation ready
2. Add US1 (SpecifyPhase) → spec.md generation works → **MVP**
3. Add US2 (Full Pipeline) → all 7 artifacts generate with state tracking
4. Add US3 (Architecture) → artifacts adapt to microservice/monolith/modular-monolith
5. Add US4 (Data Scoping) → data models respect service boundaries
6. Add US7 (Stubs) → dependent services don't block pipeline
7. CLI + Integration → production-ready commands

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US5 (edge cases) and US6 (parallel execution) are covered by US2/US3 implementation tasks (EdgecasePhase in T031-T033, ThreadPoolExecutor in T025)
- Total: 54 tasks across 11 phases
- Verify tests fail before implementing
- One conventional commit per task
