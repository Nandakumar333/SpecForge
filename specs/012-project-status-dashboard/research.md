# Research: Project Status Dashboard

**Feature**: `012-project-status-dashboard`  
**Date**: 2026-03-18

## Research Tasks

### R1: State File Reading Strategy

**Decision**: Sequential reads with per-file `Result[T]` error handling

**Rationale**: Each service has up to 4 state files (`.pipeline-state.json`, `.execution-state.json`, `.quality-report.json`, and the shared `.orchestration-state.json`). For 20 services that's ~80 file reads. Sequential I/O with `pathlib.Path.read_text()` is sufficient to meet the <3s performance target since each file is <10KB and modern SSDs handle 80 small reads in <100ms. Async I/O would add complexity without measurable benefit at this scale.

**Alternatives considered**:
- `asyncio` + `aiofiles`: Rejected — adds external dependency and complexity for negligible gain at 80 files.
- `concurrent.futures.ThreadPoolExecutor`: Rejected — threading overhead exceeds I/O time for small files on local disk.

### R2: Overall Service Status Computation

**Decision**: Deterministic status derivation from lifecycle phases using priority-ordered rules

**Rationale**: The overall status for each service (COMPLETE, IN PROGRESS, PLANNING, NOT STARTED, BLOCKED, FAILED, UNKNOWN) must be derived deterministically from the combination of pipeline state, execution state, and quality report. The derivation follows a priority waterfall:

1. If any state file is unreadable → **UNKNOWN**
2. If execution state has any task with `status == "failed"` or quality gate `passed == false` → **FAILED**
3. If orchestration state shows this service's dependencies are incomplete → **BLOCKED**
4. If execution state has tasks with `status == "in-progress"` or `"completed"` (mix) → **IN PROGRESS**
5. If pipeline state has any phase `status == "in-progress"` and no execution state → **PLANNING**
6. If all pipeline phases `status == "complete"` AND all execution tasks `status == "completed"` AND quality gate `passed == true` → **COMPLETE**
7. If no pipeline state exists → **NOT STARTED**

**Alternatives considered**:
- Status stored in a dedicated status file per service: Rejected — adds write coupling. Status is always derivable from existing state files.
- Status stored in orchestration state only: Rejected — orchestration state may not exist (e.g., before `implement --all` is run).

### R3: Phase Progress Calculation

**Decision**: Weighted average of service completion within each phase

**Rationale**: Phase completion percentage is calculated as the average of per-service completion within that phase. Per-service completion is a composite score:
- Pipeline phases complete (spec through tasks): 0–40% (each of 7 phases = ~5.7%)
- Implementation tasks complete: 40–90% (`tasks_completed / tasks_total * 50`)
- Quality gate passed: 90–100%

This weighting reflects the lifecycle flow: planning is 40% of work, implementation is 50%, quality validation is 10%.

**Alternatives considered**:
- Simple binary (all services COMPLETE = 100%, else proportional): Rejected — doesn't reflect partial progress within services.
- Task-count only: Rejected — ignores planning phases which are significant work.

### R4: Rich Terminal Rendering Patterns

**Decision**: Use `rich.table.Table` for service grid, `rich.progress.ProgressBar` for phase bars, `rich.panel.Panel` for quality summary, `rich.tree.Tree` for dependency graph

**Rationale**: These are the established Rich patterns already used in SpecForge:
- `check_cmd.py` uses `Table` for prerequisite status
- `pipeline_status_cmd.py` uses `Table` with styled status cells
- `decompose_cmd.py` uses `Panel` for architecture selection

The `Progress` widget renders inline progress bars without requiring a live context. `Tree` renders hierarchical dependency data as indented ASCII — no external graph library needed.

**Alternatives considered**:
- `rich.layout.Layout` for multi-panel dashboard: Rejected — Layout requires `Live` context for all output, overcomplicating the one-shot display case.
- `rich.columns.Columns` for side-by-side panels: Rejected — terminal width constraints make single-column stack more reliable across different terminal sizes.

### R5: Markdown Report Generation

**Decision**: Jinja2 template (`status-report.md.j2`) with the `ProjectStatusSnapshot` dataclass as context

**Rationale**: Constitution mandates "All file generation MUST use Jinja2 templates." The template receives the full snapshot object and renders tables using Jinja2 loops and filters. Progress bars are text-based: `[========  ] 80%`. Status labels use bold markdown syntax.

**Alternatives considered**:
- Direct string formatting in Python: Rejected — violates constitution (no string concatenation for output files).
- Rich `Console.export_text()` piped to file: Rejected — loses markdown semantics (tables become fixed-width text).

### R6: JSON Schema for CI/CD Contract

**Decision**: Explicit JSON schema (`status-json-schema.json`) defining the `status.json` output structure

**Rationale**: FR-018 requires that services with no artifacts have all lifecycle fields set to `null` (not omitted). A formal schema makes this contract explicit and testable. CI/CD consumers can validate the JSON against the schema. The schema is stored in `contracts/` as a project artifact.

**Alternatives considered**:
- No schema, just documented examples: Rejected — examples don't enforce null-field requirements or catch regressions.
- JSON-LD or OpenAPI: Rejected — overkill for a single file output; JSON Schema is the right tool for validating JSON documents.

### R7: Watch Mode Implementation

**Decision**: Simple poll loop with `rich.live.Live` context manager

**Rationale**: `--watch` mode uses a `while True` loop: collect → build snapshot → render into `Live` context → `time.sleep(interval)`. `Live` handles screen clearing and redrawing automatically. The loop exits on `KeyboardInterrupt` or when `all(s.overall_status in ("COMPLETE", "FAILED") for s in snapshot.services)`.

**Alternatives considered**:
- `watchdog` filesystem monitoring: Rejected — adds external dependency and doesn't work well with atomic writes (temp file → rename triggers multiple events).
- Signal-based refresh (SIGUSR1): Rejected — not cross-platform (Windows incompatible).

### R8: Dependency Graph ASCII Rendering

**Decision**: Custom layered ASCII renderer using phase groupings

**Rationale**: Services are already grouped into phases by the orchestration state. The ASCII graph renders phases as horizontal layers with services as labeled boxes, connected by edges to their dependencies in prior phases. Status is indicated by labels: `[✓]` complete, `[~]` in progress, `[✗]` failed, `[○]` not started, `[!]` blocked. This approach is simpler than a general graph layout algorithm and leverages the existing phase structure.

For Mermaid output, the same topology is serialized as a `graph TD` block with styled nodes.

**Alternatives considered**:
- `graphviz` Python bindings: Rejected — external dependency, requires system-level graphviz installation.
- `rich.tree.Tree` only: Rejected — Tree renders parent-child hierarchies, not DAG topologies with cross-edges. Used for simple cases; layered renderer for full graph.
