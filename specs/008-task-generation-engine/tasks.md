# Tasks: Task Generation Engine

**Input**: Design documents from `/specs/008-task-generation-engine/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅
**Tests**: TDD — tests written FIRST, must FAIL before implementation

**Organization**: Tasks grouped by user story (US1–US5) to enable independent implementation. Critical path: DependencyResolver + BuildSequence are prerequisites for all stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Config constants, test fixtures, project structure

- [ ] T001 Add Feature 008 task generation constants to src/specforge/core/config.py — add `TASK_ID_PREFIX`, `CROSS_SERVICE_TASK_PREFIX`, `CROSS_SERVICE_TARGET`, `MAX_TASKS_PER_SERVICE`, `EFFORT_SIZES`, `EFFORT_BUMP_THRESHOLD_FEATURES`, `EFFORT_BUMP_THRESHOLD_DEPS`, `CROSS_SERVICE_CATEGORIES`, `MICROSERVICE_STEP_COUNT`, `MONOLITH_STEP_COUNT`, `CONDITIONAL_STEPS` dict per plan §D10
- [ ] T002 [P] Create test fixture directory and PersonalFinance manifest variants in tests/fixtures/task_generation/ — create `microservice_manifest.json` (identity-service 0 deps 0 events, ledger-service 1 dep on identity with pattern="gRPC" and 1 event TransactionCreated, analytics-service 3 deps on identity+ledger+notification with 2 events TransactionCreated[consumer]+AnalyticsRequested[producer]), `monolith_manifest.json` (auth, billing, reporting modules), `modular_monolith_manifest.json` (same modules with strict_boundaries), `bidirectional_events_manifest.json` (serviceA produces EventX consumed by serviceB, serviceB produces EventY consumed by serviceA), `sample_plan.md` with Summary/Technical Context/Design Decisions sections

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and build sequences — MUST complete before ANY user story

**⚠️ CRITICAL**: All user stories depend on these frozen dataclasses and build sequence definitions

### Tests First

- [ ] T003 [P] Write tests for EffortSize type, BuildStep frozen dataclass (creation, immutability, field access), TaskItem frozen dataclass (all 12 fields, dependency tuple, governance_rules tuple), TaskFile (phase grouping, total_count), DependencyGraph (adjacency, in_degree), GenerationSummary in tests/unit/test_task_models.py
- [ ] T004 [P] Write tests for MICROSERVICE_BUILD_SEQUENCE (14 steps, correct order/category/effort/depends_on/parallelizable_with per plan §D4) and MONOLITH_BUILD_SEQUENCE (7 steps) in tests/unit/test_build_sequence.py — verify step 6 communication_clients depends on step 5, step 7 controllers parallelizable_with step 6, step 8 events parallelizable_with steps 6+7
- [ ] T005 [P] Write tests for EffortEstimator.estimate() in tests/unit/test_effort_estimator.py — test base defaults (scaffolding=S, domain_models=M, service_layer=L, integration_tests=XL), feature count bump (>3 features: M→L, L→XL for all applicable steps per plan §D6 complete table), dependency count bump (>2 deps on communication_clients: M→L), XL cap (never exceeds XL), no bump when below threshold, verify health_checks stays S regardless of feature count

### Implementation

- [ ] T006 Implement EffortSize literal type, BuildStep, TaskItem, TaskFile, DependencyGraph, GenerationSummary frozen dataclasses in src/specforge/core/task_models.py per data-model.md — all frozen, tuple fields, validation rules in docstrings
- [ ] T007 [P] Implement MICROSERVICE_BUILD_SEQUENCE (14 BuildStep instances) and MONOLITH_BUILD_SEQUENCE (7 BuildStep instances) as module-level constants in src/specforge/core/build_sequence.py per plan §D4 — include `get_sequence(architecture: str) -> tuple[BuildStep, ...]` factory function
- [ ] T008 [P] Implement EffortEstimator class with `estimate(step, feature_count, dependency_count) -> EffortSize` in src/specforge/core/effort_estimator.py per plan §D6 — bump logic reads thresholds from config.py, cap at XL

**Checkpoint**: All data models importable, build sequences defined, effort estimator works. Run `pytest tests/unit/test_task_models.py tests/unit/test_build_sequence.py tests/unit/test_effort_estimator.py` — all must pass.

---

## Phase 3: User Story 1 — Per-Service Microservice Task Generation (Priority: P1) 🎯 MVP

**Goal**: Generate ordered, dependency-aware tasks.md for a single microservice service reading manifest + plan

**Independent Test**: Provide sample manifest with identity-service (0 deps), generate tasks, verify 14-step ordering with correct file paths and effort sizes

### Tests for User Story 1

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Write tests for DependencyResolver.build_graph() in tests/unit/test_dependency_resolver.py — test DAG construction from TaskItem list, adjacency list correctness, in_degree computation, reference integrity validation (Err on missing dependency ID)
- [ ] T010 [P] [US1] Write tests for DependencyResolver.topological_sort() in tests/unit/test_dependency_resolver.py — test Kahn's algorithm output order, stable secondary sort by (phase, order), verify no task appears before its dependencies, test with identity-service tasks (linear chain) and ledger-service tasks (branching after service_layer)
- [ ] T011 [P] [US1] Write tests for DependencyResolver cycle detection in tests/unit/test_dependency_resolver.py — test circular dependency returns Err with cycle path string like `"Circular dependency: A → B → C → A"`, test self-referential task, test valid DAG returns Ok
- [ ] T012 [P] [US1] Write tests for GovernanceReader.get_relevant_rules() in tests/unit/test_governance_reader.py — test scope-to-layer mapping per plan §D7 complete table (scope:"function"→service/repository/controllers/communication_clients, scope:"class"→model/entity, scope:"module"→scaffolding/gateway/container, scope:"file"→database/health_checks/events, scope:"test"→unit_tests/integration_tests/contract_tests), test architecture filter, test graceful degradation when no governance files exist (returns empty tuple), test unmapped steps return empty tuple, test read-only contract (no writes to prompts dir), verify returned rule IDs use Feature 003 namespace (ARCH-, BACK-, SEC-, DB-, TEST-)
- [ ] T013 [US1] Write tests for TaskGenerator.generate_for_service() with identity-service (0 deps) in tests/unit/test_task_generator.py — verify all 14 microservice steps present (minus conditional: no communication_clients step 6, no contract tests step 10 since 0 deps, no event_handlers step 8 since 0 events), verify file paths use `src/identity-service/` prefix, verify effort sizes match build sequence defaults, verify task IDs sequential T001-T0xx
- [ ] T014 [US1] Write tests for TaskGenerator.generate_for_service() with ledger-service (1 dep on identity-service) in tests/unit/test_task_generator.py — verify step 6 (communication_clients) IS present with description containing "identity-service" and communication pattern from ServiceDependency.pattern (e.g., "Create identity-service gRPC client" when pattern="gRPC", "Create identity-service REST client" when pattern="REST"), verify step 6 depends on step 5 (service_layer), verify step 10 (contract tests) IS present, verify XDEP reference to cross-service-infra/X-T001 in communication client task
- [ ] T015 [US1] Write tests for TaskGenerator.generate_for_service() with analytics-service (3 deps) in tests/unit/test_task_generator.py — verify 3 communication client tasks generated (one per dependency, each using correct pattern from ServiceDependency.pattern), verify effort bumped to L for communication_clients step (>2 deps triggers bump), verify all 3 contract test tasks generated, verify service with 2 events (TransactionCreated, AnalyticsRequested) produces 2 event handler tasks with correct producer/consumer roles per EventInfo
- [ ] T016 [US1] Write tests for step filtering (FR-014) in tests/unit/test_task_generator.py — test that step 6 (communication_clients) omitted when dependencies empty, step 8 (events) omitted when events empty, step 10 (contract tests) omitted when no deps, verify omitted steps don't appear in output TaskFile

### Implementation for User Story 1

- [ ] T017 [US1] Implement DependencyResolver class in src/specforge/core/dependency_resolver.py — `build_graph()` creates adjacency list + validates references, `topological_sort()` uses Kahn's algorithm with (phase, order) stable sort, cycle detection via incomplete processing (remaining nodes after Kahn's = cycle), return Err with cycle path per plan §D3
- [ ] T018 [US1] Implement GovernanceReader class in src/specforge/core/governance_reader.py — constructor takes PromptLoader, `get_relevant_rules(layer, architecture)` loads PromptSet, filters by scope→layer mapping per research §R-005, returns tuple[str, ...] of rule_ids, empty tuple fallback if no files
- [ ] T019 [US1] Implement TaskGenerator class in src/specforge/core/task_generator.py — constructor injection (manifest_path, prompt_loader, renderer, registry), `generate_for_service(service_slug, plan_content)` implements 10-step pipeline per plan §D2: load ServiceContext → select BuildSequence → filter inapplicable steps → generate TaskItems → resolve governance rules → assign effort → build DAG → topological sort → cap at 50 → return TaskFile
- [ ] T020 [US1] Write integration test for microservice task generation in tests/integration/test_task_generation_microservice.py — use PersonalFinance microservice manifest fixture, generate tasks for ledger-service, verify output tasks.md contains all applicable steps in correct order, verify file paths, verify effort sizes, verify XDEP notation present

**Checkpoint**: Single microservice service task generation works. Run `pytest tests/unit/test_dependency_resolver.py tests/unit/test_governance_reader.py tests/unit/test_task_generator.py tests/integration/test_task_generation_microservice.py` — all must pass.

---

## Phase 4: User Story 2 — Cross-Service Infrastructure Tasks (Priority: P1)

**Goal**: Generate dedicated cross-service-infra/tasks.md with shared infrastructure tasks (once, not per-service)

**Independent Test**: Provide manifest with 3 services, generate full project, verify cross-service-infra/tasks.md exists with 5 task categories appearing exactly once

### Tests for User Story 2

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T021 [P] [US2] Write tests for CrossServiceTaskGenerator.generate() with 3 services in tests/unit/test_cross_service_tasks.py — verify 5 task categories (shared_contracts, docker_compose, message_broker, api_gateway, shared_auth) each appear exactly once, verify target_name="cross-service-infra", verify X-T prefix (X-T001 through X-T005)
- [ ] T022 [P] [US2] Write tests for conditional filtering in tests/unit/test_cross_service_tasks.py — no message broker task (X-T003) if zero async events across all services, no gateway task (X-T004) if no REST/gRPC endpoints declared, always include shared_contracts and shared_auth
- [ ] T023 [P] [US2] Write tests for architecture guard in tests/unit/test_cross_service_tasks.py — monolithic architecture returns Ok(empty TaskFile with total_count=0), microservice returns full TaskFile (all 5 categories), modular-monolith returns TaskFile with subset (shared_contracts X-T001, shared_auth X-T005 only — no Docker compose, no message broker, no gateway per plan §D5 architecture scope table)
- [ ] T024 [US2] Write tests for XDEP injection in tests/unit/test_task_generator.py — verify that when generate_for_project() runs, per-service communication client tasks get `[XDEP: cross-service-infra/X-T001]` added to dependencies, verify event handler tasks get `[XDEP: cross-service-infra/X-T003]` added to dependencies when async events are declared, verify no XDEP references in cross-service-infra's own tasks
- [ ] T024b [P] [US2] Write edge case test for bidirectional event communication in tests/unit/test_cross_service_tasks.py — given service A produces EventX consumed by service B AND service B produces EventY consumed by service A, verify both producer and consumer handler tasks generated in each service without duplication, verify X-T003 (message broker) generated exactly once, verify no false circular dependency error (event cycles are valid, service dependency cycles are not)

### Implementation for User Story 2

- [ ] T025 [US2] Implement CrossServiceTaskGenerator class in src/specforge/core/cross_service_tasks.py — constructor takes manifest_path, `generate(services)` collects communication patterns + events across all services, generates X-T prefixed tasks per plan §D5, filters by declared concerns, architecture guard returns empty for monolithic
- [ ] T026 [US2] Write integration test for full PersonalFinance manifest cross-service generation in tests/integration/test_task_generation_microservice.py — generate for entire project, verify cross-service-infra/tasks.md produced, verify identity-service/tasks.md does NOT contain any cross-service tasks, verify ledger-service gRPC client task references X-T001

**Checkpoint**: Cross-service deduplication verified. Run `pytest tests/unit/test_cross_service_tasks.py tests/integration/test_task_generation_microservice.py` — all must pass. Verify no shared tasks duplicated in per-service files.

---

## Phase 5: User Story 3 — Monolith Mode Simplified Tasks (Priority: P2)

**Goal**: Generate 7-step monolith task lists per module — no Docker, gRPC, circuit breaker, gateway, health checks, contract tests

**Independent Test**: Provide monolith manifest with auth module, generate tasks, verify exactly 7 categories with shared DbContext references

### Tests for User Story 3

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T027 [P] [US3] Write tests for monolith 7-step sequence generation in tests/unit/test_task_generator.py — test with auth module, verify exactly 7 task categories (folder_structure → domain_models → database → repo_service → controllers → boundary_interface → tests), verify file paths use `src/modules/auth/` prefix
- [ ] T028 [P] [US3] Write tests for monolith exclusion list in tests/unit/test_task_generator.py — verify zero tasks with categories: container_optimization, communication_clients, event_handlers, health_checks, contract_tests, gateway_config — assert none of these strings appear in any TaskItem.category
- [ ] T029 [P] [US3] Write tests for shared DbContext references in tests/unit/test_task_generator.py — verify database task description contains "shared DbContext" or "AppDbContext", not per-service context names
- [ ] T030 [US3] Write tests for modular-monolith boundary interface in tests/unit/test_task_generator.py — verify step 6 (boundary_interface) IS present when architecture="modular-monolith", verify step 6 is OMITTED when architecture="monolithic", verify boundary_interface depends on repo_service (step 4)

### Implementation for User Story 3

- [ ] T031 [US3] Add monolith/modular-monolith handling to TaskGenerator.generate_for_service() in src/specforge/core/task_generator.py — select MONOLITH_BUILD_SEQUENCE when architecture is "monolithic" or "modular-monolith", apply conditional step filtering for boundary_interface, apply shared DbContext naming in database task descriptions
- [ ] T032 [US3] Write integration test for monolith mode in tests/integration/test_task_generation_monolith.py — use monolith manifest fixture, generate tasks for auth module, verify 7-step output, verify no microservice concerns present
- [ ] T033 [US3] Write integration test for modular-monolith mode in tests/integration/test_task_generation_modular_monolith.py — use modular-monolith manifest fixture, verify boundary_interface task present, verify shared infra tasks generated (shared_auth, shared_contracts only)

**Checkpoint**: Monolith mode produces clean 7-step output. Run `pytest tests/integration/test_task_generation_monolith.py tests/integration/test_task_generation_modular_monolith.py` — all must pass. Verify zero microservice artifacts in output.

---

## Phase 6: User Story 4 — Dependency Ordering and Parallelization Markers (Priority: P2)

**Goal**: Every task declares dependencies + [P] marker; topological ordering is correct; parallel markers are verified

**Independent Test**: Generate tasks for ledger-service, verify controllers ∥ event_handlers after service_layer, verify unit_tests before integration_tests

### Tests for User Story 4

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T034 [P] [US4] Write tests for DependencyResolver.mark_parallel() in tests/unit/test_dependency_resolver.py — test depth-level grouping (step 6 gRPC, step 7 controllers, step 8 events all at depth=5 after service_layer), test file-path disjointness marking (clients/ ≠ controllers/ ≠ events/ → all [P]), test non-parallel case (unit_tests at depth=6, integration_tests at depth=7 → not parallel, sequential)
- [ ] T035 [P] [US4] Write tests for parallel correctness with analytics-service (3 deps) in tests/unit/test_dependency_resolver.py — verify 3 communication client tasks marked [P] relative to each other (disjoint client files), verify health_checks NOT parallel with controllers (health depends on controllers), verify contract_tests parallel with unit_tests (disjoint test dirs)
- [ ] T036 [US4] Write tests for 50-task cap with high feature count service (6+ features) in tests/unit/test_task_generator.py — verify TaskFile.total_count ≤ 50, verify grouping collapses individual feature tasks into composite layer tasks like "Create all domain models for features: auth, billing, reporting, payments, notifications, analytics"

### Implementation for User Story 4

- [ ] T037 [US4] Implement DependencyResolver.mark_parallel() in src/specforge/core/dependency_resolver.py — compute depth levels via BFS from roots, group tasks by depth, within each depth group check file_paths intersection, mark disjoint tasks parallel=True per plan §D3 and research §R-002
- [ ] T038 [US4] Implement task capping/grouping logic in TaskGenerator in src/specforge/core/task_generator.py — when TaskFile.total_count > MAX_TASKS_PER_SERVICE, collapse same-layer tasks into composites per research §R-003, preserve dependency chain integrity

**Checkpoint**: Parallelization markers verified correct. Run `pytest tests/unit/test_dependency_resolver.py -k "parallel"` — all must pass. Verify no false parallels (tasks sharing file paths at same depth NOT marked [P]).

---

## Phase 7: User Story 5 — Full Project Task Generation (Priority: P3)

**Goal**: Single command generates tasks.md per service + cross-service-infra + summary

**Independent Test**: Provide manifest with 3 services, run project-level generation, verify 4 files produced (3 service + 1 cross-service-infra) + summary

### Tests for User Story 5

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T039 [P] [US5] Write tests for TaskGenerator.generate_for_project() in tests/unit/test_task_generator.py — test with PersonalFinance microservice manifest (3 services), verify GenerationSummary.generated_files has 4 entries (3 services + cross-service-infra), verify task_counts per service, verify cross_dependencies list all XDEP refs
- [ ] T040 [P] [US5] Write tests for tasks.md.bak backup strategy in tests/unit/test_task_generator.py — verify existing tasks.md renamed to tasks.md.bak before writing new, verify tasks.md.bak overwrites previous backup, verify backup works when no prior tasks.md exists (no error)
- [ ] T041 [US5] Write tests for plan.md validation (FR-015) in tests/unit/test_task_generator.py — missing plan.md produces warning in GenerationSummary.warnings and skips that service, plan missing required sections (Summary, Technical Context, Design Decisions) also produces warning, other services still generate successfully

### Implementation for User Story 5

- [ ] T042 [US5] Implement generate_for_project() in TaskGenerator in src/specforge/core/task_generator.py — load manifest, validate architecture, detect circular service deps (FR-007), generate cross-service-infra (FR-008), iterate services with plan validation (FR-015), inject XDEP refs (FR-010), backup existing files (FR-023), write all files, return GenerationSummary (FR-017)
- [ ] T043 [US5] Write integration test for full-project generation in tests/integration/test_generate_tasks_cmd.py — use PersonalFinance microservice manifest, run via pipeline, verify all output files created at correct paths, verify summary output, verify monolith mode produces no cross-service file

**Checkpoint**: Full project generation works end-to-end. Run `pytest tests/integration/test_generate_tasks_cmd.py` — all must pass.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Pipeline integration, template, snapshots, linting

- [ ] T044 Write tests for enhanced TasksPhase in tests/unit/test_phases/test_tasks_phase.py — verify _build_context() creates TaskGenerator and calls generate_for_service(), verify run() backs up existing tasks.md, verify backward compatibility with BasePhase protocol
- [ ] T045 Enhance TasksPhase to use TaskGenerator in src/specforge/core/phases/tasks_phase.py — replace basic template delegation with TaskGenerator orchestration per plan §D8, backup logic in run() override, convert TaskFile to template context dict
- [ ] T046 [P] Update tasks.md.j2 template in src/specforge/templates/base/features/tasks.md.j2 — restructure for rich format: header with service/architecture/date, cross-service dependencies section with XDEP refs, phase-grouped tasks with effort/depends/files/commit/prompt-rules annotations, summary footer with total tasks/effort breakdown/parallelization stats per plan §D9
- [ ] T047 [P] Write snapshot tests for template rendering in tests/snapshots/test_tasks_template_rendering.py — snapshot for microservice output (ledger-service with deps), snapshot for monolith output (auth module), snapshot for cross-service-infra output, snapshot for empty-deps service (identity-service)
- [ ] T048 Run ruff linting across all new files: `ruff check src/specforge/core/task_models.py src/specforge/core/task_generator.py src/specforge/core/dependency_resolver.py src/specforge/core/build_sequence.py src/specforge/core/cross_service_tasks.py src/specforge/core/effort_estimator.py src/specforge/core/governance_reader.py` — fix any violations
- [ ] T049 Run full test suite `pytest tests/ -v --tb=short` and verify all tests pass including pre-existing tests from Features 001–007
- [ ] T050 Run pytest coverage check `pytest --cov=specforge.core --cov-report=term-missing` — verify 100% coverage on new modules (task_models, task_generator, dependency_resolver, build_sequence, cross_service_tasks, effort_estimator, governance_reader)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 config constants) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T006 task_models, T007 build_sequence, T008 effort_estimator)
- **US2 (Phase 4)**: Depends on US1 (T019 TaskGenerator) — needs generate_for_service() to work first
- **US3 (Phase 5)**: Depends on US1 (T019 TaskGenerator) — can run in parallel with US2
- **US4 (Phase 6)**: Depends on US1 (T017 DependencyResolver) — extends existing resolver with mark_parallel()
- **US5 (Phase 7)**: Depends on US1 + US2 + US3 (all generation modes) — orchestrates them
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories — **MVP**
- **US2 (P1)**: Depends on US1 (needs TaskGenerator) — can start once T019 passes tests
- **US3 (P2)**: Depends on US1 (needs TaskGenerator) — **can run in parallel with US2**
- **US4 (P2)**: Depends on US1 (needs DependencyResolver) — **can run in parallel with US2 and US3**
- **US5 (P3)**: Depends on US1 + US2 + US3 — must wait for all generation modes

### Critical Path

```
T001 → T006/T007/T008 → T017 (DependencyResolver) → T019 (TaskGenerator) → T025 (CrossService) → T042 (FullProject)
                                                   ↘ T031 (Monolith)     ↗
                                                   ↘ T037 (Parallel)     ↗
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Models before services before orchestrators
3. Unit tests before integration tests
4. Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T003, T004, T005 can run in parallel (different test files)

