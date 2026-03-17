# Tasks: Edge Case Analysis Engine

**Input**: Design documents from `/specs/007-edge-case-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/edge-cases-cmd.md
**Tests**: TDD — test tasks precede implementation tasks. Write tests first, verify they fail, then implement.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US5) this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Constants, package structure, YAML pattern files — the foundation everything builds on.

- [ ] T001 Add Feature 007 constants to `src/specforge/core/config.py` — EDGE_CASE_MAX_PER_SERVICE (30), STANDARD_EDGE_CASE_CATEGORIES (6 standard), MICROSERVICE_EDGE_CASE_CATEGORIES (6 distributed), MODULAR_MONOLITH_EXTRA_CATEGORIES ("interface_contract_violation"), SEVERITY_MATRIX_MICROSERVICE dict[(bool, str) → str] using `async-event` (singular, matching COMMUNICATION_PATTERNS), SEVERITY_MATRIX_MONOLITH dict[str → str], EDGE_CASE_CATEGORY_PRIORITY dict[str → int] with 13 entries (including interface_contract_violation at priority 7), EDGE_CASE_BASE_COUNT (6), EDGE_CASE_PER_DEPENDENCY (2), EDGE_CASE_PER_EVENT (1), EDGE_CASE_PER_EXTRA_FEATURE (2). Follow exact values from plan.md D6
- [ ] T002 Create `src/specforge/knowledge/__init__.py` and `src/specforge/knowledge/edge_case_patterns/__init__.py` — empty package init files to enable `importlib.resources` loading
- [ ] T003 [P] Create 6 microservice YAML pattern files in `src/specforge/knowledge/edge_case_patterns/` — `service_unavailability.yaml`, `network_partition.yaml`, `eventual_consistency.yaml`, `distributed_transactions.yaml`, `version_skew.yaml`, `data_ownership.yaml`. Each file has `category`, `scenarios[]` with `scenario_template`, `trigger_template`, `handling_strategies[]`, `severity_microservice` (null — runtime), `severity_monolith` (null), `test_template`, `applicable_patterns[]` using `async-event` (singular, matching config.py COMMUNICATION_PATTERNS). Follow plan.md D9 format and pattern-to-category mapping table exactly
- [ ] T004 [P] Create 7 standard/modular YAML pattern files in `src/specforge/knowledge/edge_case_patterns/` — `concurrency.yaml`, `data_boundary.yaml`, `state_machine.yaml`, `ui_ux.yaml`, `security.yaml`, `data_migration.yaml`, `interface_contract_violation.yaml`. The 6 standard files have `category`, `scenarios[]` with same fields as T003 but `severity_monolith` set to the category's monolith severity and `applicable_patterns` empty (applies to all). `interface_contract_violation.yaml` has `severity_monolith: null`, `severity_microservice: null` (severity assigned at runtime as "high" per FR-016), applicable to modular-monolith only
- [ ] T005 [P] Add `pyyaml>=6.0,<7.0` to `[project.dependencies]` in `pyproject.toml` if not already explicit. Run `uv sync` to verify dependency resolution

**Checkpoint**: Config constants defined, knowledge package exists with 12 YAML pattern files, PyYAML dependency explicit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models, pattern loader, filter, budget, severity — all core building blocks that MUST complete before user story implementation.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests First ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] Write tests for EdgeCase, EdgeCasePattern, EdgeCaseReport frozen dataclasses in `tests/unit/test_edge_case_models.py` — test immutability (frozen), field access, EC-NNN id format validation, severity literal validation, affected_services non-empty invariant, EdgeCaseReport.total_count == len(edge_cases). Test EdgeCaseCategory type covers all 13 categories (6 standard + 6 microservice + interface_contract_violation). Test EdgeCasePattern.handling_strategies is tuple. Test EdgeCasePattern.applicable_patterns is tuple. Minimum 15 tests
- [ ] T007 [P] Write tests for PatternLoader in `tests/unit/test_edge_case_patterns.py` — test load_patterns() returns tuple[EdgeCasePattern, ...], each pattern has non-empty category/scenario_template/trigger_template/handling_strategies/test_template, all 13 YAML files loaded (count check: 6 microservice + 6 standard + 1 interface_contract_violation), verify applicable_patterns is tuple, verify severity fields are str|None, test caching (second call returns same object). Minimum 10 tests
- [ ] T008 [P] Write tests for ArchitectureEdgeCaseFilter in `tests/unit/test_edge_case_filter.py` — test microservice keeps ALL patterns, monolith keeps only patterns whose category is in STANDARD_EDGE_CASE_CATEGORIES, modular-monolith keeps standard set + interface_contract_violation category, unknown architecture falls back to monolith behavior + warning emitted. Minimum 8 tests
- [ ] T009 [P] Write tests for EdgeCaseBudget in `tests/unit/test_edge_case_budget.py` — test allocate(deps=2, events=1, features=3) = 6+4+1+4 = 15, test cap at 30 (allocate with large inputs), test prioritize() sorts by severity then category priority, test prioritize() truncates to budget, test zero dependencies returns base 6, test single feature (features=1) adds 0 extra. Note: events_count = number of unique event roles for the service (producer roles + consumer roles). Minimum 10 tests

### Implementation

- [ ] T010 Implement `src/specforge/core/edge_case_models.py` — frozen dataclasses: EdgeCaseCategory (Literal union of all 13 categories including interface_contract_violation), Severity (Literal["critical","high","medium","low"]), EdgeCase (id, category, severity, scenario, trigger, affected_services: tuple[str,...], handling_strategy, test_suggestion), EdgeCasePattern (category, scenario_template, trigger_template, handling_strategies: tuple[str,...], severity_microservice: str|None, severity_monolith: str|None, test_template, applicable_patterns: tuple[str,...]), EdgeCaseReport (service_slug, architecture, edge_cases: tuple[EdgeCase,...], total_count: int). Add factory function `make_edge_case_id(n: int) -> str` returning f"EC-{n:03d}". All type hints
- [ ] T011 Implement `src/specforge/core/edge_case_patterns.py` — PatternLoader class with constructor injection (package path). `load_patterns() -> tuple[EdgeCasePattern, ...]` uses `importlib.resources.files("specforge.knowledge.edge_case_patterns")` to discover *.yaml files, parses each with `yaml.safe_load()`, maps to EdgeCasePattern dataclass, caches in `_cache: tuple[EdgeCasePattern, ...] | None`. ≤30-line functions. Return `Result[tuple[EdgeCasePattern, ...], str]`
- [ ] T012 Implement `src/specforge/core/edge_case_filter.py` — ArchitectureEdgeCaseFilter class. Constructor takes architecture: str. `filter_patterns(patterns: tuple[EdgeCasePattern, ...]) -> tuple[EdgeCasePattern, ...]`. Monolithic: keep patterns whose category is in STANDARD_EDGE_CASE_CATEGORIES. Microservice: keep all. Modular-monolith: standard set + "interface_contract_violation" category. Unknown architecture: fall back to monolith + emit warning via `warnings.warn()`. ≤30-line functions
- [ ] T013 Implement `src/specforge/core/edge_case_budget.py` — EdgeCaseBudget class. `allocate(deps_count: int, events_count: int, features_count: int) -> int` = 6 + 2*deps + events + 2*max(0, features-1), capped at 30. `prioritize(cases: tuple[EdgeCase, ...], budget: int) -> tuple[EdgeCase, ...]` sorts by SEVERITY_ORDER (critical=0, high=1, medium=2, low=3) then EDGE_CASE_CATEGORY_PRIORITY, returns first `budget` items. ≤30-line functions

**Checkpoint**: All foundational modules implemented and tested. Models validated as frozen + correct types. PatternLoader loads all 12 YAML files. Filter correctly partitions by architecture. Budget calculates and truncates correctly.

---

## Phase 3: User Story 1 — Microservice Edge Cases with Inter-Service Failures (Priority: P1) 🎯 MVP

**Goal**: MicroserviceEdgeCaseAnalyzer reads communication[] and events[] from ServiceContext to generate topology-specific edge cases for a microservice. Test with ledger-service (depends on identity-service via sync-rest, publishes transaction.created consumed by analytics-service and notification-service).

**Independent Test**: Provide a microservice ServiceContext with known deps/events, verify generated EdgeCaseReport contains dependency-specific and event-specific cases with correct severity, services, and patterns.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Write tests for MicroserviceEdgeCaseAnalyzer dependency-based edge cases in `tests/unit/test_edge_case_analyzer.py` — fixture: ledger-service with required sync-rest dep on identity-service. Assert: service_unavailability case mentions "identity-service", severity is "critical" (required+sync-rest), handling_strategy includes "circuit breaker", affected_services includes both ("ledger-service", "identity-service"), test_suggestion mentions stubbing identity-service. Test optional dep produces "high" severity. Test async-event dep produces network_partition instead of service_unavailability (use `async-event` singular matching COMMUNICATION_PATTERNS). Minimum 8 tests
- [ ] T015 [P] [US1] Write tests for MicroserviceEdgeCaseAnalyzer event-based edge cases in `tests/unit/test_edge_case_analyzer.py` — fixture: ledger-service produces transaction.created consumed by [analytics-service, notification-service]. Assert: 1 eventual_consistency case per consumer (2 total), 1 distributed_transaction case (2+ consumers), producer gets "message loss" scenario, each consumer named in affected_services. Test single-consumer event produces NO distributed_transaction case. Minimum 6 tests
- [ ] T016 [P] [US1] Write tests for MicroserviceEdgeCaseAnalyzer edge cases in `tests/unit/test_edge_case_analyzer.py` — test data_ownership case generated when BoundaryAnalyzer finds shared entities (mock BoundaryAnalyzer.analyze()), test dangling service reference (target not in manifest) includes "(service not found in manifest)" in scenario, test circular dependency (A→B, B→A both in communication[]) emits circular-dependency edge case, test zero-dependency microservice omits inter-service categories, test budget cap enforcement with sequential EC-001..EC-NNN numbering. Minimum 8 tests

### Implementation for User Story 1

- [ ] T017 [US1] Implement `src/specforge/core/edge_case_analyzer.py` — MicroserviceEdgeCaseAnalyzer class. Constructor injection: patterns (tuple[EdgeCasePattern,...]), architecture_filter (ArchitectureEdgeCaseFilter), budget (EdgeCaseBudget), boundary_analyzer (optional). `analyze(service_ctx: ServiceContext, manifest: dict) -> Result[EdgeCaseReport, str]`. Steps per plan.md D2: (1) generate standard-category cases from filtered patterns, (2) for each communication[] dep instantiate dependency patterns with real service names + severity from matrix, (3) for each events[] where service is producer instantiate eventual_consistency per consumer + distributed_transaction if 2+ consumers, (4) shared entities via BoundaryAnalyzer, (5) dangling ref handling per FR-020, (6) apply budget.prioritize(), (7) number sequentially EC-001..EC-NNN. Helper: `_instantiate_pattern(pattern, context_vars) -> EdgeCase` replaces {{placeholders}}. Helper: `_resolve_severity(required, pattern, category) -> str` uses SEVERITY_MATRIX. ≤30-line functions. All type hints
- [ ] T018 [US1] Write integration test in `tests/unit/test_edge_case_analyzer.py` — full end-to-end: build a PersonalFinance-like microservice manifest with ledger-service (2 deps, 1 event with 2 consumers → events_count=1 producer role, 3 features). Call analyze(). Assert total_count matches budget formula (6+4+1+4=15 if 2 deps, 1 event role, 3 features). Assert all EC IDs sequential. Assert severity distribution is deterministic. Assert no duplicate categories beyond what deps/events produce

**Checkpoint**: MicroserviceEdgeCaseAnalyzer produces correct, topology-aware edge cases for ledger-service. Budget enforced. IDs sequential. Severity deterministic.

---

## Phase 4: User Story 2 — Monolith Mode with Standard Categories (Priority: P1)

**Goal**: Monolith and modular-monolith architectures produce simpler edge cases with no distributed system concerns.

**Independent Test**: Provide a monolith manifest and verify zero distributed-system categories in output, only standard categories present.

### Tests for User Story 2 ⚠️

- [ ] T019 [P] [US2] Write tests for monolith edge case generation in `tests/unit/test_edge_case_analyzer.py` — fixture: monolith manifest with auth module. Test single-feature monolith → exactly 6 standard categories (concurrency, data_boundary, state_machine, ui_ux, security, data_migration). Test multi-feature monolith (3 features) → 6 + 2×(3-1) = 10 cases (budget applies to all architectures). Severity matches SEVERITY_MATRIX_MONOLITH (security=high, concurrency=high, data_boundary=medium, etc.). Assert zero service_unavailability/network_partition/eventual_consistency/distributed_transaction/version_skew/data_ownership categories in ANY monolith output. Minimum 6 tests
- [ ] T020 [P] [US2] Write tests for modular-monolith edge case generation in `tests/unit/test_edge_case_analyzer.py` — fixture: modular-monolith manifest. Assert: standard categories PLUS interface_contract_violation category present, interface_contract_violation severity is "high", no other microservice categories present. Minimum 3 tests

### Implementation for User Story 2

- [ ] T021 [US2] Add monolith/modular-monolith paths to `src/specforge/core/edge_case_analyzer.py` — if architecture is "monolithic", skip dependency/event analysis entirely, generate only from standard-category patterns. If "modular-monolith", add interface_contract_violation. Reuse the same `analyze()` entry point with architecture branching. Severity assigned from SEVERITY_MATRIX_MONOLITH for standard categories. ≤30-line functions

**Checkpoint**: Monolith with 1 feature generates exactly 6 standard-category edge cases; with multiple features, budget formula adds feature-interaction cases. Modular-monolith adds interface_contract_violation. Zero distributed concerns in either mode. SC-002 satisfied.

---

## Phase 5: User Story 3 — Machine-Parseable YAML Frontmatter (Priority: P2)

**Goal**: Each edge case in edge-cases.md has a fenced YAML block with id, category, severity, affected_services (YAML list), handling_strategy, test_suggestion — parseable by Feature 009 sub-agent.

**Independent Test**: Generate edge-cases.md, regex-extract all ` ```yaml...``` ` blocks, parse with yaml.safe_load(), verify every block has all required fields with valid values.

### Tests for User Story 3 ⚠️

- [ ] T022 [P] [US3] Write tests for YAML frontmatter rendering in `tests/unit/test_edge_case_template.py` — test render with EdgeCaseReport context produces fenced YAML blocks per edge case, test each block is valid YAML with required fields (id, category, severity, affected_services, handling_strategy, test_suggestion), test affected_services is a YAML list not comma-separated string, test backward compatibility (empty edge_cases falls back to adapter_edge_cases loop), test unknown extra fields tolerated (forward compat). Minimum 8 tests

### Implementation for User Story 3

- [ ] T023 [US3] Enhance `src/specforge/templates/base/features/edge-cases.md.j2` — add conditional block: `{% if edge_cases %}` renders enriched format with per-case heading + fenced ` ```yaml ` block containing id/category/severity/affected_services (as YAML list)/handling_strategy/test_suggestion + scenario description + trigger. `{% else %}` falls back to existing adapter_edge_cases loop. Preserve all existing template variables (project_name, features, adapter_edge_cases, service, architecture). Use `{{ ec.affected_services | join(', ') }}` for YAML list rendering via custom approach
- [ ] T024 [US3] Write snapshot tests in `tests/snapshots/test_edge_cases_template.py` — render edge-cases.md.j2 with (a) microservice EdgeCaseReport (5+ edge cases, mixed severity), (b) monolith EdgeCaseReport (6 standard cases), (c) empty edge_cases (backward compat with adapter_edge_cases). Use syrupy snapshot assertions. Minimum 3 snapshot tests

