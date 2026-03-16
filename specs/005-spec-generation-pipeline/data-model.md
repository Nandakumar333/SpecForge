# Data Model — Spec Generation Pipeline

**Feature**: 005-spec-generation-pipeline
**Created**: 2026-03-16

## Entities

### ServiceContext (Frozen Dataclass)

Resolved context for a target service, loaded from manifest.json. Used by every phase to scope artifact content.

| Field | Type | Description |
|-------|------|-------------|
| `service_slug` | `str` | URL-safe service identifier (e.g., "ledger-service") |
| `service_name` | `str` | Human-readable name (e.g., "Ledger Service") |
| `architecture` | `str` | Architecture type from manifest ("monolithic", "microservice", "modular-monolith") |
| `project_description` | `str` | Project description from manifest |
| `domain` | `str` | Domain name from manifest (e.g., "finance") |
| `features` | `tuple[FeatureInfo, ...]` | Features mapped to this service |
| `dependencies` | `tuple[ServiceDependency, ...]` | Services this service depends on |
| `events` | `tuple[EventInfo, ...]` | Events produced or consumed by this service |
| `output_dir` | `Path` | Resolved output directory (`.specforge/features/<slug>/`) |

**Validation rules**:
- `service_slug` must be non-empty and a valid directory name
- `features` must contain at least one entry (FR-059)
- `architecture` must be in VALID_ARCHITECTURES

### FeatureInfo (Frozen Dataclass)

Lightweight feature data extracted from manifest.json for template context.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Feature ID (e.g., "001") |
| `name` | `str` | Feature slug (e.g., "auth") |
| `display_name` | `str` | Human-readable name (e.g., "Authentication") |
| `description` | `str` | Feature description |
| `priority` | `str` | Priority level (P0-P3) |
| `category` | `str` | Feature category (foundation, core, etc.) |

### ServiceDependency (Frozen Dataclass)

A dependency on another service, extracted from manifest communication links.

| Field | Type | Description |
|-------|------|-------------|
| `target_slug` | `str` | Slug of the depended-upon service |
| `target_name` | `str` | Human-readable name of the depended-upon service |
| `pattern` | `str` | Communication pattern (sync-rest, async-event, grpc) |
| `required` | `bool` | Whether this dependency is required or optional |
| `description` | `str` | What this dependency is used for |

### EventInfo (Frozen Dataclass)

Event metadata for inter-service communication context.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Event name |
| `producer` | `str` | Service slug that produces this event |
| `consumers` | `tuple[str, ...]` | Service slugs that consume this event |
| `payload_summary` | `str` | Brief description of event payload |

### PhaseStatus (Frozen Dataclass)

Status of a single pipeline phase within PipelineState.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Phase name (e.g., "spec", "research", "datamodel") |
| `status` | `str` | One of: "pending", "in-progress", "complete", "failed" |
| `started_at` | `str \| None` | ISO-8601 timestamp when phase started |
| `completed_at` | `str \| None` | ISO-8601 timestamp when phase completed |
| `artifact_paths` | `tuple[str, ...]` | Relative paths of output artifacts |
| `error` | `str \| None` | Error message if status is "failed" |

**Validation rules**:
- `status` must be one of PIPELINE_PHASE_STATUSES
- `completed_at` must be None if status is "pending" or "in-progress"
- `started_at` must be set if status is not "pending"

### PipelineState (Frozen Dataclass)

Aggregate pipeline state for a service, persisted in `.pipeline-state.json`.

| Field | Type | Description |
|-------|------|-------------|
| `service_slug` | `str` | Service this state belongs to |
| `schema_version` | `str` | State schema version ("1.0") |
| `phases` | `tuple[PhaseStatus, ...]` | Status of each pipeline phase |
| `created_at` | `str` | ISO-8601 timestamp of initial creation |
| `updated_at` | `str` | ISO-8601 timestamp of last update |

