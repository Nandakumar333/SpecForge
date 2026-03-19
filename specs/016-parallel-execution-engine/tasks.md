# Tasks: Parallel Execution Engine

**Input**: Design documents from `/specs/016-parallel-execution-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: TDD — write tests first, ensure they fail, then implement.

**Organization**: Tasks grouped by user story with TDD ordering. [P] marks parallelizable tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/specforge/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Constants, config schema, and frozen dataclasses for parallel state

- [ ] T001 Add PARALLEL_DEFAULT_MAX_WORKERS, PARALLEL_STATE_FILENAME, and PARALLEL_LOCK_STALE_THRESHOLD constants in src/specforge/core/config.py
- [ ] T002 [P] Write tests for ParallelExecutionState, ServiceRunStatus, WaveStatus, ProgressEvent frozen dataclasses in tests/unit/test_parallel_state.py — cover creation, state transitions, validation rules, JSON round-trip
- [ ] T003 [P] Implement ParallelExecutionState, ServiceRunStatus, WaveStatus, ProgressEvent frozen dataclasses in src/specforge/core/parallel_state.py — all fields from data-model.md
- [ ] T004 Implement save_state and load_state functions for ParallelExecutionState in src/specforge/core/parallel_state.py — atomic write via tempfile + os.replace, JSON serialization
- [ ] T005 Add state transition functions (mark_service_in_progress, mark_service_completed, mark_service_failed, mark_service_blocked, mark_service_cancelled) to src/specforge/core/parallel_state.py
- [ ] T006 Add create_initial_state and detect_resume_point functions to src/specforge/core/parallel_state.py — filter completed services for resume

**Checkpoint**: State model complete — all dataclasses, persistence, and transitions tested

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: TopologicalParallelExecutor wave computation and ProgressTracker — these block all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests

- [ ] T007 [P] Write tests for wave computation from dependency graph in tests/unit/test_topological_parallel_executor.py — cover: all-independent (single wave), linear chain (N waves), diamond deps, cycle detection error, empty graph
- [ ] T008 [P] Write tests for ProgressTracker thread safety in tests/unit/test_parallel_progress_tracker.py — cover: on_phase_complete/on_service_complete/on_service_failed/on_service_blocked/on_service_cancelled callbacks, get_summary aggregation, concurrent calls from multiple threads

### Implementation

- [ ] T009 Implement compute_waves function in src/specforge/core/topological_parallel_executor.py — takes manifest dict, calls existing build_graph + compute_phases from dependency_graph.py, returns tuple[WaveStatus, ...] with service assignments
- [ ] T010 Implement architecture_to_waves function in src/specforge/core/topological_parallel_executor.py — microservice: use compute_waves; monolith: single wave with all modules; modular-monolith: use compute_waves if communication[] entries exist, otherwise single wave
- [ ] T011 Implement ProgressTracker class in src/specforge/core/parallel_progress_tracker.py — constructor takes Console + total_services + state_path; all callback methods use threading.Lock; on_phase_complete prints inline progress; on_service_complete prints timing
- [ ] T012 Implement get_summary method on ProgressTracker in src/specforge/core/parallel_progress_tracker.py — aggregates internal counters into ParallelExecutionState
- [ ] T013 Implement atomic dashboard state write in ProgressTracker._persist_state in src/specforge/core/parallel_progress_tracker.py — writes parallel-state.json after each event if state_path is set

**Checkpoint**: Wave computation + progress tracking ready — user story implementation can begin

---

## Phase 3: User Story 1 — Parallel Spec Generation via Decompose (Priority: P1) 🎯 MVP

**Goal**: `specforge decompose "App" --auto --parallel` discovers services via AI, then runs 7-phase spec pipeline concurrently across all services

**Independent Test**: Run decompose with --auto --parallel on a fresh directory; verify all service dirs contain 7 complete artifacts

### Tests

- [ ] T014 [P] [US1] Write tests for ParallelPipelineRunner in tests/unit/test_parallel_pipeline_runner.py — cover: parallel execution of N services, error isolation (one fails others continue), fail-fast cancellation, resume skips completed services, max_workers cap, mock rate-limit error to verify backoff doesn't deadlock ThreadPoolExecutor
- [ ] T015 [P] [US1] Write tests for --auto flag suppressing interactive prompts in tests/unit/test_parallel_pipeline_runner.py — cover: architecture selection bypassed, feature confirmation bypassed, over-engineering warning suppressed

### Implementation

- [ ] T016 [US1] Implement ParallelPipelineRunner class in src/specforge/core/parallel_pipeline_runner.py — constructor takes orchestrator_factory, tracker, max_workers, fail_fast; .run() submits service pipelines to ThreadPoolExecutor; if --parallel and provider unavailable, return Err (no template fallback)
- [ ] T017 [US1] Implement worker function _run_single_service in src/specforge/core/parallel_pipeline_runner.py — calls orchestrator_factory() per invocation to create fresh PipelineOrchestrator with isolated ProviderFactory.create() instance, calls orchestrator.run(slug, project_root, force), reports to tracker
- [ ] T018 [US1] Implement fail-fast logic in ParallelPipelineRunner._handle_futures in src/specforge/core/parallel_pipeline_runner.py — on first failure with fail_fast=True, set shutdown_event and call executor.shutdown(cancel_futures=True)
- [ ] T019 [US1] Implement resume logic in ParallelPipelineRunner.run in src/specforge/core/parallel_pipeline_runner.py — load parallel-state.json, filter out completed services, run only incomplete ones
- [ ] T020 [US1] Implement SIGINT handler in src/specforge/core/parallel_pipeline_runner.py — register signal.signal(SIGINT, handler) that sets shutdown_event; workers check event between phases; second SIGINT forces exit
- [ ] T021 [US1] Implement completion summary in ParallelPipelineRunner._build_summary in src/specforge/core/parallel_pipeline_runner.py — aggregate per-service status, timing, phase counts, errors into Rich table output
- [ ] T022 [US1] Add --auto flag to decompose command in src/specforge/cli/decompose_cmd.py — is_flag=True, when set: skip architecture prompt (use LLM result), skip feature confirmation, imply --no-warn
- [ ] T023 [US1] Add --parallel flag to decompose command in src/specforge/cli/decompose_cmd.py — is_flag=True, when set: after decomposition completes, invoke ParallelPipelineRunner.run with all service slugs from manifest
- [ ] T024 [US1] Add --max-parallel and --fail-fast flags to decompose command in src/specforge/cli/decompose_cmd.py — max_parallel is click.INT with default None (falls back to config), fail_fast is is_flag=True
- [ ] T025 [US1] Wire parallel execution into decompose flow in src/specforge/cli/decompose_cmd.py — after manifest write, if --parallel: create ProgressTracker + ParallelPipelineRunner, resolve max_workers from --max-parallel or config.json, run and print summary
- [ ] T026 [US1] Add parallel.max_workers config reading to ProviderFactory or new helper in src/specforge/core/config.py — read .specforge/config.json "parallel" key with default {"max_workers": 4}

**Checkpoint**: `specforge decompose "App" --auto --parallel` fully functional with parallel spec generation, error isolation, resume, and fail-fast

---

## Phase 4: User Story 2 — Parallel Implementation with Dependency Ordering (Priority: P2)

**Goal**: `specforge implement --all --parallel` runs services in topologically sorted dependency waves with concurrent execution per wave

**Independent Test**: Create manifest with known deps, run implement --all --parallel, verify wave ordering

### Tests

- [ ] T027 [P] [US2] Write tests for TopologicalParallelExecutor.execute in tests/unit/test_topological_parallel_executor.py — cover: multi-wave execution, blocked dependents on failure, fail-fast across waves, monolith single-wave, resume from partial wave

### Implementation

- [ ] T028 [US2] Implement TopologicalParallelExecutor class in src/specforge/core/topological_parallel_executor.py — constructor takes runner, tracker; .execute() calls architecture_to_waves, iterates waves sequentially, calls runner.run(wave.services) per wave
- [ ] T029 [US2] Implement wave-to-wave blocked service detection in TopologicalParallelExecutor._check_blocked in src/specforge/core/topological_parallel_executor.py — after each wave, identify services in next wave whose dependencies failed, mark as blocked via tracker
- [ ] T030 [US2] Implement wave status aggregation in TopologicalParallelExecutor._update_wave_status in src/specforge/core/topological_parallel_executor.py — compute completed/partial/skipped from per-service results
- [ ] T031 [US2] Add --parallel, --max-parallel, --fail-fast flags to implement command in src/specforge/cli/specify_cmd.py — parallel requires --all, max_parallel/fail_fast require --parallel
- [ ] T032 [US2] Wire TopologicalParallelExecutor into implement --all flow in src/specforge/cli/specify_cmd.py — when --parallel: create tracker + runner + executor, call executor.execute(manifest, project_root, max_workers, fail_fast)

**Checkpoint**: `specforge implement --all --parallel` runs with correct wave ordering, blocked detection, and fail-fast

---

## Phase 5: User Story 3 — Live Dashboard During Parallel Execution (Priority: P3)

**Goal**: `specforge status --watch` shows live per-service progress during parallel operations

**Independent Test**: Run parallel operation + status --watch in separate terminal, verify updates appear within refresh interval

### Implementation

- [ ] T033 [US3] Ensure ProgressTracker._persist_state writes dashboard-compatible JSON to .specforge/parallel-state.json in src/specforge/core/parallel_progress_tracker.py — format matches StatusSnapshot expectations from Feature 012
- [ ] T034 [US3] Update collect_project_status in src/specforge/cli/status_cmd.py or src/specforge/cli/dashboard_renderer.py — read .specforge/parallel-state.json if it exists, merge per-service parallel progress into StatusSnapshot
- [ ] T035 [US3] Add parallel execution section to dashboard render in src/specforge/cli/dashboard_renderer.py — show per-service phase progress (e.g., "identity-service: research [3/7]"), wave info for implement mode, failed/blocked indicators

**Checkpoint**: Dashboard shows live parallel progress via --watch

---

## Phase 6: User Story 4 — Monolith Module Parallelism (Priority: P4)

**Goal**: --parallel works for monolith/modular-monolith without generating microservice artifacts

**Independent Test**: Run decompose with --arch monolithic --auto --parallel, verify no Docker/contract artifacts generated

### Implementation

- [ ] T036 [US4] Add monolith-specific test cases to tests/unit/test_topological_parallel_executor.py — verify monolith returns single wave, modular-monolith with communication[] entries uses dependency ordering
- [ ] T037 [US4] Verify architecture_to_waves in src/specforge/core/topological_parallel_executor.py correctly handles monolith (all modules in wave 0) and modular-monolith (boundary-aware if communication[] present)

**Checkpoint**: All architecture types work correctly with --parallel

---

## Phase 7: Integration Tests

**Purpose**: End-to-end CLI validation for microservice and monolith modes

- [ ] T038 [P] Write integration test for parallel decompose with microservice architecture in tests/integration/test_parallel_decompose_microservice.py — use CliRunner + tmp_path, mock LLM provider, verify: manifest created, all service dirs have 7 artifacts, parallel-state.json written, exit code 0, artifact content matches sequential baseline (same PipelineOrchestrator output), include case for --parallel without --auto (prompts then parallel pipeline)
- [ ] T039 [P] Write integration test for parallel implement with monolith architecture in tests/integration/test_parallel_implement_monolith.py — use CliRunner + tmp_path, pre-create manifest + spec artifacts, mock sub-agent executor, verify: single wave, no Docker artifacts, exit code 0
- [ ] T040 Write integration test for --fail-fast behavior in tests/integration/test_parallel_decompose_microservice.py — mock one service to fail, verify: other services cancelled, summary shows completed/cancelled/not-started, exit code 1
- [ ] T041 Write integration test for resume after interruption in tests/integration/test_parallel_decompose_microservice.py — pre-create parallel-state.json with 2 of 4 services completed, run decompose --auto --parallel, verify: only 2 services re-run

**Checkpoint**: Full integration coverage for both architecture modes

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, backward compatibility, and cleanup

- [ ] T042 Add backward-compatibility guard in src/specforge/cli/decompose_cmd.py — decompose without --parallel or --auto behaves identically to pre-016 (no functional change to existing flow); verify Feature 010 quality reports write to per-service dirs (no shared file contention in parallel mode)
- [ ] T043 Add config.json graceful default in src/specforge/core/config.py — if "parallel" key missing from config.json, use {"max_workers": 4} without error
- [ ] T044 Add --max-parallel input validation in src/specforge/cli/decompose_cmd.py and src/specforge/cli/specify_cmd.py — must be >= 1, non-integer raises Click error; --max-parallel and --fail-fast without --parallel are silently ignored
- [ ] T045 [P] Run ruff check + ruff format on all new files in src/specforge/core/ and tests/
- [ ] T046 Run full test suite (uv run pytest --cov=specforge) and verify no regressions in existing tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (state model)
- **US1 (Phase 3)**: Depends on Phase 2 (wave computation, progress tracker)
- **US2 (Phase 4)**: Depends on Phase 3 (ParallelPipelineRunner)
- **US3 (Phase 5)**: Depends on Phase 2 (ProgressTracker with persist)
- **US4 (Phase 6)**: Depends on Phase 2 (architecture_to_waves)
- **Integration (Phase 7)**: Depends on Phases 3-6
- **Polish (Phase 8)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational — no other story dependencies
- **US2 (P2)**: Depends on US1 (reuses ParallelPipelineRunner)
- **US3 (P3)**: Depends on Foundational only (ProgressTracker._persist_state)
- **US4 (P4)**: Depends on Foundational only (architecture_to_waves)

### Within Each Story (TDD Order)

1. Tests first → ensure they fail
2. Core logic (dataclasses, pure functions)
3. Orchestration (runner, executor)
4. CLI integration (flags, wiring)

### Parallel Opportunities

- T002 + T003 (state tests + implementation — different files)
- T007 + T008 (executor tests + tracker tests — different files)
- T014 + T015 (runner tests — same file but independent test classes)
- T027 can start after T009/T010 (only needs wave computation)
- T033-T035 (US3) can run parallel with T028-T032 (US2) after Phase 2
- T036-T037 (US4) can run parallel with T028-T032 (US2) after Phase 2
- T038 + T039 (integration tests — different files)

---

## Parallel Example: US1 + US3 + US4 After Foundational

```bash
# After Phase 2 completes, these can start in parallel:

# Stream 1: US1 (MVP)
Task: T014-T015 (tests) → T016-T021 (implementation) → T022-T026 (CLI)

# Stream 2: US3 (dashboard) — independent of US1
Task: T033-T035 (dashboard integration)

# Stream 3: US4 (monolith) — independent of US1
Task: T036-T037 (monolith verification)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T013)
3. Complete Phase 3: US1 (T014-T026)
4. **STOP and VALIDATE**: Test `specforge decompose "Test" --auto --parallel`
5. Commit and demo if ready

### Incremental Delivery

1. Setup + Foundational → State model + wave computation ready
2. Add US1 → Parallel decompose works → MVP!
3. Add US2 → Parallel implement works
4. Add US3 + US4 (parallel) → Dashboard + monolith support
5. Integration tests + polish → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD enforced: write tests (T002, T007, T008, T014, T015, T027) before implementation
- Each task targets ≤30 lines per function (constitution III)
- All new code uses Result[T, E] for errors, frozen dataclasses, constructor injection
- Commit after each task or logical group using `feat(016):` prefix