**Checkpoint**: All generated edge-cases.md files have valid, parseable YAML frontmatter per case. SC-003 and SC-005 satisfied. Backward compatibility preserved.

---

## Phase 6: User Story 4 — Pipeline Integration as Phase 3b (Priority: P2)

**Goal**: Enhanced EdgecasePhase delegates to MicroserviceEdgeCaseAnalyzer, passes enriched EdgeCaseReport to template context, updates pipeline state.

**Independent Test**: Invoke EdgecasePhase.run() with a ServiceContext and verify pipeline state shows `complete` for edgecase phase with correct artifact path.

### Tests for User Story 4 ⚠️

- [ ] T025 [P] [US4] Write tests for enhanced EdgecasePhase in `tests/unit/test_phases/test_edgecase_phase.py` — test _build_context() includes `edge_cases` key (list of EdgeCase dicts) alongside existing `adapter_edge_cases`, test analyzer is called with correct ServiceContext, test pipeline state updated to complete on success, test pipeline state updated to failed on analyzer error. Update existing 3 tests (test_microservice_includes_distributed, test_monolith_boundary_violations, test_modular_monolith_interface_violations) to also assert new enriched edge_cases in context. Minimum 6 new tests + 3 updated

### Implementation for User Story 4

- [ ] T026 [US4] Enhance `src/specforge/core/phases/edgecase_phase.py` — inject PatternLoader, ArchitectureEdgeCaseFilter, EdgeCaseBudget, MicroserviceEdgeCaseAnalyzer into phase (or construct internally from ServiceContext). Override `_build_context()` to: (1) load patterns, (2) filter by architecture, (3) run analyzer, (4) convert EdgeCaseReport to template context dict with `edge_cases` key (list of dicts with all YAML fields), (5) keep existing `adapter_edge_cases` for backward compat. Handle analyzer errors via Result — if Err, log warning and fall back to adapter-only behavior. ≤30-line functions
- [ ] T027 [US4] Write integration test in `tests/integration/test_phases/test_edgecase_phase.py` — test full phase execution with tmp_path, microservice manifest, verify edge-cases.md written with YAML frontmatter, verify pipeline state complete. Test monolith manifest produces standard-only edge-cases.md. Minimum 2 integration tests

