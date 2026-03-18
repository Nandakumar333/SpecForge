# Implementation Plan: Project Status Dashboard

**Branch**: `012-project-status-dashboard` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-project-status-dashboard/spec.md`

## Summary

Build `specforge status` — a single CLI command that reads the project manifest, all per-service state files (pipeline, execution, quality), and orchestration state to produce a comprehensive project progress dashboard. Outputs to Rich terminal (default), markdown file, and/or JSON file. Adapts columns and metrics to the detected architecture type (microservice/monolith/modular-monolith).

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal rendering — Table, Panel, Progress, Tree), Jinja2 3.x (markdown report template)  
**Storage**: File system — `.specforge/manifest.json`, `.specforge/features/<slug>/` state files, `.specforge/.orchestration-state.json`  
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)  
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)  
**Project Type**: CLI tool  
**Performance Goals**: < 3 seconds for projects with up to 20 services (SC-001)  
**Constraints**: Core domain modules in `core/` must have zero external dependencies (Rich prohibited in core layer). All file output via Jinja2 templates — no string concatenation.  
**Scale/Scope**: Reads up to ~80 JSON files (20 services × 4 state files per service) per invocation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md + clarifications complete before plan |
| II. Architecture | ✅ PASS | Domain models + logic in `core/` (zero external deps). Rich rendering isolated in `cli/`. All file output via Jinja2 templates. |
| III. Code Quality | ✅ PASS | Strict type hints, ≤30-line functions, ≤200-line classes, `Result[T]` for recoverable errors, constants in `config.py`, constructor injection |
| IV. Testing | ✅ PASS | TDD: tests written before implementation. Unit tests for all `core/` modules, integration tests for CLI with `CliRunner` + `tmp_path`, snapshot tests for report rendering |
| V. Commit Strategy | ✅ PASS | Conventional Commits, one commit per task |
| VI. File Structure | ✅ PASS | `cli/status_cmd.py`, `core/status_*.py`, `templates/base/features/status-report.md.j2` |
| VII. Governance | ✅ PASS | Constitution supersedes all. No conflicts detected. |

No violations. Complexity Tracking table not needed.

## Project Structure

### Documentation (this feature)

```text
specs/012-project-status-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── status-json-schema.json
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── status_cmd.py              # Click command: specforge status
│   └── dashboard_renderer.py      # Rich terminal rendering (Table, Panel, Progress, Tree)
├── core/
│   ├── status_models.py           # Frozen dataclasses: ProjectStatusSnapshot, ServiceStatusRecord, etc.
│   ├── status_collector.py        # Reads manifest + all state files → ProjectStatusSnapshot
│   ├── metrics_calculator.py      # Pure aggregation: completion %, coverage avg, fix rate
│   ├── graph_builder.py           # Dependency graph topology + ASCII/Mermaid text serialization
│   └── report_generator.py        # Writes status.json (json.dumps) + status.md (Jinja2)
├── templates/
│   └── base/
│       └── features/
│           └── status-report.md.j2  # Markdown report template
tests/
├── unit/
│   ├── test_status_models.py
│   ├── test_status_collector.py
│   ├── test_metrics_calculator.py
│   ├── test_graph_builder.py
│   └── test_report_generator.py
├── integration/
│   └── test_status_cmd.py
└── snapshots/
    └── test_status_report_snapshot.py
