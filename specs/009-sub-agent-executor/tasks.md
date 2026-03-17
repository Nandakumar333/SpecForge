# Tasks: Sub-Agent Execution Engine

**Input**: Design documents from `/specs/009-sub-agent-executor/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/, research.md, quickstart.md

**Tests**: TDD approach — tests written FIRST, must FAIL before implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/specforge/core/` and `src/specforge/cli/`
- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- **Snapshots**: `tests/snapshots/`
- **Templates**: `src/specforge/templates/base/prompts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, config constants, and frozen data model

- [ ] T001 Add Feature 009 config constants to src/specforge/core/config.py: EXECUTION_STATE_FILENAME, EXECUTION_LOCK_FILENAME, EXECUTION_LOCK_STALE_MINUTES, MAX_FIX_ATTEMPTS, CONTEXT_TOKEN_BUDGET, CHARS_PER_TOKEN_ESTIMATE, AGENT_RETRY_DELAYS, HEALTH_CHECK_TIMEOUT, HEALTH_CHECK_ENDPOINT, DOCKER_COMPOSE_TEST_PROFILE, IMPLEMENTATION_MODES, CONTEXT_PRIORITY
- [ ] T002 Create implementation prompt Jinja2 template in src/specforge/templates/base/prompts/implement-task.md.j2 with sections: Task Description, File Targets, Quality Standards, Service Context, Data Model, Dependency Contracts, Prior Tasks, Constraints

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Frozen dataclasses and execution state persistence — ALL subsequent phases depend on these

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T003 [P] Write unit tests for 8 frozen dataclasses and the ExecutionMode type alias in tests/unit/test_executor_models.py: test frozen immutability, default values, field types for ServiceLock, TaskExecution, QualityCheckResult, AutoFixAttempt, ExecutionState, VerificationState, ExecutionContext, ImplementPrompt, plus ExecutionMode Literal validation
- [ ] T004 [P] Write unit tests for execution state functions in tests/unit/test_execution_state.py: test create_initial_state, mark_task_in_progress, mark_task_completed, mark_task_failed, get_next_pending_task, validate_against_tasks (orphan removal + new task insertion), save_state (atomic write to tmp + os.replace), load_state (missing file returns Ok(None), corrupt file returns Err), detect_committed_task (finds commit SHA in git log, returns None when not found)

### Implementation for Foundational

- [ ] T005 [P] Create 8 frozen dataclasses and 1 type alias in src/specforge/core/executor_models.py: ExecutionMode Literal["prompt-display", "agent-call"], ServiceLock, TaskExecution (status includes "skipped"), QualityCheckResult, AutoFixAttempt, ExecutionState, VerificationState, ExecutionContext, ImplementPrompt — all with strict type hints and frozen=True
- [ ] T006 Implement execution state persistence functions in src/specforge/core/execution_state.py: create_initial_state, mark_task_in_progress, mark_task_completed, mark_task_failed, get_next_pending_task, validate_against_tasks, save_state (atomic: temp file + os.fsync + os.replace), load_state, detect_committed_task (checks git log for task's conventional commit message, returns SHA or None) — following pipeline_state.py patterns, all pure functions returning Result[T, str]

**Checkpoint**: Data model frozen, state persistence tested, all Phase 2 tests pass ✅

---

## Phase 3: User Story 3 — Context Isolation (Priority: P1) 🎯 CRITICAL

**Goal**: ContextBuilder assembles per-task context with strict isolation enforcement — sub-agent sees ONLY its service's artifacts + dependent contracts, never other services' code

**Independent Test**: Run ContextBuilder.build() for ledger-service (depends on identity-service), verify context includes identity-service contracts but zero files from identity-service implementation directories

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007 [P] [US3] Write unit tests for ContractResolver in tests/unit/test_contract_resolver.py: test resolve with 1 ServiceDependency loads contracts/ files, resolve with missing contracts/ warns but returns Ok, resolve with empty dependencies tuple returns empty dict, resolve with multiple dependencies merges all contracts, resolve NEVER accesses non-dependent service directories
- [ ] T008 [P] [US3] Write unit tests for ContextBuilder in tests/unit/test_context_builder.py: test build loads constitution.md (missing = warning not error), build loads all 5 service spec artifacts (spec.md, plan.md, data-model.md, edge-cases.md, tasks.md), build loads from multiple feature dirs for multi-feature services, build calls PromptContextBuilder.build() with task_domain hint, build includes dependency contracts from ContractResolver using ServiceContext.dependencies, build EXCLUDES files outside the allowlist (assert no paths from other services' src/), build adds architecture-specific prompts for microservice mode only, build omits architecture-specific prompts for monolith mode, token estimation warns when > CONTEXT_TOKEN_BUDGET with Rich warning listing truncated sections, token truncation removes lowest-priority sections first (edge-cases → architecture → contracts → data-model → plan → governance → spec, never constitution or current task), build is called per-task (current_task field varies)

### Implementation for User Story 3

- [ ] T009 [US3] Implement ContractResolver in src/specforge/core/contract_resolver.py: resolve(dependencies: tuple[ServiceDependency, ...]) takes pre-resolved dependencies from ServiceContext (not raw manifest), loads .specforge/features/<dep.target_slug>/contracts/* files, returns dict[str, str] mapping dep-slug to concatenated contract content, warns on missing contracts (non-blocking), returns Result[dict, str]. Only loads contracts for declared dependencies — never all services
- [ ] T010 [US3] Implement ContextBuilder in src/specforge/core/context_builder.py: __init__(project_root, prompt_loader, contract_resolver), build(service_ctx, task) is called PER TASK (not once before the loop) — loads constitution → governance prompts → service artifacts (from all feature dirs if multi-feature service) → dependency contracts via contract_resolver.resolve(service_ctx.dependencies) → architecture prompts (microservice only) → current task, enforces allowlist (only reads from constitution.md, .specforge/prompts/, .specforge/features/<target-slug>/, .specforge/features/<dep-slug>/contracts/), estimates tokens (chars/4), truncates by CONTEXT_PRIORITY if over budget with Rich warning listing truncated sections, returns frozen ExecutionContext

**Checkpoint**: ContextBuilder tested with identity-service (no deps) and ledger-service (1 dep), isolation verified ✅

---

## Phase 4: User Story 1 — Single Service Implementation (Priority: P1) 🎯 MVP

**Goal**: `specforge implement ledger-service` executes tasks in dependency order with quality checks and commits — Mode A (prompt-display) first

**Independent Test**: Provide a service with 3-5 tasks, run implement, verify each task executes in order with quality checks and conventional commits

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Write unit tests for QualityChecker in tests/unit/test_quality_checker.py: test check runs build (no-op if unconfigured), ruff, pytest in sequence, check returns passed=True when all pass, check returns passed=False with correct failed_checks, detect_regression returns True when new test failures appear (B ⊄ A), detect_regression returns False when failures are subset (B ⊆ A)
- [ ] T012 [P] [US1] Write unit tests for TaskRunner Mode A in tests/unit/test_task_runner.py: test run in prompt-display mode renders prompt via Jinja2 template, run displays Rich Panel with task description and file hints, run waits for user confirmation (y/n/skip), user 'y' detects changed files via git status, user 'n' returns Err, user 'skip' returns Ok([])
- [ ] T013 [P] [US1] Write unit tests for SubAgentExecutor in tests/unit/test_sub_agent_executor.py: test execute validates spec artifacts exist (Err if missing), execute acquires ServiceLock (Err if locked), execute loads ExecutionState (fresh or resume), execute processes tasks in dependency order, execute calls QualityChecker after each task, execute commits on quality pass with conventional commit message format, execute saves state after each task, execute skips completed tasks on resume, execute handles zero-dependency service (identity-service pattern), execute handles one-dependency service (ledger-service pattern)
- [ ] T014 [P] [US1] Write snapshot tests for prompt rendering in tests/snapshots/test_implement_prompt_rendering.py: test implement-task.md.j2 renders with full context (all sections populated), renders with minimal context (no dependency contracts), renders for monolith (no architecture-specific sections)

### Implementation for User Story 1

- [ ] T015 [US1] Implement QualityChecker in src/specforge/core/quality_checker.py: __init__(project_root, service_slug), check(changed_files) runs build command (from manifest or no-op), ruff check on .py files, pytest on tests/<slug>/ — aggregates into QualityCheckResult, detect_regression(before, after) parses test names from output, returns True if new failures. For shared-infra context: also run `docker-compose config` on generated docker-compose.yml (no-op if docker-compose not installed)
- [ ] T016 [US1] Implement TaskRunner Mode A in src/specforge/core/task_runner.py: __init__(project_root), run(prompt, mode) for prompt-display: render implement-task.md.j2 via TemplateRenderer, display with Rich Panel, wait for Rich.Prompt confirmation (y/n/skip), detect changed files via git status, return Ok(changed_files) or Err
- [ ] T017 [US1] Implement SubAgentExecutor in src/specforge/core/sub_agent_executor.py: __init__(context_builder, task_runner, quality_checker, auto_fix_loop, docker_manager, project_root), execute(service_slug, mode, resume) follows D2 algorithm — load manifest → validate artifacts → check shared infra → acquire lock → load/create state → parse tasks → per-task loop (build context per task → generate prompt → execute → quality check → commit → save state) → release lock → return state. On resume, call detect_committed_task() to handle crash-window recovery before re-executing in-progress tasks
- [ ] T018 [US1] Implement implement CLI command in src/specforge/cli/implement_cmd.py: @click.command with target argument, --shared-infra, --resume, --mode, --max-fix-attempts options, mutual exclusion validation, wires up SubAgentExecutor with injected dependencies, handles exit codes (0 success, 1 halt, 2 invalid args, 3 missing prereqs, 4 lock conflict)
- [ ] T019 [US1] Register implement command in src/specforge/cli/main.py: import implement_cmd, add cli.add_command(implement)
- [ ] T020 [US1] Write integration test for Mode A with identity-service (no deps) in tests/integration/test_implement_cmd.py: scaffold a tmp project with manifest (1 service, no deps, microservice arch), write mock spec artifacts (spec.md, plan.md, data-model.md, edge-cases.md, tasks.md with 3 tasks), invoke `specforge implement identity-service` via CliRunner, simulate Mode A user confirmations, verify 3 commits created with conventional messages, verify execution state file tracks all 3 tasks as completed

**Checkpoint**: `specforge implement identity-service` works end-to-end in Mode A with quality checks and commits ✅

---

## Phase 5: User Story 2 — Auto-Fix Loop (Priority: P1)

**Goal**: Quality check failures trigger automatic retry with targeted fix prompts, regression detection reverts bad fixes, max 3 attempts before halt

**Independent Test**: Provide a task producing a test failure, verify auto-fix generates fix prompt, retries, and either succeeds or halts with diagnostic report after 3 attempts

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T021 [P] [US2] Write unit tests for AutoFixLoop in tests/unit/test_auto_fix_loop.py: test fix generates fix prompt from error + original task context + changed files, fix calls TaskRunner then QualityChecker per attempt, fix returns Ok on successful retry (quality checks pass), fix returns Err after max_attempts exhausted with diagnostic summary, fix detects regression (new failures) and reverts via git checkout on fix files only (preserves original task changes), fix counts reverted attempt as failed, fix passes updated error to next attempt when no regression

### Implementation for User Story 2

- [ ] T022 [US2] Implement AutoFixLoop in src/specforge/core/auto_fix_loop.py: __init__(task_runner, quality_checker, max_attempts=3), fix(original_task, error, changed_files, mode) loops up to max_attempts — generates fix prompt from error output + original context + changed files, executes via TaskRunner, runs QualityChecker, if pass returns Ok, if regression reverts fix files via git checkout and counts failed, if fail continues with updated error, after exhaustion returns Err with full diagnostic (original error + each attempt's error + files involved)
- [ ] T023 [US2] Wire AutoFixLoop into SubAgentExecutor execution loop in src/specforge/core/sub_agent_executor.py: after quality check failure in step 8f, call auto_fix_loop.fix(), if fix succeeds commit combined changes (original + fix), if exhausted mark task failed + halt + save state
- [ ] T024 [US2] Write integration test for auto-fix with ledger-service in tests/integration/test_implement_cmd.py: scaffold tmp project with ledger-service (depends on identity-service), mock a task that fails quality checks on first attempt, verify auto-fix loop retries, verify combined commit on fix success, verify halt with diagnostic output after 3 exhausted attempts

**Checkpoint**: Auto-fix loop handles build/lint/test failures with regression detection and graceful halt ✅

---

## Phase 6: User Story 4 — Shared Infrastructure (Priority: P2)

**Goal**: `specforge implement --shared-infra` builds cross-service infrastructure before any service, warns when infra missing for microservice services

**Independent Test**: Run --shared-infra for a microservice project, verify shared contracts, docker-compose, and gateway skeleton are created and pass quality checks

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T025 [P] [US4] Write unit tests for SharedInfraExecutor in tests/unit/test_shared_infra_executor.py: test execute validates architecture is microservice or modular-monolith (Err for monolithic), execute locates cross-service-infra/tasks.md (Err if missing), execute builds project-wide context (all services' specs + full manifest), execute processes infra tasks using same loop pattern as SubAgentExecutor, execute marks shared_infra_complete in state, execute commits on current working branch (no separate branch)

### Implementation for User Story 4

- [ ] T026 [US4] Implement SharedInfraExecutor in src/specforge/core/shared_infra_executor.py: __init__(context_builder, task_runner, quality_checker, auto_fix_loop, project_root), execute(mode) loads manifest → validates architecture → locates cross-service-infra/tasks.md → builds project-wide context → processes tasks via same execution loop → marks shared_infra_complete → returns state
- [ ] T027 [US4] Add shared-infra prerequisite check to SubAgentExecutor in src/specforge/core/sub_agent_executor.py: in execute() step 3, if architecture is microservice or modular-monolith, check if shared_infra_complete is True — if not, warn and ask user whether to proceed or run --shared-infra first
- [ ] T028 [US4] Wire --shared-infra flag in implement CLI command in src/specforge/cli/implement_cmd.py: if --shared-infra, instantiate SharedInfraExecutor instead of SubAgentExecutor, validate mutual exclusion with target argument, report "not applicable" for monolithic
- [ ] T029 [US4] Write integration test for --shared-infra in tests/integration/test_implement_microservice.py: scaffold tmp microservice project with 3 services and cross-service-infra/tasks.md, run `specforge implement --shared-infra`, verify infra tasks processed, verify shared_infra_complete=true in state, then run `specforge implement identity-service` and verify no shared-infra warning

**Checkpoint**: Shared infra builds before services, monolith correctly rejected, prerequisite check works ✅

---

## Phase 7: User Story 5 — Resume Capability (Priority: P2)

**Goal**: `specforge implement --resume ledger-service` picks up from last committed task, validates state against current tasks.md

**Independent Test**: Run 5 tasks, interrupt after 3, resume with --resume, verify starts at task 4

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [US5] Write unit tests for resume logic in tests/unit/test_sub_agent_executor.py (extend existing): test resume=True loads existing state and starts from first pending task, resume validates state against tasks.md (removes orphaned IDs, adds new), resume restarts in-progress tasks from scratch (attempt 1), resume with all-complete state reports "already complete", no-resume with existing state warns and offers choice

### Implementation for User Story 5

- [ ] T031 [US5] Enhance SubAgentExecutor.execute() resume path in src/specforge/core/sub_agent_executor.py: if resume=True, load state via load_state, call validate_against_tasks to sync with current tasks.md, reset any in-progress tasks to pending (restart from scratch), skip completed tasks, start from first pending; if state exists and resume=False, warn with Rich prompt offering resume or fresh start
- [ ] T032 [US5] Write integration test for resume in tests/integration/test_implement_resume.py: scaffold tmp project, run implement for 5 tasks with interruption after task 3 (mock exit), verify state file shows 3 completed + 2 pending, run `specforge implement --resume ledger-service`, verify tasks 4-5 execute, verify final state shows 5 completed

**Checkpoint**: Resume picks up from last committed task, validates against modified tasks.md ✅

---

## Phase 8: User Story 6 — Microservice Verification (Priority: P3)

**Goal**: After all tasks, build Docker image, run health check, run Pact contract tests, register in docker-compose

**Independent Test**: Complete all tasks for ledger-service, verify Docker image builds, health check passes, contract tests run against stubs

### Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T033 [P] [US6] Write unit tests for DockerManager in tests/unit/test_docker_manager.py: test build_image locates Dockerfile and runs docker build, health_check runs container and polls /health endpoint, run_contract_tests runs pytest on tests/<slug>/contract/, compose_up_test_profile runs docker-compose --profile test up -d, compose_down_test_profile runs docker-compose --profile test down, register_in_compose reads/writes docker-compose.yml atomically, all methods return Result[T, str], monolith mode: DockerManager is None (never instantiated)

### Implementation for User Story 6

- [ ] T034 [US6] Implement DockerManager in src/specforge/core/docker_manager.py: __init__(project_root, service_slug), build_image() locates Dockerfile at src/<slug>/Dockerfile → runs docker build -t <slug>:latest, health_check(timeout=30) runs container → polls /health → stops/removes, run_contract_tests() runs pytest tests/<slug>/contract/, compose_up_test_profile() runs docker-compose --profile test up -d, compose_down_test_profile() runs docker-compose --profile test down, register_in_compose(path) reads + updates + atomic writes docker-compose.yml
- [ ] T035 [US6] Wire verification into SubAgentExecutor post-task loop in src/specforge/core/sub_agent_executor.py: after all tasks complete in step 9, if architecture=microservice and docker_manager is not None, run build_image → health_check → run_contract_tests → register_in_compose, apply auto_fix_loop on verification failures, record results in VerificationState, skip verification entirely for monolith/modular-monolith
- [ ] T036 [US6] Wire docker-compose lifecycle for integration test tasks in src/specforge/core/sub_agent_executor.py: before executing integration test tasks (detected by task layer or category), call docker_manager.compose_up_test_profile(), after quality checks call compose_down_test_profile(), handle compose failures as pre-condition errors (halt, not auto-fix)
- [ ] T037 [US6] Write integration test for microservice verification in tests/integration/test_implement_microservice.py (extend): scaffold tmp microservice project with ledger-service, mock Docker commands (subprocess), run full implementation, verify VerificationState in execution state shows container_built, health_check_passed, contract_tests_passed, compose_registered

**Checkpoint**: Microservice services verified with Docker, health checks, Pact contracts; monolith skips verification ✅

---

## Phase 9: User Story 1 (Mode B Extension) — Agent-Call Mode (Priority: P1 extension)

**Goal**: Mode B sends prompts directly to configured agent, retries on unreachability, falls back to Mode A

**Independent Test**: Run implement in agent-call mode, verify agent subprocess invocation, verify fallback to Mode A after 3 agent failures

### Tests for User Story 1 (Mode B)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T038 [P] [US1] Write unit tests for TaskRunner Mode B in tests/unit/test_task_runner.py (extend): test run in agent-call mode detects agent via agent_detector, run sends prompt to agent subprocess, run captures stdout/stderr, run retries 3 times on agent unreachable with exponential backoff (1s, 2s, 4s), run falls back to Mode A after 3 failures with warning, run detects changed files via git status after agent completes

### Implementation for User Story 1 (Mode B)

- [ ] T039 [US1] Implement TaskRunner Mode B in src/specforge/core/task_runner.py (extend run method): detect agent via existing agent_detector.py, send rendered prompt to agent subprocess (stdin pipe), capture stdout/stderr, retry with AGENT_RETRY_DELAYS on failure, fall back to Mode A after 3 failures (log warning, switch to prompt-display for current task), detect changed files via git status

**Checkpoint**: Mode B agent-call works with fallback to Mode A ✅

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Monolith integration test, completion summary, documentation

- [ ] T040 Write integration test for monolith mode in tests/integration/test_implement_monolith.py: scaffold tmp monolith project (architecture=monolithic, 1 module), run `specforge implement auth-module`, verify no Docker verification runs, no shared-infra check, no architecture-specific prompts in context, standard build/lint/test quality checks only, verify contracts are empty (monolith modules have no communication entries), verify DockerManager is None (never instantiated)
- [ ] T041 Add Rich completion summary to SubAgentExecutor in src/specforge/core/sub_agent_executor.py: after execution completes (or halts), display summary table with tasks completed/failed/skipped counts, auto-fix attempt stats, commits created, verification results (microservice only)
- [ ] T042 [P] Add Rich progress display to execution loop in src/specforge/core/sub_agent_executor.py: show progress bar or status panel during task processing — current task name, N of M completed, elapsed time
- [ ] T043 Run full test suite and verify all tests pass: `pytest tests/ -x --tb=short`
- [ ] T044 Run ruff linter across all new modules: `ruff check src/specforge/core/executor_models.py src/specforge/core/execution_state.py src/specforge/core/context_builder.py src/specforge/core/task_runner.py src/specforge/core/quality_checker.py src/specforge/core/auto_fix_loop.py src/specforge/core/sub_agent_executor.py src/specforge/core/shared_infra_executor.py src/specforge/core/contract_resolver.py src/specforge/core/docker_manager.py src/specforge/cli/implement_cmd.py`
- [ ] T045 Run quickstart.md validation — verify documented commands match actual CLI behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US3 Context Isolation (Phase 3)**: Depends on Foundational — BLOCKS US1 (SubAgentExecutor needs ContextBuilder)
- **US1 Single Service (Phase 4)**: Depends on US3 (ContextBuilder), Foundational (models + state)
- **US2 Auto-Fix (Phase 5)**: Depends on US1 (QualityChecker, TaskRunner, SubAgentExecutor)
- **US4 Shared Infra (Phase 6)**: Depends on US1 (execution loop pattern), US3 (ContextBuilder)
- **US5 Resume (Phase 7)**: Depends on US1 (SubAgentExecutor), Foundational (ExecutionState)
- **US6 Docker Verification (Phase 8)**: Depends on US1 (SubAgentExecutor), US2 (AutoFixLoop)
- **Mode B Extension (Phase 9)**: Depends on US1 (TaskRunner Mode A established)
- **Polish (Phase 10)**: Depends on all above

### User Story Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Foundational)
        └── Phase 3 (US3: Context Isolation)
              └── Phase 4 (US1: Single Service + Mode A) 🎯 MVP
                    ├── Phase 5 (US2: Auto-Fix)
                    │     └── Phase 8 (US6: Docker Verification)
                    ├── Phase 6 (US4: Shared Infra)
                    ├── Phase 7 (US5: Resume)
                    └── Phase 9 (US1 Mode B Extension)
                          └── Phase 10 (Polish)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/contracts before services
- Services before CLI wiring
- Unit tests before integration tests
- Mode A before Mode B

### Parallel Opportunities

- T003, T004 (Phase 2 tests) can run in parallel
- T005, T006 (Phase 2 implementation) — T005 parallel, T006 depends on T005
- T007, T008 (Phase 3 tests) can run in parallel
- T011, T012, T013, T014 (Phase 4 tests) can run in parallel
- T021 (Phase 5 tests) independent
- T025 (Phase 6 tests) independent
- T030 (Phase 7 tests) independent
- T033 (Phase 8 tests) independent
- T038 (Phase 9 tests) independent

---

## Parallel Example: Phase 4 (User Story 1)

```bash
# Launch all US1 tests together (TDD — write first, must fail):
Task T011: "Unit tests for QualityChecker"
Task T012: "Unit tests for TaskRunner Mode A"
Task T013: "Unit tests for SubAgentExecutor"
Task T014: "Snapshot tests for prompt rendering"