**State transitions per phase**:
```text
[pending] → start_phase() → [in-progress] → complete_phase() → [complete]
                                           → fail_phase(err) → [failed]
[in-progress] (stale — no completion) → recovery → [pending] (re-run)
[complete] → --force flag → [pending] (reset)
```

### PipelineLock (Frozen Dataclass)

Per-service lock file for concurrency control.

| Field | Type | Description |
|-------|------|-------------|
| `service_slug` | `str` | Service this lock belongs to |
| `pid` | `int` | Process ID of lock owner |
| `timestamp` | `str` | ISO-8601 timestamp when lock was acquired |

**Validation rules**:
- Lock is stale if timestamp age exceeds LOCK_STALE_THRESHOLD_MINUTES (30)
- Lock file path: `<service_output_dir>/.pipeline-lock`

### PhaseDefinition (Frozen Dataclass)

Static definition of a pipeline phase (not runtime state).

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Phase name (e.g., "spec", "research") |
| `number` | `int` | Phase number (1-6; 3 for both datamodel and edgecase) |
| `template_name` | `str` | Template logical name for TemplateRegistry lookup |
| `artifact_filename` | `str` | Output filename (e.g., "spec.md") |
| `prerequisites` | `tuple[str, ...]` | Phase names that must be complete first |
| `parallel_with` | `str \| None` | Name of phase to run in parallel with (e.g., "edgecase" for "datamodel") |

### ArchitectureAdapter (Protocol)

Not a dataclass — a protocol defining the interface for architecture-specific behavior.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_context(ctx: ServiceContext)` | `dict[str, Any]` | Architecture-specific template variables |
| `get_datamodel_context(ctx: ServiceContext)` | `dict[str, Any]` | Entity scoping rules: shared entity refs (monolith), API contract refs (microservice), strict boundary flags (modular-monolith) |
| `get_research_extras()` | `list[dict[str, str]]` | Architecture-specific research questions (e.g., service mesh for microservice, module boundary enforcement for modular-monolith) |
| `get_plan_sections()` | `list[dict[str, str]]` | Extra plan.md sections |
| `get_task_extras()` | `list[dict[str, str]]` | Extra tasks.md tasks |
| `get_edge_case_extras()` | `list[dict[str, str]]` | Extra edge-cases.md scenarios |
| `get_checklist_extras()` | `list[dict[str, str]]` | Extra checklist.md items |

Three implementations: `MicroserviceAdapter`, `MonolithAdapter`, `ModularMonolithAdapter`.

## Relationships

```text
PipelineOrchestrator
  ├── reads → manifest.json → builds → ServiceContext
  │                                      ├── has_many → FeatureInfo[]
  │                                      ├── has_many → ServiceDependency[]
  │                                      └── has_many → EventInfo[]
  ├── manages → PipelineState
  │               └── has_many → PhaseStatus[]
  ├── acquires → PipelineLock
  ├── selects → ArchitectureAdapter (based on ServiceContext.architecture)
  └── runs → PhaseDefinition[] (in dependency order)
               └── each phase uses → ServiceContext + ArchitectureAdapter + TemplateRenderer
```

## Constants (for config.py)

| Constant | Value | Description |
|----------|-------|-------------|
| `PIPELINE_STATE_FILENAME` | `".pipeline-state.json"` | State file name per service |
| `PIPELINE_LOCK_FILENAME` | `".pipeline-lock"` | Lock file name per service |
| `LOCK_STALE_THRESHOLD_MINUTES` | `30` | Minutes before lock is considered stale |
| `PIPELINE_PHASE_STATUSES` | `["pending", "in-progress", "complete", "failed"]` | Valid phase statuses |
| `PIPELINE_PHASES` | `["spec", "research", "datamodel", "edgecase", "plan", "checklist", "tasks"]` | Phase names in order |
| `SHARED_ENTITIES_PATH` | `".specforge/shared_entities.md"` | Project-level shared entities file |
| `CONTRACTS_DIR` | `"contracts"` | Subdirectory for API contracts |
| `STUB_CONTRACT_SUFFIX` | `".stub.json"` | Suffix for stub contract files |