**Checkpoint**: EdgecasePhase delegates to analyzer, produces enriched edge-cases.md, updates pipeline state. Backward compatible — old tests still pass.

---

## Phase 7: User Story 5 — Standalone CLI Command (Priority: P3)

**Goal**: `specforge edge-cases <target>` generates edge-cases.md for a specific service without running the full pipeline.

**Independent Test**: Invoke via CliRunner with a manifest in tmp_path, verify edge-cases.md produced and pipeline state updated.

### Tests for User Story 5 ⚠️

- [ ] T028 [P] [US5] Write integration tests for CLI in `tests/integration/test_edge_cases_cmd.py` — test success path: tmp_path with manifest.json + spec.md for ledger-service, invoke `specforge edge-cases ledger-service`, assert exit code 0, output contains "Generated N edge cases", edge-cases.md exists. Test error paths: no manifest.json → exit 1 + error message, unknown service slug → exit 1 + error message. Test feature number resolution: `specforge edge-cases 002` resolves to correct service. Use CliRunner() (no mix_stderr). Minimum 5 tests

### Implementation for User Story 5

- [ ] T029 [US5] Implement `src/specforge/cli/edge_cases_cmd.py` — follow `research_cmd.py` pattern exactly. `@click.command("edge-cases")` with `target` argument. Steps: resolve_target → load_service_context → acquire_lock → load patterns → filter → analyze → render template → update pipeline state → release lock → print summary (count, severity breakdown, output path). Error handling: no manifest → Err + exit 1, unknown service → Err + exit 1, lock held → Err + exit 1, template error → Err + exit 1. Use Rich console for output. ≤30-line functions
- [ ] T030 [US5] Register `edge_cases` command in `src/specforge/cli/main.py` — import edge_cases_cmd, add `cli.add_command(edge_cases_cmd.edge_cases)` following existing pattern for research/clarify commands

