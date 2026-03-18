# Tasks: Project Status Dashboard

**Input**: Design documents from `/specs/012-project-status-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD enforced — tests written FIRST, must FAIL before implementation.

**Organization**: Tasks grouped by user story. Data logic built first; Rich terminal output built last (after all core logic is solid and tested).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/specforge/`, `tests/` at repository root
- Core domain logic in `src/specforge/core/` (zero external deps — no Rich, no Click)
- CLI layer in `src/specforge/cli/` (Rich + Click allowed)
- Templates in `src/specforge/templates/base/features/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Config constants and project scaffolding for Feature 012

- [x] T001 Add status-related constants to src/specforge/core/config.py: `STATUS_REPORT_DIR = ".specforge/reports"`, `STATUS_JSON_FILENAME = "status.json"`, `STATUS_MD_FILENAME = "status.md"`, `ORCHESTRATION_STATE_FILENAME = ".orchestration-state.json"`, `EXECUTION_STATE_FILENAME = ".execution-state.json"`, `QUALITY_REPORT_FILENAME = ".quality-report.json"`, and `ServiceOverallStatus` enum with values COMPLETE, IN_PROGRESS, PLANNING, NOT_STARTED, BLOCKED, FAILED, UNKNOWN
- [x] T002 [P] Create empty module files with docstrings for all new modules: src/specforge/core/status_models.py, src/specforge/core/status_collector.py, src/specforge/core/metrics_calculator.py, src/specforge/core/graph_builder.py, src/specforge/core/report_generator.py, src/specforge/cli/status_cmd.py, src/specforge/cli/dashboard_renderer.py

---

## Phase 2: Foundational (Data Models)

**Purpose**: Frozen dataclasses that ALL user stories depend on. Must be complete and tested before any collector/calculator work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Data Models ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] Write unit tests for all status data models in tests/unit/test_status_models.py: test LifecyclePhases frozen dataclass with all fields nullable, test ServiceStatusRecord with slug/display_name/features/lifecycle/overall_status/phase_index, test ServicePhaseDetail, test PhaseProgressRecord with index/label/services/completion_percent/status/blocked_by/service_details, test QualitySummaryRecord with all 14 fields (services_*/tasks_*/coverage_avg/docker_*/contract_*/autofix_success_rate), test GraphNode and DependencyGraph, test ProjectStatusSnapshot with all fields including has_failures and warnings. Verify all dataclasses are frozen (immutable). Verify default values for optional fields.

### Implementation for Data Models

- [x] T004 Implement all frozen dataclasses in src/specforge/core/status_models.py per data-model.md: LifecyclePhases, ServiceStatusRecord, ServicePhaseDetail, PhaseProgressRecord, QualitySummaryRecord, GraphNode, DependencyGraph, ProjectStatusSnapshot. All fields use strict type hints. Tuples for collections (not lists). All classes frozen=True.

**Checkpoint**: All data models exist and pass unit tests. Foundation ready for collector/calculator work.

---

## Phase 3: User Story 1 — Per-Service Progress Overview (Priority: P1) 🎯 MVP

**Goal**: StatusCollector reads manifest + all state files and derives per-service lifecycle status. MetricsCalculator computes overall service status using the priority waterfall from research.md R2.

**Independent Test**: Feed collector a tmp_path with manifest + varying state files (empty project, partial project, complete project). Verify correct LifecyclePhases and overall_status for each service.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Write unit tests for manifest reading in tests/unit/test_status_collector.py: test_load_manifest_returns_service_list with architecture type and feature mappings, test_load_manifest_missing_file returns Err with descriptive message, test_load_manifest_corrupt_json returns Err without crashing, test_load_manifest_empty_services returns Ok with empty service list, test_service_to_feature_mapping correctly maps services with multiple features (e.g., planning-service → ["004", "006", "007"])
- [x] T006 [P] [US1] Write unit tests for per-service state file reading in tests/unit/test_status_collector.py: test_read_pipeline_state_complete returns LifecyclePhases with spec/plan/tasks=DONE, test_read_pipeline_state_partial returns WIP for in-progress phases, test_read_pipeline_state_missing returns all-None lifecycle, test_read_pipeline_state_corrupt returns Err and warning, test_read_execution_state returns impl_percent from task completion ratio, test_read_execution_state_no_tasks returns impl_percent=0, test_read_execution_state_missing returns None impl_percent, test_read_quality_report extracts test pass/total counts, test_read_quality_report_missing returns None test counts, test_read_quality_report_docker_check extracts OK/FAIL for microservice
- [x] T007 [P] [US1] Write unit tests for overall status derivation in tests/unit/test_metrics_calculator.py: test_derive_status_no_state_files returns NOT_STARTED, test_derive_status_pipeline_in_progress returns PLANNING, test_derive_status_execution_in_progress returns IN_PROGRESS, test_derive_status_all_complete returns COMPLETE, test_derive_status_task_failed returns FAILED, test_derive_status_quality_gate_failed returns FAILED, test_derive_status_corrupt_state returns UNKNOWN, test_derive_status_blocked_by_dependency returns BLOCKED, test_derive_status_priority_waterfall (FAILED takes precedence over IN_PROGRESS). Each test constructs minimal input dataclasses and asserts the correct ServiceOverallStatus.
- [x] T008 [P] [US1] Write integration-level collector tests in tests/unit/test_status_collector.py: test_collect_empty_project (manifest exists, no service state files — all services NOT_STARTED), test_collect_partial_project (3 services: one complete, one in-progress, one not-started), test_collect_complete_project (all services fully complete with quality reports), test_collect_corrupt_state_file (one service has invalid JSON — shows UNKNOWN, others still correct), test_collect_no_manifest (returns Err), test_collect_single_service_project (1-service monolith — simplest boundary, verify no crash and correct snapshot shape), test_collect_large_project_15_services (15 services with mixed states — verify all 15 appear in snapshot, no duplication, no truncation), test_collect_execution_state_zero_tasks (service has execution state with empty tasks array — impl_percent must be 0, not division-by-zero error). Each test creates a realistic tmp_path directory with manifest.json and state files.

### Implementation for User Story 1

- [x] T009 [US1] [FR-001, FR-013, FR-014] Implement manifest reading in src/specforge/core/status_collector.py: `load_manifest(project_root: Path) -> Result[ManifestData, str]` function that reads `.specforge/manifest.json`, extracts architecture type, service list with slugs/names, feature mappings, and service communication (dependency) data. Returns `Err` for missing/corrupt files. Define `ManifestData` frozen dataclass to hold the extracted fields. This subsumes FR-014 (integrate with pipeline-status data sources) since all data sources are the same manifest + state files already used by pipeline-status.
- [x] T010 [US1] Implement per-service state file reading in src/specforge/core/status_collector.py: `read_service_states(features_dir: Path, slug: str) -> ServiceRawState` that reads `.pipeline-state.json`, `.execution-state.json`, and `.quality-report.json` from the service directory. Each read returns `Result[dict, str]`. `ServiceRawState` holds 3 Result fields. Map pipeline phase statuses (spec/plan/tasks from 7-phase pipeline) to LifecyclePhases fields. Calculate impl_percent from execution task completion ratio. Extract test counts and docker status from quality report.
- [x] T011 [US1] Implement overall status derivation in src/specforge/core/metrics_calculator.py: `derive_service_status(raw: ServiceRawState, dependencies_met: bool) -> ServiceOverallStatus` implementing the priority waterfall from research.md R2: (1) corrupt → UNKNOWN, (2) failed tasks/quality → FAILED, (3) deps incomplete → BLOCKED, (4) execution in-progress → IN_PROGRESS, (5) pipeline in-progress → PLANNING, (6) all complete → COMPLETE, (7) no state → NOT_STARTED.
- [x] T012 [US1] Implement the top-level collect function in src/specforge/core/status_collector.py: `collect_project_status(project_root: Path) -> Result[ProjectStatusSnapshot, str]` that orchestrates: load manifest → read all service states → derive statuses → assemble ServiceStatusRecords → return snapshot with warnings for any Err states. This is the single entry point used by all downstream consumers.

**Checkpoint**: `collect_project_status()` correctly reads and derives status for empty/partial/complete projects. All 4 test files pass. MVP data layer complete.

---

## Phase 4: User Story 2 — Phase Progress Visualization (Priority: P1)

**Goal**: Calculate phase progress percentages from orchestration state + per-service status.

**Independent Test**: Feed calculator orchestration state with 3 phases at different completion levels. Verify correct percentages and blocked_by detection.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US2] Write unit tests for phase progress in tests/unit/test_metrics_calculator.py: test_calculate_phase_progress_all_complete returns 100%, test_calculate_phase_progress_partial returns weighted average, test_calculate_phase_progress_blocked identifies blocked_by phase index, test_calculate_phase_progress_no_orchestration_state returns empty phases tuple, test_calculate_phase_progress_monolith returns empty phases (no phased execution), test_phase_service_details_lists_per_service_status for parenthetical notes, test_calculate_phase_progress_not_started_services_reduce_percent (phase with 3 services, 2 NOT_STARTED — weighted average must be ~33% not 100%), test_calculate_phase_progress_multi_feature_service_no_double_count (planning-service with features 004+006+007 counts as 1 service in phase calculation, not 3)

### Implementation for User Story 2

- [x] T014 [US2] Implement orchestration state reading in src/specforge/core/status_collector.py: `read_orchestration_state(project_root: Path) -> Result[dict, str]` that reads `.specforge/.orchestration-state.json` and extracts phase definitions with service assignments
- [x] T015 [US2] Implement phase progress calculation in src/specforge/core/metrics_calculator.py: `calculate_phase_progress(orchestration: dict | None, service_statuses: dict[str, ServiceStatusRecord]) -> tuple[PhaseProgressRecord, ...]` that computes per-phase completion using weighted average (research.md R3), determines blocked_by from prerequisite phase status, and builds ServicePhaseDetail tuples for each phase
- [x] T016 [US2] Wire phase progress into `collect_project_status()` in src/specforge/core/status_collector.py: read orchestration state (if exists), pass to metrics_calculator, include PhaseProgressRecords in the returned ProjectStatusSnapshot

**Checkpoint**: Phase progress correctly identifies blocked dependencies. Empty/missing orchestration state handled gracefully.

---

## Phase 5: User Story 3 — Quality Summary Dashboard (Priority: P2)

**Goal**: Aggregate quality metrics across all services into QualitySummaryRecord.

**Independent Test**: Feed calculator a mix of services (some with quality reports, some without). Verify correct aggregation and architecture-specific metric filtering.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T017 [P] [US3] Write unit tests for quality aggregation in tests/unit/test_metrics_calculator.py: test_aggregate_quality_service_counts_by_status (verify all 7 status counters sum to services_total — COMPLETE, IN_PROGRESS, PLANNING, NOT_STARTED, BLOCKED, FAILED, UNKNOWN), test_aggregate_quality_task_counts from execution states, test_aggregate_quality_coverage_average excludes services without data, test_aggregate_quality_docker_metrics_microservice_only, test_aggregate_quality_docker_metrics_none_for_monolith, test_aggregate_quality_contract_results, test_aggregate_quality_autofix_rate from fix_attempts, test_aggregate_quality_no_reports returns zero counts with None for optional metrics, test_has_failures_true_when_any_failed, test_has_failures_false_when_none_failed, test_aggregate_quality_multi_task_level_reports_merged (multiple task-level QualityReports for one service — union check_results, AND passed values)

### Implementation for User Story 3

- [x] T018 [US3] Implement quality aggregation in src/specforge/core/metrics_calculator.py: `aggregate_quality(services: tuple[ServiceStatusRecord, ...], architecture: str, raw_states: dict) -> QualitySummaryRecord` that counts services by status, sums task counts from execution states, computes average coverage from quality reports (excluding services without data), computes Docker/contract metrics only for microservice architecture (None for others), and computes autofix success rate from fix_attempts
- [x] T019 [US3] Implement `has_failures` computation in src/specforge/core/metrics_calculator.py: `compute_has_failures(services: tuple[ServiceStatusRecord, ...]) -> bool` that returns True if any service has overall_status == FAILED
- [x] T020 [US3] Wire quality aggregation into `collect_project_status()` in src/specforge/core/status_collector.py: pass collected data to quality aggregation, include QualitySummaryRecord and has_failures in ProjectStatusSnapshot

**Checkpoint**: Quality metrics correctly aggregate with architecture-aware filtering. Missing data produces None, not crashes.

---

## Phase 6: User Story 4 + 5 — Reports: Markdown & JSON (Priority: P2)

**Goal**: Generate `.specforge/reports/status.md` via Jinja2 template and `.specforge/reports/status.json` matching the JSON schema contract.

**Independent Test**: Feed report_generator a ProjectStatusSnapshot and verify: (1) JSON output validates against contracts/status-json-schema.json, (2) markdown contains all sections, (3) NOT_STARTED services have null lifecycle fields in JSON.

### Tests for User Stories 4 & 5 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T021 [P] [US5] Write unit tests for JSON report in tests/unit/test_report_generator.py: test_generate_json_valid_schema (output validates against contracts/status-json-schema.json), test_generate_json_not_started_service_null_fields (all lifecycle fields null, status NOT_STARTED, impl_percent 0), test_generate_json_complete_service_all_fields_populated, test_generate_json_creates_reports_dir, test_generate_json_overwrites_existing, test_generate_json_includes_timestamp, test_generate_json_includes_warnings_array, test_generate_json_phases_ordered_by_index
- [x] T022 [P] [US4] Write unit tests for markdown report in tests/unit/test_report_generator.py: test_generate_markdown_contains_architecture_badge, test_generate_markdown_contains_service_table, test_generate_markdown_contains_phase_progress_bars, test_generate_markdown_contains_quality_summary, test_generate_markdown_progress_bar_format (text-based e.g. `[========  ] 80%`), test_generate_markdown_creates_reports_dir, test_generate_markdown_includes_timestamp
- [x] T023 [P] [US4] Write snapshot test for markdown template rendering in tests/snapshots/test_status_report_snapshot.py: create a representative ProjectStatusSnapshot fixture (microservice, 3 services at different states, 2 phases) and snapshot the rendered markdown output

### Implementation for User Stories 4 & 5

- [x] T024 [US5] Implement JSON report generation in src/specforge/core/report_generator.py: `generate_json_report(snapshot: ProjectStatusSnapshot, output_dir: Path) -> Result[Path, str]` that serializes ProjectStatusSnapshot to JSON matching the status-json-schema.json contract. Uses `_snapshot_to_dict()` helper for serialization. NOT_STARTED services have all lifecycle fields as None→null. Creates reports dir if needed. Uses atomic write pattern (tempfile + os.replace).
- [x] T025 [US4] Create Jinja2 markdown template in src/specforge/templates/base/features/status-report.md.j2: template receives the full snapshot and renders architecture badge, service table (with `|` delimited markdown table), text-based phase progress bars, quality summary section, timestamp header. Uses Jinja2 loops for services/phases and conditional blocks for architecture-specific sections.
- [x] T026 [US4] Implement markdown report generation in src/specforge/core/report_generator.py: `generate_markdown_report(snapshot: ProjectStatusSnapshot, output_dir: Path) -> Result[Path, str]` that renders status-report.md.j2 with the snapshot as context. Uses the existing TemplateRenderer from src/specforge/core/template_renderer.py. Creates reports dir if needed. Uses atomic write pattern.

**Checkpoint**: Both reports generate correctly. JSON validates against schema. Markdown renders in GitHub viewer. Snapshot test captures baseline.

---

## Phase 7: User Story 6 — Dependency Graph (Priority: P3)

**Goal**: Build dependency graph from manifest and render as ASCII art and Mermaid syntax.

**Independent Test**: Feed graph_builder a manifest with 3 phases and verify ASCII output contains status-labeled nodes and Mermaid output is valid `graph TD` syntax.

### Tests for User Story 6 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T027 [P] [US6] Write unit tests for graph building in tests/unit/test_graph_builder.py: test_build_graph_from_manifest creates correct GraphNode topology with dependencies, test_build_graph_annotates_status from service statuses, test_render_ascii_contains_status_labels (✓/~/✗/○/!), test_render_ascii_phase_layers groups services by phase, test_render_mermaid_valid_syntax produces graph TD block, test_render_mermaid_status_styles uses class annotations for done/in-progress/blocked/failed, test_build_graph_no_dependencies returns independent nodes, test_build_graph_monolith_flat returns nodes without edges

### Implementation for User Story 6

- [x] T028 [US6] Implement graph construction in src/specforge/core/graph_builder.py: `build_dependency_graph(manifest_data: ManifestData, service_statuses: dict[str, str]) -> DependencyGraph` that extracts service dependencies from manifest communication patterns, creates GraphNode per service with status annotation, groups nodes into phase_groups
- [x] T029 [US6] Implement ASCII renderer in src/specforge/core/graph_builder.py: `render_ascii(graph: DependencyGraph) -> str` that renders phase layers with service boxes labeled by status indicators (✓ complete, ~ in-progress, ✗ failed, ○ not-started, ! blocked)
- [x] T030 [US6] Implement Mermaid renderer in src/specforge/core/graph_builder.py: `render_mermaid(graph: DependencyGraph) -> str` that outputs valid Mermaid `graph TD` syntax with styled node classes for each status
- [x] T031 [US6] Wire graph building into `collect_project_status()` in src/specforge/core/status_collector.py: build DependencyGraph from manifest data and service statuses, include in ProjectStatusSnapshot

**Checkpoint**: Graph correctly represents service dependencies with status annotations. Both ASCII and Mermaid output verified.

---

## Phase 8: User Story 1+2+3 Terminal Rendering — Rich Dashboard (Priority: P1)

**Purpose**: Rich terminal rendering built LAST after all data logic is solid and tested.

**Goal**: Dashboard renders the ProjectStatusSnapshot as a Rich terminal dashboard with architecture-adaptive columns, phase progress bars, and quality summary panel.

**Independent Test**: Run `specforge status` via CliRunner on a tmp_path project with 3 services. Verify output contains architecture badge, table rows, phase bars.

### Tests for Terminal Dashboard ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T032 [P] Write unit tests for dashboard rendering in tests/unit/test_dashboard_renderer.py (import from specforge.cli.dashboard_renderer): test_render_badge_microservice outputs [MICROSERVICE], test_render_badge_monolith outputs [MONOLITH], test_render_badge_modular outputs [MODULAR], test_render_service_table_microservice_includes_docker_column, test_render_service_table_monolith_omits_docker_column, test_render_service_table_modular_includes_boundary_column, test_render_service_table_not_started_shows_dashes, test_render_phase_progress_bars, test_render_quality_summary_panel, test_render_quality_summary_omits_docker_for_monolith, test_render_graph_ascii uses Rich Tree, test_render_service_table_single_service (1 service — verify table renders without crash), test_render_service_table_15_services (15 services — verify all rows present, no truncation, reasonable formatting)

### Implementation for Terminal Dashboard

- [x] T033 Implement badge rendering in src/specforge/cli/dashboard_renderer.py: `render_badge(console: Console, architecture: str) -> None` using rich.panel.Panel with centered architecture badge text, styled by architecture type
- [x] T034 Implement service table rendering in src/specforge/cli/dashboard_renderer.py: `render_service_table(console: Console, snapshot: ProjectStatusSnapshot) -> None` using rich.table.Table with architecture-adaptive columns (Docker for microservice, boundary for modular-monolith, neither for monolith). Status cells styled using existing `_status_style()` pattern from pipeline_status_cmd.py. NOT_STARTED services show "-" for empty fields.
- [x] T035 Implement phase progress rendering in src/specforge/cli/dashboard_renderer.py: `render_phase_progress(console: Console, phases: tuple[PhaseProgressRecord, ...]) -> None` using rich.progress.ProgressBar per phase with completion percentage and service detail notes. Blocked phases show "blocked by Phase N" in dim style.
- [x] T036 Implement quality summary rendering in src/specforge/cli/dashboard_renderer.py: `render_quality_summary(console: Console, quality: QualitySummaryRecord, architecture: str) -> None` using rich.panel.Panel with key-value metrics. Failed counts highlighted in red. Docker/contract metrics omitted for non-microservice. "No data" for None values.
- [x] T037 Implement graph rendering in src/specforge/cli/dashboard_renderer.py: `render_graph(console: Console, graph: DependencyGraph, graph_text: str) -> None` that prints the pre-rendered ASCII graph text (from graph_builder) using Console.print()
- [x] T038 Implement top-level render function in src/specforge/cli/dashboard_renderer.py: `render_dashboard(console: Console, snapshot: ProjectStatusSnapshot, show_graph: bool = False) -> None` that calls render_badge → render_service_table → render_phase_progress (if phases exist) → render_quality_summary → render_graph (if show_graph). Single entry point for the CLI command.

**Checkpoint**: Rich terminal dashboard displays all sections with architecture-adaptive columns. Visual output verified.

---

## Phase 9: User Story 7 — Watch Mode (Priority: P3)

**Goal**: `--watch` flag auto-refreshes the terminal dashboard at configurable intervals.

**Independent Test**: Verify that `--watch` with `--format markdown` produces an error. Verify watch loop can be interrupted.

### Tests for User Story 7 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T039 [P] [US7] Write integration tests for watch mode in tests/integration/test_status_cmd.py: test_watch_rejects_format_markdown (exits with error message), test_watch_rejects_format_json (exits with error message), test_watch_default_interval_is_5

### Implementation for User Story 7

- [x] T040 [US7] Implement watch mode in src/specforge/cli/status_cmd.py: when `--watch` flag is set and format is terminal-only, use `rich.live.Live` context with a loop: collect → render → sleep(interval). Exit on KeyboardInterrupt or when all services reach terminal state (COMPLETE or FAILED). Validate --watch incompatibility with --format markdown/json at option parsing time.

**Checkpoint**: Watch mode refreshes correctly and rejects incompatible format options.

---

## Phase 10: CLI Wiring & Integration Tests

**Purpose**: Wire everything together in the Click command and run end-to-end integration tests.

### Tests ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T041 [P] Write integration tests for CLI command in tests/integration/test_status_cmd.py: test_status_no_project (error message, non-zero exit), test_status_no_manifest (suggests specforge decompose), test_status_empty_project_all_not_started, test_status_partial_project_mixed_statuses, test_status_complete_project, test_status_format_json_creates_file, test_status_format_markdown_creates_file, test_status_format_both_creates_both_files, test_status_graph_flag_shows_graph, test_status_exit_code_0_no_failures, test_status_exit_code_1_with_failures, test_status_corrupt_state_shows_unknown_with_warning, test_status_single_service_project (1-service — full pipeline end-to-end), test_status_large_project_15_services (15 services — verify dashboard renders, JSON output has 15 entries, markdown has 15 rows). All tests use CliRunner + tmp_path with realistic state file fixtures.

### Implementation

- [x] T042 Implement Click command in src/specforge/cli/status_cmd.py: `@click.command("status")` with options `--format` (multiple, type=click.Choice(["terminal", "markdown", "json"]), default=["terminal"]), `--graph` (flag), `--watch` (flag), `--interval` (int, default=5). Wire: validate options → collect_project_status() → if terminal: render_dashboard() → if markdown: generate_markdown_report() → if json: generate_json_report() → if graph: include graph in renders → sys.exit(1) if has_failures.
- [x] T043 Register status command in src/specforge/cli/main.py: add `from specforge.cli.status_cmd import status` and `cli.add_command(status)` to the Click group

**Checkpoint**: Full end-to-end CLI works. All integration tests pass. Exit codes correct.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all modules

- [x] T044 [P] Run ruff linter across all new files and fix any violations: src/specforge/core/status_models.py, src/specforge/core/status_collector.py, src/specforge/core/metrics_calculator.py, src/specforge/core/graph_builder.py, src/specforge/core/report_generator.py, src/specforge/cli/status_cmd.py, src/specforge/cli/dashboard_renderer.py
- [x] T045 [P] Verify all functions have strict type hints and no function exceeds 30 lines, no class exceeds 200 lines per constitution III
- [x] T046 [P] Run full test suite with coverage: `pytest tests/unit/test_status_*.py tests/unit/test_metrics_calculator.py tests/unit/test_graph_builder.py tests/unit/test_report_generator.py tests/unit/test_dashboard_renderer.py tests/integration/test_status_cmd.py tests/snapshots/test_status_report_snapshot.py --cov=specforge.core.status_models --cov=specforge.core.status_collector --cov=specforge.core.metrics_calculator --cov=specforge.core.graph_builder --cov=specforge.core.report_generator --cov-report=term-missing` and ensure 100% coverage on core modules. Additionally, include a performance smoke test: test_collect_20_services_under_3_seconds (SC-001 validation — create 20-service fixture, time collect_project_status, assert < 3 seconds)
- [x] T047 Run quickstart.md validation: execute the commands from specs/012-project-status-dashboard/quickstart.md against a test project to verify documentation accuracy

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS US2, US3, US4+5, US6 (all need collector)
- **US2 (Phase 4)**: Depends on Phase 3 (extends collector + calculator)
- **US3 (Phase 5)**: Depends on Phase 3 (extends collector + calculator). Can parallel with US2.
- **US4+5 (Phase 6)**: Depends on Phase 3 (consumes snapshot). Can parallel with US2/US3.
- **US6 (Phase 7)**: Depends on Phase 3 (consumes manifest + statuses). Can parallel with US2/US3/US4+5.
- **Rich Dashboard (Phase 8)**: Depends on Phases 3, 4, 5, 7 (needs all snapshot data for rendering)
- **US7 Watch (Phase 9)**: Depends on Phase 8 (needs dashboard_renderer)
- **CLI Wiring (Phase 10)**: Depends on Phases 6, 8, 9 (needs all components)
- **Polish (Phase 11)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Foundation only — no dependencies on other stories. **This is the MVP.**
- **US2 (P1)**: Extends US1's collector and calculator — sequential after US1
- **US3 (P2)**: Extends US1's collector and calculator — can parallel with US2
- **US4+5 (P2)**: Consumes US1's snapshot — can parallel with US2/US3
- **US6 (P3)**: Consumes US1's manifest data — can parallel with US2/US3/US4+5
- **US7 (P3)**: Requires Rich dashboard (Phase 8) — sequential after dashboard

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/dataclasses before functions that use them
- Pure calculation functions before integration wiring
- Core domain logic before CLI layer

### Parallel Opportunities

- T002 can parallel with T001 (different files)
- T005, T006, T007, T008 can ALL run in parallel (separate test files/concerns)
- After Phase 3 completes: US2, US3, US4+5, US6 can start in parallel
- T021, T022, T023 can run in parallel (different test files)
- T027 can parallel with T021/T022/T023
- T032 can parallel with T039
- T044, T045, T046 can run in parallel (different concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test tasks together:
Task T005: "Unit tests for manifest reading in tests/unit/test_status_collector.py"
Task T006: "Unit tests for per-service state file reading in tests/unit/test_status_collector.py"
Task T007: "Unit tests for overall status derivation in tests/unit/test_metrics_calculator.py"
Task T008: "Integration-level collector tests in tests/unit/test_status_collector.py"

# Then implement sequentially:
Task T009: "Implement manifest reading" (foundation for T010)
Task T010: "Implement per-service state file reading" (depends on T009)
Task T011: "Implement overall status derivation" (can parallel with T010)
Task T012: "Implement top-level collect function" (depends on T009, T010, T011)
```

