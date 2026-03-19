# Implementation Plan: Parallel Execution Engine

**Branch**: `016-parallel-execution-engine` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-parallel-execution-engine/spec.md`

## Summary

Build a parallel execution engine that enables `specforge decompose --auto --parallel` to run the full 7-phase spec pipeline concurrently across all discovered services, and `specforge implement --all --parallel` to execute implementation in topologically sorted dependency waves. Uses Python's `concurrent.futures.ThreadPoolExecutor` with configurable max_workers (default 4), resilient error handling with optional `--fail-fast`, and inline progress streaming. Extends the existing `PipelineOrchestrator`, `dependency_graph`, and `OrchestrationState` infrastructure.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `concurrent.futures` (stdlib), Click 8.x (CLI), Rich 13.x (progress output), existing `specforge.core` modules
**Storage**: File system — `.specforge/features/<slug>/` per-service state files, `.specforge/config.json`, `.specforge/parallel-state.json`
**Testing**: pytest + pytest-cov + ruff; unit tests for core logic, integration tests for CLI with `CliRunner` + `tmp_path`
**Target Platform**: Cross-platform (Windows, macOS, Linux)
**Project Type**: CLI tool (extension to existing SpecForge)
**Performance Goals**: N independent services complete in ~1/min(N, max_workers) of sequential time with <15% coordination overhead
**Constraints**: I/O-bound workload (LLM subprocess calls), thread-safe state writes via existing atomic `os.replace()` pattern
**Scale/Scope**: Up to 20 concurrent services without deadlocks or resource exhaustion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | PASS | spec.md, plan.md, tasks.md exist before implementation |
| II. Architecture | PASS | New modules in `core/` with zero external dependencies (uses stdlib `concurrent.futures`). No Jinja2 templates needed (no file generation output — this feature orchestrates existing phases). |
| III. Code Quality | PASS | All functions typed, <=30 lines, Result[T] for errors, constructor injection, constants in config.py |
| IV. Testing | PASS | TDD: unit tests for all core logic, integration tests for CLI commands |
| V. Commit Strategy | PASS | Conventional Commits, one commit per task |
| VI. File Structure | PASS | New files in `src/specforge/core/` and `tests/unit/` + `tests/integration/` |
| VII. Governance | PASS | No conflicts with existing governance |

**No violations. No Jinja2 templates required** — this feature orchestrates existing phase runners that already produce output via templates/LLM. The parallel engine itself produces no file output artifacts beyond state JSON files.

## Project Structure

### Documentation (this feature)

```text
specs/016-parallel-execution-engine/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.md  # CLI flag contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── decompose_cmd.py          # MODIFY: add --auto, --parallel, --max-parallel, --fail-fast flags
│   └── specify_cmd.py            # MODIFY: add --parallel, --max-parallel, --fail-fast to implement flow
├── core/
│   ├── config.py                 # MODIFY: add PARALLEL_* constants
│   ├── parallel_pipeline_runner.py    # NEW: ParallelPipelineRunner + WorkerPool
│   ├── topological_parallel_executor.py  # NEW: TopologicalParallelExecutor (wave-based)
│   ├── parallel_progress_tracker.py   # NEW: ProgressTracker (thread-safe callbacks + inline output)
│   └── parallel_state.py             # NEW: ParallelExecutionState (frozen dataclass + persistence)
└── ...

tests/
├── unit/
│   ├── test_parallel_pipeline_runner.py   # NEW
│   ├── test_topological_parallel_executor.py  # NEW
│   ├── test_parallel_progress_tracker.py  # NEW
│   └── test_parallel_state.py             # NEW
└── integration/
    ├── test_parallel_decompose_microservice.py  # NEW
    └── test_parallel_implement_monolith.py       # NEW
