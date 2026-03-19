# Data Model: Parallel Execution Engine

**Feature**: 016-parallel-execution-engine
**Date**: 2026-03-19

## Entity Diagram

```text
┌─────────────────────────┐     ┌──────────────────────────┐
│  ParallelExecutionState │     │    ServiceRunStatus      │
│─────────────────────────│     │──────────────────────────│
│  run_id: str            │     │  slug: str               │
│  mode: str              │◄────│  status: str             │
│  architecture: str      │ 1:N │  wave_index: int         │
│  total_services: int    │     │  phases_completed: int   │
│  max_workers: int       │     │  phases_total: int (=7)  │
│  fail_fast: bool        │     │  error: str | None       │
│  status: str            │     │  blocked_by: str | None  │
│  started_at: str        │     │  started_at: str | None  │
│  completed_at: str|None │     │  completed_at: str|None  │
│  services: tuple[...]   │     └──────────────────────────┘
│  waves: tuple[...]      │
│  created_at: str        │     ┌──────────────────────────┐
│  updated_at: str        │     │    WaveStatus            │
└─────────────────────────┘     │──────────────────────────│
         │                      │  index: int              │
         ├──────────────────────│  status: str             │
         │                 1:N  │  services: tuple[str]    │
         │                      │  started_at: str | None  │
         │                      │  completed_at: str|None  │
         │                      └──────────────────────────┘
         │
         │                      ┌──────────────────────────┐
         │                      │   ProgressEvent          │
         └──────────────────────│──────────────────────────│
                           1:N  │  timestamp: str          │
                                │  slug: str               │
                                │  event_type: str         │
                                │  phase: str | None       │
                                │  message: str            │
                                └──────────────────────────┘
```

## Entities

### ParallelExecutionState

Tracks the overall status of a parallel run. Persisted to `.specforge/parallel-state.json` for resume capability.

| Field | Type | Description |
|-------|------|-------------|
| run_id | str | Unique identifier for this parallel run (ISO timestamp) |
| mode | str | "decompose" or "implement" |
| architecture | str | "microservice", "monolithic", or "modular-monolith" |
| total_services | int | Number of services in this run |
| max_workers | int | Configured max concurrent workers |
| fail_fast | bool | Whether --fail-fast was specified |
| status | str | "pending", "in-progress", "completed", "failed", "cancelled" |
| services | tuple[ServiceRunStatus, ...] | Per-service progress |
| waves | tuple[WaveStatus, ...] | Per-wave progress (implement mode only) |
| started_at | str | ISO timestamp when run started |
| completed_at | str or None | ISO timestamp when run finished |
| created_at | str | ISO timestamp |
| updated_at | str | ISO timestamp |

**State transitions**: pending -> in-progress -> completed | failed | cancelled

**Validation rules**:
- `total_services` must equal `len(services)`
- `status` = "completed" only when all services are "completed" or "blocked"
- `status` = "failed" when any service is "failed" and not all others completed
- `status` = "cancelled" when shutdown triggered by fail-fast or SIGINT

### ServiceRunStatus

Tracks individual service progress within a parallel run.

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service slug (matches manifest) |
| status | str | "pending", "in-progress", "completed", "failed", "blocked", "cancelled" |
| wave_index | int | Which dependency wave this service belongs to |
| phases_completed | int | Number of completed phases (0-7) |
| phases_total | int | Always 7 (the spec pipeline phases) |
| error | str or None | Error message if failed |
| blocked_by | str or None | Slug of failed dependency (if blocked) |
| started_at | str or None | ISO timestamp when execution started |
| completed_at | str or None | ISO timestamp when finished |

**State transitions**:
- pending -> in-progress -> completed | failed
- pending -> blocked (dependency failed)
- in-progress -> cancelled (fail-fast or SIGINT)

**Validation rules**:
- `blocked_by` is set only when `status` = "blocked"
- `phases_completed` <= `phases_total`
- `completed_at` is set only when `status` in ("completed", "failed", "blocked", "cancelled")

### WaveStatus

Tracks dependency wave progress (used only in implement mode).

| Field | Type | Description |
|-------|------|-------------|
| index | int | Wave index (0-based, from topological sort) |
| status | str | "pending", "in-progress", "completed", "partial", "skipped" |
| services | tuple[str, ...] | Service slugs assigned to this wave |
| started_at | str or None | ISO timestamp |
| completed_at | str or None | ISO timestamp |

**State transitions**: pending -> in-progress -> completed | partial | skipped

**Validation rules**:
- `status` = "partial" when some services completed and some failed/blocked
- `status` = "skipped" when wave was never started due to fail-fast

### ProgressEvent (Internal Only)

Not a persisted dataclass. ProgressTracker uses internal counters and dicts to track events. Inline console output is produced directly by callback methods. No separate ProgressEvent frozen dataclass is needed. |

## Relationships

- **ParallelExecutionState** 1:N **ServiceRunStatus**: Each parallel run contains one entry per service.
- **ParallelExecutionState** 1:N **WaveStatus**: Each implement run contains one entry per dependency wave.
- **ParallelExecutionState** 1:N **ProgressEvent**: Events are accumulated in-memory for summary generation (not persisted individually).
- **ServiceRunStatus.slug** references **manifest.json services[].slug**: Links parallel state to the canonical service definition.
- **ServiceRunStatus.wave_index** references **WaveStatus.index**: Links service to its dependency wave.

## Config Schema Extension

New keys in `.specforge/config.json`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| parallel.max_workers | int | 4 | Maximum concurrent service pipelines |
| parallel.enabled | bool | true | Whether --parallel flag is available |

These are read-only at startup. `--max-parallel N` CLI flag overrides `parallel.max_workers` for the current invocation.

## Persistence Strategy

- **ParallelExecutionState**: `.specforge/parallel-state.json` — atomic write via `tempfile` + `os.replace()`, same pattern as `pipeline_state.py` and `orchestration_state.py`.
- **Per-service PipelineState**: `.specforge/features/<slug>/.pipeline-state.json` — unchanged from Feature 005, each thread writes to its own service directory.
- **ProgressEvent**: In-memory only (list within `ProgressTracker`). Used for summary generation at end of run.