**Checkpoint**: `specforge edge-cases ledger-service` produces correct edge-cases.md with YAML frontmatter. All error paths handled. Pipeline state updated.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate full integration, fix any broken existing tests, final lint pass.

- [ ] T031 [P] Update `tests/unit/test_config.py` to verify all new Feature 007 constants are present and correctly typed — EDGE_CASE_MAX_PER_SERVICE, STANDARD_EDGE_CASE_CATEGORIES, MICROSERVICE_EDGE_CASE_CATEGORIES, MODULAR_MONOLITH_EXTRA_CATEGORIES, SEVERITY_MATRIX_MICROSERVICE (verify keys use `async-event` singular), SEVERITY_MATRIX_MONOLITH, EDGE_CASE_CATEGORY_PRIORITY (13 entries including interface_contract_violation)
- [ ] T032 [P] Update `tests/unit/test_scaffold_plan.py` and `tests/unit/test_template_registry.py` ONLY IF template count or feature set changes — check whether edge-cases.md.j2 enhancement changes any counts (likely no since template name unchanged)
- [ ] T033 Run full test suite (`python -m pytest tests/ -x -q`) + ruff lint (`ruff check src/ tests/`) — verify all existing 706+ tests still pass, all new tests pass, zero lint errors. Fix any regressions
- [ ] T034 Run quickstart.md validation — create a tmp PersonalFinance manifest matching Feature 004 output, invoke `specforge edge-cases ledger-service`, verify output matches quickstart.md expectations (11 edge cases, severity breakdown, YAML parseable)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — the critical path
- **US2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1 (different test fixtures)
- **US3 (Phase 5)**: Depends on US1 (needs EdgeCaseReport to render)
- **US4 (Phase 6)**: Depends on US1 + US3 (needs analyzer + template)
- **US5 (Phase 7)**: Depends on US4 (needs enhanced phase)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P1)**: Can start after Foundational — shares analyzer module with US1 but tests use different fixtures
- **US3 (P2)**: Needs EdgeCaseReport from US1 to test template rendering
- **US4 (P2)**: Needs analyzer (US1) + template (US3) for phase integration
- **US5 (P3)**: Needs enhanced phase (US4) for CLI command

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before integration
- Core implementation before CLI integration
- Story complete before moving to next priority

