# Tasks: Implementation Orchestrator

**Input**: Design documents from `/specs/011-implementation-orchestrator/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅
**TDD**: Tests written FIRST for every module — tests MUST fail before implementation.
**Test scenario**: 3-phase microservice: Phase 0 (identity-service + admin-service), Phase 1 (ledger-service + portfolio-service), Phase 2 (planning-service + analytics-service + notification-service). Intentional contract mismatch between ledger ↔ identity for violation detection. Within-phase execution is sequential (parallel deferred to future feature — avoids port/git/file contention).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)

---

## Phase 1: Constants & Models (Foundation — blocks everything)

**Purpose**: Define all frozen dataclasses and constants. Zero logic, zero external deps.

- [X] T001 [P] [US1] Add orchestration constants to `src/specforge/core/config.py`: `ORCHESTRATION_STATE_FILENAME = ".specforge/orchestration-state.json"`, `ORCHESTRATION_LOCK_FILENAME = ".specforge/.orchestration-lock"`, `ORCHESTRATION_LOCK_STALE_MINUTES = 120`, `ORCHESTRATION_PHASE_STATUSES = ("pending", "in-progress", "completed", "partial", "failed")`, `ORCHESTRATION_STATUSES = ("pending", "in-progress", "completed", "failed", "halted")`, `SHARED_INFRA_STATUSES = ("pending", "in-progress", "completed", "failed", "skipped")`, `VERIFICATION_SEVERITIES = ("error", "warning")`, `REPORT_VERDICTS = ("pass", "fail", "partial")`, `DOCKER_COMPOSE_UP_TIMEOUT = 120`, `HEALTH_CHECK_POLL_INTERVAL = 2`, `INTEGRATION_REPORT_FILENAME = "integration-report.md"`

- [X] T002 [P] [US1] Create tests in `tests/unit/test_orchestrator_models.py`: test all 14 frozen dataclasses from data-model.md — `Phase`, `OrchestrationPlan`, `ServiceStatus`, `PhaseState`, `OrchestrationState`, `ContractMismatch`, `ContractCheckResult`, `BoundaryCheckResult`, `VerificationResult`, `HealthCheckResult`, `RouteCheckResult`, `RequestFlowResult`, `EventPropagationResult`, `IntegrationTestResult`, `IntegrationReport`. Test: frozen immutability, default values, field types, `_now_iso()` factory. Follow `test_executor_models.py` pattern: one test class per dataclass, test `dataclasses.fields()` count, test `frozen=True` raises `FrozenInstanceError`.

- [X] T003 [US1] Create `src/specforge/core/orchestrator_models.py` implementing all 14 frozen dataclasses. Each dataclass follows `executor_models.py` patterns: `from __future__ import annotations`, `@dataclass(frozen=True)`, tuple for collections, `str | None` for optional fields, `_now_iso()` helper for timestamps. Make all tests from T002 pass.

**Checkpoint**: All model imports work, all model tests green, `ruff check` passes.

---

## Phase 2: Dependency Graph — US1 Core (Blocks Phase 3+)

**Purpose**: Pure function module for topological sort, cycle detection, phase computation. This is the algorithmic heart of the orchestrator.

- [X] T004 [P] [US1] Create tests in `tests/unit/test_dependency_graph.py`:

  **`TestBuildGraph`**:
  - `test_build_graph_from_manifest`: 6-service manifest (identity, admin, ledger, portfolio, planning, analytics) with communication links → returns adjacency dict `{"identity-service": (), "admin-service": (), "ledger-service": ("identity-service",), "portfolio-service": ("identity-service",), "planning-service": ("ledger-service",), "analytics-service": ("ledger-service", "portfolio-service")}`.
  - `test_build_graph_empty_manifest`: no services → `Err`.
  - `test_build_graph_no_communication`: 3 services with no deps → all have empty tuple dependencies.
  - `test_build_graph_unknown_dependency_target`: communication target not in services list → `Err` with specific message.

  **`TestDetectCycles`**:
  - `test_no_cycles`: 3-phase graph → returns empty tuple.
  - `test_simple_cycle`: A→B→A → returns tuple containing cycle `("A", "B")` or `("B", "A")`.
  - `test_self_cycle`: A→A → detected.
  - `test_complex_cycle`: A→B→C→A with D→A (D is outside cycle) → cycle detected, D not included.

  **`TestComputePhases`** (the critical 3-phase scenario):
  - `test_three_phase_scenario`: graph = {identity: (), admin: (), ledger: (identity,), portfolio: (identity,), planning: (ledger,), analytics: (ledger, portfolio)} → Phase 0: [identity, admin], Phase 1: [ledger, portfolio], Phase 2: [planning, analytics]. Assert service ordering within each phase is sorted alphabetically for determinism.
  - `test_single_service`: one service, no deps → one phase with one service.
  - `test_all_independent`: 4 services, no deps → single phase with all 4.
  - `test_linear_chain`: A→B→C → three phases, one service each.
  - `test_graph_with_cycle_returns_err`: cyclic graph → `Err` with cycle details.
  - `test_notification_service_phase`: add notification-service depending on ledger + planning → must be in Phase 3 (after planning's Phase 2), not Phase 2.

- [X] T005 [US1] Create `src/specforge/core/dependency_graph.py`: pure function module with `build_graph(manifest: dict) → Result[dict[str, tuple[str, ...]], str]`, `detect_cycles(graph: dict[str, tuple[str, ...]]) → tuple[tuple[str, ...], ...]`, `compute_phases(graph: dict[str, tuple[str, ...]]) → Result[tuple[Phase, ...], str]`. Implement Kahn's algorithm per research.md R-001. `compute_phases` calls `detect_cycles` first and returns `Err` if cycles found. Services within each phase sorted alphabetically. All functions ≤ 30 lines. Make all tests from T004 pass.

**Checkpoint**: `pytest tests/unit/test_dependency_graph.py -v` all green. `ruff check src/specforge/core/dependency_graph.py` clean.

---

## Phase 3: Orchestration State — US6 (Blocks Phase 5+)

**Purpose**: Project-level state persistence. Follows `pipeline_state.py` + `execution_state.py` atomic-write patterns.

- [X] T006 [P] [US6] Create tests in `tests/unit/test_orchestration_state.py`:
  - `test_create_initial_state`: 3-phase plan → OrchestrationState with 3 PhaseStates all pending, shared_infra_status="pending" for microservice, "skipped" for monolith.
  - `test_mark_shared_infra_complete`: state transitions shared_infra_status pending→completed.
  - `test_mark_shared_infra_failed`: state transitions shared_infra_status pending→failed.
  - `test_mark_phase_in_progress`: phase 0 status pending→in-progress.
  - `test_mark_service_completed`: specific service within phase marked completed with task counts.
  - `test_mark_service_failed`: specific service within phase marked failed with error message.
  - `test_mark_phase_completed`: all services completed → phase status = "completed".
  - `test_mark_phase_partial`: 2/3 services completed, 1 failed → phase status = "partial".
  - `test_mark_phase_failed`: all services failed → phase status = "failed".
  - `test_add_verification_result`: append VerificationResult to state.
  - `test_save_and_load_round_trip`: save to tmp_path, load back, assert equality.
  - `test_atomic_write_creates_parent_dirs`: save to non-existent dir → creates it.
  - `test_load_missing_file_returns_err`: non-existent path → `Err`.
  - `test_get_completed_services`: state with phases 0 (completed) and 1 (in-progress) → returns all services from phase 0.
  - `test_detect_resume_point`: state with phases 0=completed, 1=partial, 2=pending → resume from phase 1 first incomplete service.

- [X] T007 [US6] Create `src/specforge/core/orchestration_state.py`: pure function module following `pipeline_state.py` pattern. Functions: `create_initial_state(plan, architecture) → OrchestrationState`, `mark_shared_infra_complete/failed(state) → OrchestrationState`, `mark_phase_in_progress/mark_service_completed/mark_service_failed(state, ...) → OrchestrationState`, `compute_phase_status(phase_state) → str`, `add_verification_result(state, result) → OrchestrationState`, `save_state(path, state) → Result`, `load_state(path) → Result[OrchestrationState, str]`, `get_completed_services(state) → tuple[str, ...]`, `detect_resume_point(state) → tuple[int, str | None]` (phase_index, service_slug or None). Uses `os.replace()` atomic write + `os.fsync()`. Make all tests from T006 pass.

**Checkpoint**: `pytest tests/unit/test_orchestration_state.py -v` all green.

---

## Phase 4: Contract Enforcer — US2 Critical Path

**Purpose**: Post-phase contract verification. The core differentiator of phased orchestration.

- [X] T008 [P] [US2] Create tests in `tests/unit/test_contract_enforcer.py`:

  **`TestContractEnforcer`** with 3-phase scenario fixture:

  Setup: tmp_path with `.specforge/features/` containing contract files:
  - `identity-service/contracts/auth-api.json`: `{"endpoints": [{"path": "/auth/token", "response": {"claims": {"role": {"type": "string", "enum": ["admin", "user", "readonly"]}}}}]}`
  - `ledger-service/contracts/ledger-api.json`: `{"endpoints": [{"path": "/ledger/entries", "auth": "jwt"}]}`
  - `ledger-service/contracts/consumer-expectations.json`: `{"consumes": {"identity-service": {"auth-api": {"claims": {"role": {"type": "string", "enum": ["admin", "user", "readonly"]}}}}}}`

  Manifest with communication links: ledger→identity, portfolio→identity.

  - `test_verify_passing_contracts`: identity + ledger contracts match → `VerificationResult(passed=True, ...)`.
  - `test_verify_contract_mismatch_detected`: modify identity's contract to `{"role": {"type": "string"}}` (remove enum constraint) while ledger still expects enum → `VerificationResult(passed=False)` with `ContractMismatch(field="claims.role", expected="string enum [...]", actual="string")`.
  - `test_verify_multiple_mismatches_all_reported`: introduce 2 mismatches across 2 service pairs → both reported in single VerificationResult (FR-021).
  - `test_verify_cumulative_scope`: after Phase 2 with 3 services implemented, verify checks all pairs (identity↔ledger, identity↔portfolio, ledger↔portfolio) not just Phase 2 pairs.
  - `test_verify_no_contracts_dir_is_warning_not_error`: service with no `contracts/` dir → passes with warning (non-blocking).
  - `test_verify_boundary_analysis_runs`: mock BoundaryAnalyzer, verify it's called with correct manifest + implemented services.
  - `test_verify_monolith_skips_contracts`: architecture="monolithic" → contract checks skipped, boundary checks run instead.
  - `test_verify_modular_monolith_boundary_checks`: architecture="modular-monolith" → boundary analysis runs AND contract checks skipped. Distinct from plain monolith (which skips both) and microservice (which does both) (C4).
  - `test_cross_service_db_access_detected`: microservice mode, service A's contract references service B's database schema → `VerificationResult(passed=False)` with mismatch "cross-service database access" (FR-025).
  - `test_cross_module_schema_violation_monolith`: modular-monolith mode, module A writes to module B's schema → boundary violation detected (FR-026).

- [X] T009 [US2] Create `src/specforge/core/contract_enforcer.py`: class `ContractEnforcer` with constructor `__init__(self, project_root: Path, boundary_analyzer: BoundaryAnalyzer | None = None)`. Method `verify(self, implemented_services: tuple[str, ...], manifest: dict) → Result[VerificationResult, str]`. Loads contract files from `.specforge/features/<slug>/contracts/` for each implemented service. Finds consumer-expectations files that reference provider contracts. Compares field-by-field with `_compare_contracts()` helper. Checks database isolation: `_check_database_isolation()` (microservice: no cross-service DB refs; monolith: schema-per-module boundaries — FR-025/FR-026). Produces `ContractCheckResult` per service pair. Calls `BoundaryAnalyzer.analyze()` for shared entity detection. For modular-monolith: runs boundary analysis but skips contract checks. Returns aggregate `VerificationResult`. Functions ≤ 30 lines, split into `_load_service_contracts()`, `_find_consumer_expectations()`, `_compare_contracts()`, `_check_database_isolation()`, `_build_verification_result()`. Make all tests from T008 pass.

**Checkpoint**: `pytest tests/unit/test_contract_enforcer.py -v` all green. Contract mismatch detection confirmed with intentional JWT claims mismatch.

---

## Phase 5: Phase Executor — US1 Core (Blocks Phase 7)

**Purpose**: Runs all services in a phase by delegating to SubAgentExecutor. Implements continue-then-halt policy.

- [X] T010 [P] [US1] Create tests in `tests/unit/test_phase_executor.py`:

  Use mock `SubAgentExecutor` that returns `Ok(ExecutionState(...))` for success or `Err("build failed")` for failure.

  - `test_run_single_service_phase`: Phase(index=0, services=("identity-service",)) → calls executor.execute("identity-service", mode) → returns tuple with 1 ServiceStatus(status="completed").
  - `test_run_parallel_services`: Phase with 2 services → both executed, both ServiceStatus returned.
  - `test_continue_on_failure`: Phase with 3 services, portfolio-service fails → ledger-service and planning-service still complete, portfolio-service has status="failed" with error. Assert all 3 ServiceStatus returned.
  - `test_all_services_fail`: Phase with 2 services, both fail → 2 ServiceStatus both "failed".
  - `test_service_status_includes_task_counts`: mock executor returns ExecutionState with 5 completed/10 total tasks → ServiceStatus(tasks_completed=5, tasks_total=10).
  - `test_skipped_service`: Phase with service that has status="skipped" already in orchestration state → executor not called for it, ServiceStatus(status="skipped").
  - `test_context_isolation_only_dep_contracts`: Phase 1 with ledger-service (depends on identity-service) → SubAgentExecutor.execute() called with only identity-service's published contracts in context, NOT sibling portfolio-service's code or contracts (FR-007).
  - `test_sequential_execution_order`: Phase with 3 services → assert executor.execute() called sequentially (call order matches phase.services order). Within-phase parallelism is deferred to future feature (avoids port/git conflicts).

- [X] T011 [US1] Create `src/specforge/core/phase_executor.py`: class `PhaseExecutor` with constructor `__init__(self, sub_agent_executor: SubAgentExecutor, project_root: Path)`. Method `run(self, phase: Phase, mode: ExecutionMode, skipped_services: frozenset[str] = frozenset()) → tuple[ServiceStatus, ...]`. Iterates through phase services, calls `self._sub_agent_executor.execute(slug, mode)` for each, catches `Err` results, builds `ServiceStatus` from `ExecutionState`. Continues to next service on failure (DD-003). Functions ≤ 30 lines. Make all tests from T010 pass.

**Checkpoint**: `pytest tests/unit/test_phase_executor.py -v` all green.

---

## Phase 6: Integration Test Runner — US3

**Purpose**: docker-compose up + health checks + request flow + event propagation for microservice. Single-app test for monolith.

- [X] T012 [P] [US3] Create tests in `tests/unit/test_integration_test_runner.py`:

  Mock all subprocess calls (docker compose, curl/httpx). Never actually run Docker in unit tests.

  - `test_run_microservice_starts_compose`: mock `subprocess.run` for `docker compose up -d` → called with correct project dir.
  - `test_run_health_checks_all_pass`: mock HTTP GET to `/health` for 3 services → all HealthCheckResult(passed=True).
  - `test_run_health_check_failure`: one service returns 503 → HealthCheckResult(passed=False, status_code=503).
  - `test_run_health_check_timeout`: one service doesn't respond within timeout → HealthCheckResult(passed=False, error="timeout").
  - `test_run_gateway_routes`: mock HTTP calls through gateway → RouteCheckResult per route.
  - `test_run_teardown_always_called`: even on failure, `docker compose down` is called (via try/finally).
  - `test_run_monolith_mode`: architecture="monolithic" → no docker compose, runs monolith app test instead.
  - `test_run_returns_integration_test_result`: aggregate all checks → IntegrationTestResult with overall pass/fail.
  - `test_auto_generate_contract_tests`: given contract files for 3 services, auto-generates temporary test files from contract definitions, executes them, and cleans up after. Generated files not persisted (FR-023).
  - `test_compose_up_waits_for_dependencies`: verify `_compose_up()` uses `docker compose up -d --wait` to handle startup ordering (database healthy before app services).
  - `test_compose_up_subset_for_verification`: for inter-phase health checks, only starts services from completed phases (e.g., `docker compose up -d identity-service admin-service` for Phase 0 verification).

- [X] T013 [US3] Create `src/specforge/core/integration_test_runner.py`: class `IntegrationTestRunner` with constructor `__init__(self, project_root: Path)`. Method `run(self, services: tuple[str, ...], architecture: str) → Result[IntegrationTestResult, str]`. For microservice: `_compose_up(services)` using `docker compose up -d --wait` (compose v2 built-in health-wait for startup ordering), `_check_health(services)`, `_check_gateway_routes(manifest)`, `_auto_generate_contract_tests(services)` (create temp test files from contract JSON, execute, clean up — FR-023), `_compose_down()`. For monolith: `_run_monolith_test()`. Each method ≤ 30 lines. Uses `subprocess.run` with timeouts from config. Health check polling with `HEALTH_CHECK_POLL_INTERVAL`. `_compose_up(services)` accepts a service subset for inter-phase verification (only completed-phase services). Make all tests from T012 pass.

**Checkpoint**: `pytest tests/unit/test_integration_test_runner.py -v` all green.

---

## Phase 7: Integration Orchestrator — US1+US2 Core (Blocks Phase 8)

**Purpose**: The main controller that ties everything together: manifest → graph → phases → execute → verify → report.

- [X] T014 [P] [US1] Create tests in `tests/unit/test_integration_orchestrator.py`:

  All collaborators mocked. **3-phase scenario**: Phase 0: identity+admin (no deps), Phase 1: ledger+portfolio (dep: identity), Phase 2: planning+analytics+notification (dep: ledger/portfolio).

  **`TestExecuteHappyPath`**:
  - `test_execute_all_three_phases`: mock manifest with 6 services, mock SubAgentExecutor returns Ok for all, mock ContractEnforcer returns passed=True, mock IntegrationTestRunner returns passed=True → `Ok(IntegrationReport(verdict="pass", total_services=6, total_phases=3))`. Assert SharedInfraExecutor.execute() called first. Assert PhaseExecutor.run() called 3 times in order. Assert ContractEnforcer.verify() called 3 times with cumulative service lists: after phase 0: (identity,admin), after phase 1: (identity,admin,ledger,portfolio), after phase 2: all 6.
  - `test_progress_display_called_at_transitions`: verify `render_phase_map()` called before execution, `render_service_table()` called after each phase, `render_summary()` called at end.
  - `test_execute_monolith_skips_shared_infra`: architecture="monolithic" → SharedInfraExecutor.execute() NOT called. ContractEnforcer NOT called. IntegrationTestRunner called with architecture="monolithic".

  **`TestExecuteFailures`**:
  - `test_shared_infra_failure_halts`: SharedInfraExecutor returns Err → no phases attempted, report verdict="fail".
  - `test_service_failure_halts_after_phase`: Phase 1 ledger fails → Phase 1 continues (portfolio completes, both in same phase), Phase 2 NOT attempted. Report shows Phase 1 as "partial".
  - `test_contract_violation_halts`: Phase 0 passes, ContractEnforcer after Phase 0 returns passed=False → Phase 1 NOT attempted. Report shows verification failure.
  - `test_all_services_in_phase_fail`: Phase 0 both services fail → phase status="failed", no further phases.

  **`TestExecutePartial`**:
  - `test_to_phase_limits_execution`: phase_ceiling=1 → only Phase 0 and Phase 1 executed, Phase 2 skipped. Integration test skipped.
  - `test_to_phase_exceeds_total`: phase_ceiling=10 with 3 phases → all phases executed, warning logged.

  **`TestExecuteResume`**:
  - `test_resume_skips_completed_phases`: state with Phase 0 completed → Phase 0 skipped, Phase 1 starts.
  - `test_resume_no_state_starts_fresh`: no state file → starts from scratch (FR-014).

  **`TestPreFlight`**:
  - `test_cycle_detected_before_execution`: manifest with cycle → `Err` with cycle details, nothing executed.
  - `test_missing_artifacts_skips_service`: identity-service has no tasks.md → skipped, planning-service (depends on identity) also skipped.
  - `test_lock_prevents_concurrent_run`: lock file exists → `Err` with lock details.

- [X] T015 [US1] Create `src/specforge/core/integration_orchestrator.py`: class `IntegrationOrchestrator` with constructor per contracts/orchestrate-cmd.md. Method `execute(self, mode, resume, phase_ceiling) → Result[IntegrationReport, str]`. Orchestration loop:
  1. `_load_manifest()` → architecture + services
  2. `_build_plan()` → dependency_graph.build_graph() + compute_phases() → OrchestrationPlan
  3. `_preflight_check()` → validate artifacts exist, check lock, detect cycles
  4. `_acquire_lock()` → pipeline_lock.acquire_lock()
  5. `_load_or_create_state()` → orchestration_state.load_state() or create_initial_state()
  6. `_run_shared_infra()` → SharedInfraExecutor.execute() (microservice only)
  7. `_run_phases()` → loop: PhaseExecutor.run() → ContractEnforcer.verify() → update state
  8. `_run_integration()` → IntegrationTestRunner.run() (if all phases complete)
  9. `_build_report()` → IntegrationReport from OrchestrationState
  10. `_release_lock()`
  Each step is a private method ≤ 30 lines. The `execute()` method is the top-level coordinator calling these in order with early returns on failure. Uses try/finally for lock release. Make all tests from T014 pass.

**Checkpoint**: `pytest tests/unit/test_integration_orchestrator.py -v` all green. Full 3-phase happy path + all failure modes verified.

---

## Phase 8: Integration Reporter — US7

**Purpose**: Generates Markdown integration report via Jinja2 template.

- [X] T016 [P] [US7] Create Jinja2 template `src/specforge/templates/base/features/integration-report.md.j2`: renders IntegrationReport data as Markdown. Sections: Summary (architecture, total services, verdict), Phase Results (per-phase table with service status), Verification Results (per-boundary contract/boundary results), Integration Validation (health checks, gateway, request flow, events), Failures (detailed error info for any failed services/checks). Uses `{% for %}` loops and `{% if %}` conditionals. Follows existing template patterns from `src/specforge/templates/base/`.

- [X] T017 [P] [US7] Create tests in `tests/unit/test_integration_reporter.py`:
  - `test_generate_pass_report`: IntegrationReport with verdict="pass", 3 phases, 6 services all completed → Markdown file created with all sections.
  - `test_generate_fail_report`: report with 1 failed service, 1 contract violation → failure details in report.
  - `test_generate_partial_report`: report with verdict="partial", Phase 2 partial → shows which services succeeded/failed.
  - `test_report_output_path`: report written to `.specforge/integration-report.md`.
  - `test_report_includes_elapsed_time`: report contains total elapsed time calculation.

- [X] T018 [US7] Create `src/specforge/core/integration_reporter.py`: class `IntegrationReporter` with constructor `__init__(self, renderer: TemplateRenderer, registry: TemplateRegistry)`. Method `generate(self, state: OrchestrationState, plan: OrchestrationPlan) → Result[Path, str]`. Builds template context from OrchestrationState, calls `renderer.render()` with `integration-report.md.j2`, writes to `.specforge/integration-report.md`. Functions ≤ 30 lines. Make all tests from T017 pass.

**Checkpoint**: `pytest tests/unit/test_integration_reporter.py -v` all green. Snapshot test for rendered report (syrupy).

---

## Phase 9: CLI Extension — US1+US4+US5 (Blocks integration tests)

**Purpose**: Extend `specforge implement` with `--all` and `--to-phase` flags.

- [X] T019 [P] [US1] Create tests in `tests/integration/test_implement_all_microservice.py`:

  Full integration test using CliRunner + tmp_path with scaffolded 6-service microservice project.

  - `test_implement_all_happy_path`: scaffold project with 6 services across 3 phases, mock SubAgentExecutor/SharedInfraExecutor/ContractEnforcer to return success → exit code 0, output contains "Verdict: PASS".
  - `test_implement_all_contract_violation`: scaffold project, ContractEnforcer returns mismatch → exit code 1, output contains "Contract mismatch" and specific field.
  - `test_implement_all_to_phase`: `--all --to-phase 1` → only Phase 0 and 1 executed, exit code 0.
  - `test_implement_all_and_target_mutually_exclusive`: `--all identity-service` → exit code 2, error message.
  - `test_implement_all_and_shared_infra_mutually_exclusive`: `--all --shared-infra` → exit code 2.
  - `test_to_phase_requires_all`: `--to-phase 2` without `--all` → exit code 2.

- [X] T020 [P] [US4] Create tests in `tests/integration/test_implement_all_monolith.py`:
  - `test_implement_all_monolith_no_docker`: scaffold monolith project, mock executor → no docker commands, no contract verification, exit code 0.
  - `test_implement_all_monolith_boundary_checks`: modular-monolith project → boundary compliance checks run instead of contracts.

- [X] T021 [P] [US6] Create tests in `tests/integration/test_implement_all_resume.py`:
  - `test_resume_skips_completed`: create orchestration state with Phase 0 completed, run `--all --resume` → Phase 0 not re-run.
  - `test_resume_no_state_starts_fresh`: no state file, `--all --resume` → starts from beginning.

- [X] T022 [US1] Extend `src/specforge/cli/implement_cmd.py`: add `--all` flag (is_flag=True, mutually exclusive with target and --shared-infra), add `--to-phase` option (type=int, requires --all). When `--all` is set: import and construct IntegrationOrchestrator with all dependencies (SubAgentExecutor, SharedInfraExecutor, ContractEnforcer, IntegrationTestRunner, IntegrationReporter), call `orchestrator.execute(mode, resume, phase_ceiling)`, display result summary using Rich console, sys.exit(0) on success, sys.exit(1) on failure. Preserve all existing single-service behavior untouched. Make all integration tests from T019-T021 pass.

**Checkpoint**: `pytest tests/integration/test_implement_all_*.py -v` all green. Existing `specforge implement identity-service` still works.

---

## Phase 10: Progress Display — US7

**Purpose**: Rich-based real-time progress output during orchestration.

- [X] T023 [P] [US7] Create tests for progress display in `tests/unit/test_orchestration_progress.py`:
  - `test_render_phase_map`: OrchestrationPlan with 3 phases → Rich Tree with ✅/⏳/⏸ indicators per phase.
  - `test_render_service_table`: PhaseState with 3 services (1 completed, 1 in-progress, 1 pending) → Rich Table with status column.
  - `test_render_verification_result`: VerificationResult(passed=True) → "✅ contracts OK ✅ boundaries OK".
  - `test_render_final_summary`: IntegrationReport with verdict="pass" → summary table with totals.

- [X] T024 [US7] Add progress display methods to IntegrationOrchestrator (or extract to a small helper in `src/specforge/core/orchestration_progress.py`): `render_phase_map(plan, state) → Tree`, `render_service_table(phase_state) → Table`, `render_verification(result) → str`, `render_summary(report) → Panel`. Hook into orchestrator loop: display phase map before execution, update after each phase, display summary at end. Uses `rich.tree.Tree`, `rich.table.Table`, `rich.panel.Panel`. Each function ≤ 30 lines. Make all tests from T023 pass.

**Checkpoint**: `pytest tests/unit/test_orchestration_progress.py -v` all green.

---

## Phase 11: Edge Cases & Polish

**Purpose**: Handle all edge cases from spec, ensure robustness.

- [X] T025 [P] [US1] Add edge case tests to `tests/unit/test_dependency_graph.py`:
  - `test_single_service_no_deps_single_phase`: 1 service → 1 phase, acts as pass-through.
  - `test_service_missing_from_manifest_in_communication`: A depends on B but B not in services → `Err`.

- [X] T026 [P] [US1] Add edge case tests to `tests/unit/test_integration_orchestrator.py`:
  - `test_concurrent_lock_prevents_second_run`: orchestrator acquires lock, second call → `Err` with lock message.
  - `test_lock_released_on_failure`: orchestrator fails mid-phase → lock file removed (try/finally).
  - `test_service_with_no_tasks_md_skipped`: identity-service missing tasks.md → skipped, ledger-service (depends on identity) also skipped with explanation.
  - `test_to_phase_exceeds_total_logs_warning`: phase_ceiling=99, 3 phases → all phases run, warning logged.
  - `test_single_service_passthrough`: 1 service, no deps, microservice mode → shared infra + single phase + integration test, no contract verification needed (edge case 6).

- [X] T027 [US1] Implement edge case handling in existing modules: ensure `dependency_graph.py` handles unknown targets in communication links (T025 test), ensure `IntegrationOrchestrator._preflight_check()` validates artifacts and propagates skip to dependents (T026 test), ensure lock is always released via try/finally. Make all edge case tests pass.

**Checkpoint**: `pytest tests/unit/ -v -k "edge"` or full suite green. All 10 edge cases from spec covered.

---

## Phase 12: Final Validation

**Purpose**: Full test suite, linting, cross-module integration.

- [X] T028 Run `ruff check src/specforge/core/orchestrator_models.py src/specforge/core/dependency_graph.py src/specforge/core/orchestration_state.py src/specforge/core/contract_enforcer.py src/specforge/core/phase_executor.py src/specforge/core/integration_test_runner.py src/specforge/core/integration_orchestrator.py src/specforge/core/integration_reporter.py src/specforge/cli/implement_cmd.py` — fix any lint issues.

- [X] T029 Run full test suite: `pytest tests/ -v --tb=short` — all existing tests still pass (no regressions), all new Feature 011 tests pass.

- [X] T030 Run `pytest tests/ --cov=src/specforge/core --cov-report=term-missing` — verify 100% coverage on new modules: `orchestrator_models.py`, `dependency_graph.py`, `orchestration_state.py`, `contract_enforcer.py`, `phase_executor.py`, `integration_test_runner.py`, `integration_orchestrator.py`, `integration_reporter.py`.

- [X] T031 Run quickstart.md validation: verify `specforge implement --all --help` shows new flags, verify `specforge implement --all --to-phase 2` argument validation works, verify backward compatibility with `specforge implement identity-service`.

**Checkpoint**: Full green. Feature 011 complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Models+Constants)**: No dependencies — start immediately
- **Phase 2 (Dependency Graph)**: Depends on Phase 1 (uses Phase model)
- **Phase 3 (Orchestration State)**: Depends on Phase 1 (uses all models)
- **Phase 4 (Contract Enforcer)**: Depends on Phase 1 (uses VerificationResult, ContractCheckResult)
- **Phase 5 (Phase Executor)**: Depends on Phase 1 (uses ServiceStatus, Phase)
- **Phase 6 (Integration Test Runner)**: Depends on Phase 1 (uses IntegrationTestResult)
- **Phase 7 (Integration Orchestrator)**: Depends on Phases 2-6 (uses all components)
- **Phase 8 (Integration Reporter)**: Depends on Phase 1 (uses IntegrationReport)
- **Phase 9 (CLI Extension)**: Depends on Phase 7 (uses IntegrationOrchestrator)
- **Phase 10 (Progress Display)**: Depends on Phase 1 (uses models for rendering)
- **Phase 11 (Edge Cases)**: Depends on Phase 7 (extends existing modules)
- **Phase 12 (Final Validation)**: Depends on all phases

### Parallel Opportunities

After Phase 1 completes, Phases 2-6 + 8 + 10 can all run in parallel (different files, no dependencies between them). Phase 7 blocks on 2-6. Phase 9 blocks on 7. Phase 11 blocks on 7. Phase 12 blocks on all.

```
Phase 1 (Models)
    ├── Phase 2 (Graph)     ─┐
    ├── Phase 3 (State)      │
    ├── Phase 4 (Contract) ──├── Phase 7 (Orchestrator) ── Phase 9 (CLI)
    ├── Phase 5 (Executor)   │                          └── Phase 11 (Edge Cases)
    ├── Phase 6 (Runner)   ──┘
    ├── Phase 8 (Reporter) ────────────────────────────────── Phase 12 (Validation)
    └── Phase 10 (Progress) ──────────────────────────────/
```

### TDD Enforcement

Within EVERY phase:
1. Test file created FIRST (odd-numbered tasks: T002, T004, T006, ...)
2. Tests run and FAIL (red)
3. Implementation created (even-numbered tasks: T003, T005, T007, ...)
4. Tests run and PASS (green)
5. `ruff check` on new files (clean)

---

## Notes

- Total tasks: 31 (T001–T031)
- Test tasks: 14 (T002, T004, T006, T008, T010, T012, T014, T017, T019, T020, T021, T023, T025, T026)
- Implementation tasks: 13 (T001, T003, T005, T007, T009, T011, T013, T015, T016, T018, T022, T024, T027)
- Validation tasks: 4 (T028, T029, T030, T031)
- Critical path: T001 → T002/T003 → T004/T005 → T014/T015 → T019/T022 → T028–T031
- Test scenario: 6 services across 3 phases (identity, admin | ledger, portfolio | planning, analytics) + notification added in edge cases
- Contract violation test: intentional JWT claims.role enum mismatch between identity-service (provider) and ledger-service (consumer)