# Then implement sequentially (dependency chain):
Task T015: QualityChecker (no deps within phase)
Task T016: TaskRunner Mode A (no deps within phase)
Task T017: SubAgentExecutor (depends on T015, T016 — wires them together)
Task T018: CLI command (depends on T017)
Task T019: Register command (depends on T018)
Task T020: Integration test (depends on T017, T018, T019)
```

---

## Implementation Strategy

### MVP First (Phase 1 → Phase 4)

1. Complete Phase 1: Config + template
2. Complete Phase 2: Frozen models + state persistence
3. Complete Phase 3: ContextBuilder + ContractResolver (isolation proven)
4. Complete Phase 4: SubAgentExecutor + QualityChecker + TaskRunner Mode A + CLI
5. **STOP and VALIDATE**: Test with identity-service (no deps) end-to-end
6. Deploy/demo if ready — single service implementation works

### Incremental Delivery

1. Setup + Foundational + US3 + US1 → MVP: `specforge implement identity-service` ✅
2. Add US2 (Auto-Fix) → Error recovery works ✅
3. Add US4 (Shared Infra) → `specforge implement --shared-infra` ✅
4. Add US5 (Resume) → `specforge implement --resume ledger-service` ✅
5. Add US6 (Docker) → Microservice verification ✅
6. Add Mode B → Agent-call mode ✅
7. Polish → Monolith tests, summary display, progress bars

### Test Matrix

| Test Scenario | Service | Architecture | Dependencies | Docker |
|---------------|---------|-------------|-------------|--------|
| identity-service (no deps) | identity-service | microservice | none | Phase 8 |
| ledger-service (1 dep) | ledger-service | microservice | identity-service | Phase 8 |
| auth-module (monolith) | auth-module | monolithic | none | N/A |
| shared-infra | cross-service-infra | microservice | all services | N/A |
| resume | ledger-service | microservice | identity-service | N/A |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD enforced: every phase has test tasks before implementation tasks
- QualityChecker and AutoFixLoop are thin wrappers — Feature 010 replaces internals
- DockerManager is None for monolith (never instantiated, never called)
- Mode A is full priority — Mode B added in Phase 9 after Mode A is stable
- Context Isolation (US3) elevated to Phase 3 (before US1) because SubAgentExecutor depends on ContextBuilder