### Parallel Opportunities

Within Phase 1:
- T003, T004, T005 can run in parallel (different files)

Within Phase 2 (tests):
- T006, T007, T008, T009 can ALL run in parallel (different test files)

Within Phase 3 (tests):
- T014, T015, T016 can ALL run in parallel (same file but independent test classes)

Within Phase 4 (tests):
- T019, T020 can run in parallel

---

## Parallel Example: User Story 1 (Phase 3)

```bash
# Launch all US1 tests in parallel (they all go in test_edge_case_analyzer.py but test different aspects):
Task T014: "Test dependency-based edge cases — ledger-service → identity-service"
Task T015: "Test event-based edge cases — transaction.created → analytics, notification"
Task T016: "Test data ownership, dangling refs, circular deps, budget enforcement"

# After tests fail, implement the analyzer:
Task T017: "Implement MicroserviceEdgeCaseAnalyzer"

# Then run integration test:
Task T018: "Full end-to-end PersonalFinance manifest test"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (constants + YAML files)
2. Complete Phase 2: Foundational (models, loader, filter, budget)
3. Complete Phase 3: US1 — MicroserviceEdgeCaseAnalyzer with ledger-service
4. Complete Phase 4: US2 — Monolith mode
5. **STOP and VALIDATE**: Both architectures produce correct edge cases

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. US1 → Microservice edge cases work → Test with ledger-service
3. US2 → Monolith mode works → Test with auth module
4. US3 → YAML frontmatter + template → Machine-parseable output
5. US4 → Pipeline integration → Phase 3b works
6. US5 → Standalone CLI → `specforge edge-cases` command works
7. Polish → All tests green, lint clean