```

**Structure Decision**: Extends existing `src/specforge/core/` with 4 new modules. No new directories. CLI modifications are minimal flag additions to existing commands. Tests follow existing pattern: unit for core logic, integration for CLI.

## Complexity Tracking

> No constitution violations to justify.

## Design Decisions

### D1: ThreadPoolExecutor over ProcessPoolExecutor

**Decision**: Use `ThreadPoolExecutor` for all parallel execution.
**Rationale**: The workload is I/O-bound (waiting for LLM subprocess calls via `SubprocessProvider`). Threads share memory (no pickling overhead), and the existing `PipelineState` + atomic writes are already thread-safe. ProcessPoolExecutor would add serialization complexity without benefit.

### D2: Separate ParallelPipelineRunner vs TopologicalParallelExecutor

**Decision**: Two distinct orchestration classes.
**Rationale**: `ParallelPipelineRunner` handles the decompose flow (all services independent, single wave). `TopologicalParallelExecutor` handles the implement flow (multi-wave with dependency ordering). Different concerns, different error semantics (decompose: all-independent; implement: wave-blocked).

### D3: Progress via Callback Protocol, not Shared Mutable State

**Decision**: `ProgressTracker` uses a callback protocol that phases invoke on state transitions. Console output uses Rich's thread-safe `Console.print()`.
**Rationale**: Avoids shared mutable state between threads. Each worker calls `tracker.on_phase_complete(slug, phase)` which is internally synchronized via `threading.Lock`. The tracker also writes to the dashboard-readable state file atomically.

### D4: ParallelExecutionState as Separate File

**Decision**: Persist parallel run state in `.specforge/parallel-state.json`, distinct from per-service `.pipeline-state.json`.
**Rationale**: Per-service state tracks individual pipeline progress (7 phases). Parallel state tracks the overall run: which services are assigned to which threads, overall timing, fail-fast status, wave progress. Separating concerns prevents the per-service state from growing with parallelism metadata.

### D5: --auto Flag Uses LLM for All Interactive Decisions

**Decision**: `--auto` on decompose skips architecture selection prompt (defaults to LLM-chosen architecture), feature confirmation, and over-engineering warnings.
**Rationale**: The LLM decompose prompt already returns architecture and features. `--auto` simply skips the interactive confirmation steps, using the LLM output directly. No new LLM calls needed — just bypassing `click.confirm()` and `rich.prompt.Prompt.ask()`.

### D6: Monolith = Single Wave; Modular-Monolith = Boundary-Aware

**Decision**: For monolithic architectures, all modules execute in a single wave (no dependency ordering). For modular-monolith architectures, if `communication[]` entries exist in the manifest, use them for topological ordering (same algorithm as microservices); otherwise, single wave.
**Rationale**: Monolith modules share infrastructure and have no explicit dependency graph. Modular-monolith modules may have boundary-aware communication entries that define sequencing constraints. The `ArchitectureAdapter` already differentiates behavior per-phase; the parallel executor checks for `communication[]` presence to decide.

## Component Interfaces

### ParallelPipelineRunner

```
ParallelPipelineRunner(
    orchestrator_factory: Callable[[], PipelineOrchestrator],
    tracker: ProgressTracker,
    max_workers: int = 4,
    fail_fast: bool = False,
)

.run(
    service_slugs: tuple[str, ...],
    project_root: Path,
    force: bool = False,
) -> Result[ParallelExecutionState, str]
```

- Creates one `PipelineOrchestrator` per worker thread (via factory — ensures isolated provider instances)
- Submits `orchestrator.run(slug, project_root, force)` to ThreadPoolExecutor
- On completion/failure: calls `tracker.on_service_complete/on_service_failed`
- If `fail_fast` and any future raises: cancels remaining futures via `executor.shutdown(cancel_futures=True)`
- Returns aggregated `ParallelExecutionState`

### TopologicalParallelExecutor

```
TopologicalParallelExecutor(
    runner: ParallelPipelineRunner,
    integration_orchestrator: IntegrationOrchestrator,
    tracker: ProgressTracker,
)

.execute(
    manifest: dict,
    project_root: Path,
    max_workers: int = 4,
    fail_fast: bool = False,
) -> Result[ParallelExecutionState, str]
```

- Calls `build_graph(manifest)` + `compute_phases(graph)` to get waves
- For microservice: iterates waves sequentially, calling `runner.run(wave.services)` per wave
- For monolith: single wave with all modules
- Between waves: checks for failed services and blocks dependents
- Delegates to `IntegrationOrchestrator` for shared infra and contract verification

### ProgressTracker

```
ProgressTracker(
    console: Console,
    total_services: int,
    total_phases_per_service: int = 7,
    state_path: Path | None = None,
)

.on_phase_start(slug: str, phase: str) -> None
.on_phase_complete(slug: str, phase: str) -> None
.on_phase_failed(slug: str, phase: str, error: str) -> None
.on_service_complete(slug: str) -> None
.on_service_failed(slug: str, error: str) -> None
.on_service_blocked(slug: str, blocked_by: str) -> None
.on_service_cancelled(slug: str) -> None
.get_summary() -> ParallelExecutionState
```

- All methods are thread-safe (internal `threading.Lock`)
- `on_phase_complete` prints inline: `"  [service-slug] completed research [2/7]"`
- `on_service_complete` prints: `"  [service-slug] DONE (42.3s)"`
- `on_service_failed` prints: `"  [service-slug] FAILED at plan: <error>"`
- If `state_path` provided, atomically writes dashboard-readable JSON after each event