```

**Structure Decision**: Follows existing SpecForge single-project layout. Domain logic (`status_models.py`, `status_collector.py`, `metrics_calculator.py`, `graph_builder.py`, `report_generator.py`) in `core/` with zero Rich dependency. CLI layer (`status_cmd.py`, `dashboard_renderer.py`) owns Rich rendering. This mirrors the existing separation where `pipeline_status_cmd.py` uses Rich directly while `pipeline_state.py` is a pure model.

## Module Responsibilities

### `core/status_models.py` — Data Models
Frozen dataclasses forming the internal representation. Architecture-agnostic data structures that all downstream modules operate on. Key types:
- `LifecyclePhases` — per-service spec/plan/tasks/impl/test/docker status
- `ServiceStatusRecord` — one service's full status + features + overall label
- `PhaseProgressRecord` — one execution phase's aggregate completion
- `QualitySummaryRecord` — project-wide aggregated quality metrics
- `ProjectStatusSnapshot` — top-level container backing all three output formats

### `core/status_collector.py` — State File Reader
Reads `manifest.json` to get the service list, architecture type, dependency graph, and feature mappings. Then reads each service's `.pipeline-state.json`, `.execution-state.json`, and `.quality-report.json` from `.specforge/features/<slug>/`. Also reads `.specforge/.orchestration-state.json` for phase data. Returns raw collected data (no derived calculations). Uses `Result[T]` for each file read — corrupted/missing files produce `Err` that maps to `UNKNOWN` status.

### `core/metrics_calculator.py` — Aggregation Engine
Pure functions that compute derived metrics from raw collected data:
- Overall service status (COMPLETE / IN PROGRESS / PLANNING / NOT STARTED / BLOCKED / FAILED)
- Phase completion percentages from service statuses within each phase
- Quality aggregations: task counts, coverage averages, Docker/contract summaries, auto-fix rates
- `has_failures` flag for exit code determination

### `core/graph_builder.py` — Dependency Graph
Builds a directed acyclic graph from manifest service dependencies. Annotates nodes with status from the snapshot. Serializes to ASCII art (for terminal) and Mermaid syntax (for markdown). No Rich dependency — outputs plain strings.

### `core/report_generator.py` — File Output
Writes `.specforge/reports/status.json` (via `json.dumps` with the contracts schema) and `.specforge/reports/status.md` (via Jinja2 template `status-report.md.j2`). Creates reports directory if needed. Uses atomic writes (existing `os.replace()` pattern).

### `cli/status_cmd.py` — Click Entry Point
Registers `specforge status` command with options: `--format` (multiple, default `terminal`), `--graph`, `--watch`, `--interval`. Wires together collector → calculator → renderer/generator. Sets exit code 1 if `has_failures`. Validates option combinations (--watch incompatible with file formats).

### `cli/dashboard_renderer.py` — Rich Terminal Renderer
Receives a `ProjectStatusSnapshot` and renders it using Rich:
- `render_badge()` — architecture badge via `rich.panel.Panel`
- `render_service_table()` — `rich.table.Table` with architecture-adaptive columns
- `render_phase_progress()` — `rich.progress.Progress` bars per phase
- `render_quality_summary()` — `rich.panel.Panel` with key metrics
- `render_graph()` — `rich.tree.Tree` for ASCII dependency visualization
Each function takes the snapshot + `Console` — no global state.

## Key Design Decisions

1. **Manifest-authoritative service list**: All services come from `manifest.json`. No filesystem scanning. Services without any state files → `NOT_STARTED`.

2. **Architecture-adaptive columns**: `dashboard_renderer.py` checks `snapshot.architecture` to decide which columns to include. Microservice adds Docker + contract columns. Modular-monolith adds boundary compliance column. Monolith uses the minimal set.

3. **Graceful degradation**: Each state file read returns `Result[T]`. `Err` values produce `UNKNOWN` status for that service + a warning appended to the snapshot. The collector never raises for missing/corrupt state.

4. **Exit code contract**: `status_cmd.py` checks `snapshot.has_failures` (computed by `metrics_calculator`) and calls `sys.exit(1)` if true. Terminal/file output always completes before exit.

5. **Watch mode**: `status_cmd.py` implements a simple loop: collect → render → sleep(interval) → clear → repeat. Exits on Ctrl+C (KeyboardInterrupt) or when all services reach terminal state. Rich `Live` context manager handles screen clearing.

6. **JSON null-field contract**: Services with no artifacts have all lifecycle fields set to `null` in JSON, `status: "NOT_STARTED"`, `implementation_percent: 0`. This is enforced by `report_generator.py`'s serialization logic matching the `status-json-schema.json` contract.

## Constitution Re-Check (Post-Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | All design traceable to spec FR-001 through FR-018 |
| II. Architecture | ✅ PASS | Core modules have zero Rich/Click imports. Jinja2 used only for file generation (constitutionally mandated). Plugin boundary not crossed. |
| III. Code Quality | ✅ PASS | All modules ≤200 lines estimated. Functions decomposed to ≤30 lines. Type hints on all signatures. Result[T] for file I/O. Constants in config.py. |
| IV. Testing | ✅ PASS | TDD with unit tests per core module, integration tests for CLI, snapshot tests for template rendering. |
| V. Commit Strategy | ✅ PASS | One commit per task, conventional commit format. |
| VI. File Structure | ✅ PASS | All new files placed in correct architectural layers. No cross-layer imports from core→cli. |
| VII. Governance | ✅ PASS | No conflicts with constitution. |