## Parallel Example: After Phase 3

```bash
# These can all start simultaneously after US1 (Phase 3) is complete:
Phase 4 (US2): T013 → T014 → T015 → T016
Phase 5 (US3): T017 → T018 → T019 → T020
Phase 6 (US4+5): T021/T022/T023 → T024 → T025 → T026
Phase 7 (US6): T027 → T028 → T029 → T030 → T031
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Data Models (T003–T004)
3. Complete Phase 3: StatusCollector + MetricsCalculator (T005–T012)
4. **STOP and VALIDATE**: All unit tests pass. Collector handles empty/partial/complete/corrupt projects.
5. Jump to Phase 8 (T032–T038) + Phase 10 (T041–T043) for minimal terminal output
6. **MVP DELIVERED**: `specforge status` shows per-service table

### Incremental Delivery

1. Setup + Foundational + US1 → MVP terminal dashboard ✓
2. Add US2 (phase progress) → Phase bars appear in dashboard ✓
3. Add US3 (quality metrics) → Quality panel appears ✓
4. Add US4+US5 (reports) → --format markdown/json work ✓
5. Add US6 (graph) → --graph works ✓
6. Add US7 (watch) → --watch works ✓
7. Each story adds value without breaking previous stories

### Data-First Strategy (User's Instruction)

All core domain logic (collector, calculator, graph builder, report generator) is built and tested BEFORE any Rich terminal rendering. This ensures:
- Data correctness is verified independently of presentation
- Rich rendering bugs cannot mask data bugs
- Report generation (JSON/markdown) can ship before terminal polish
- Each core module has 100% test coverage before CLI integration

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- StatusCollector is the CRITICAL path — test exhaustively with empty/partial/complete/corrupt scenarios
- Rich terminal output built LAST per user instruction — data logic must be solid first