**Phase 3 (US1)**:
- T009, T010, T011, T012 can run in parallel (different test concerns in same file, or split)

**Phase 4+5 (US2+US3) after US1 complete**:
- T021–T024 (US2 tests) can run in parallel with T027–T030 (US3 tests) — different stories, different files

**Phase 6 (US4) after US1 complete**:
- T034, T035 can run in parallel with US2/US3 implementation — extends different module

---

## Parallel Example: User Story 1

```bash
# Launch all DependencyResolver tests in parallel:
T009: "Tests for build_graph()" in tests/unit/test_dependency_resolver.py
T010: "Tests for topological_sort()" in tests/unit/test_dependency_resolver.py
T011: "Tests for cycle detection" in tests/unit/test_dependency_resolver.py

# Launch all 3 service variant tests in parallel:
T013: "identity-service (0 deps)" in tests/unit/test_task_generator.py
T014: "ledger-service (1 dep)" in tests/unit/test_task_generator.py
T015: "analytics-service (3 deps)" in tests/unit/test_task_generator.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T008) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T009–T020)
4. **STOP and VALIDATE**: Generate tasks for ledger-service, verify 14-step ordering
5. Demo: Show ordered tasks.md with effort sizes and dependency chain

### Incremental Delivery

1. Setup + Foundational → Data models and build sequences work
2. US1 → Single microservice task generation works → **Deploy/Demo (MVP!)**
3. US2 → Cross-service deduplication works → Deploy/Demo
4. US3 → Monolith mode works → Deploy/Demo (all architectures covered)
5. US4 → Parallelization markers accurate → Deploy/Demo
6. US5 → Full project generation → Deploy/Demo (complete feature)
7. Polish → Pipeline integration, templates, snapshots

### Test Matrix (User-Requested)

| Service | Dependencies | Events | Expected Steps | Key Verification |
|---------|-------------|--------|----------------|-----------------|
| identity-service | 0 deps | 0 events | 11 (omit comm clients, events, contract tests) | No step 6, 8, 10 |
| ledger-service | 1 dep (identity, gRPC) | 1 event (TransactionCreated producer) | 13 (omit events if no consumer) | Step 6 has identity-service gRPC client, XDEP to X-T001 |
| analytics-service | 3 deps | 2 events (consumer+producer) | 14 (all steps) | 3 comm clients, effort bump M→L, 3 contract tests, 2 event handlers, XDEP to X-T003 |
| Full PersonalFinance | 3 services | mixed | 3 service files + 1 cross-service-infra | Verify X-T tasks appear once, not per-service |
| auth (monolith) | N/A | N/A | 7 | No Docker, comm clients, gateway; shared DbContext |
| bidirectional events | 2 services | A→B, B→A | 2 service files + cross-service | Both producer+consumer handlers, no false cycle error |

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD enforced: write tests first, verify they fail, then implement
- Commit after each task: `feat(task-gen):`, `test(task-gen):`, `chore(task-gen):`
- DependencyResolver + BuildSequence = critical path — prioritize these
- PersonalFinance manifest is the canonical test fixture for all architectures
