# Data Model: Project Status Dashboard

**Feature**: `012-project-status-dashboard`  
**Date**: 2026-03-18

## Entity Overview

```
ProjectStatusSnapshot (top-level, backs all output formats)
├── architecture: str
├── services: [ServiceStatusRecord, ...]
│   └── lifecycle: LifecyclePhases
├── phases: [PhaseProgressRecord, ...]
│   └── service_details: [(slug, status), ...]
├── quality: QualitySummaryRecord
├── graph: DependencyGraph
│   └── nodes: [GraphNode, ...]
│       └── edges: [str, ...]
└── warnings: [str, ...]
```

## Entities

### ProjectStatusSnapshot

Top-level container representing a point-in-time capture of the entire project. This is the single data structure passed to all renderers and report generators.

| Field | Type | Description |
|-------|------|-------------|
| project_name | str | Project name from manifest or directory name |
| architecture | str | `"microservice"` \| `"monolithic"` \| `"modular-monolith"` |
| services | tuple[ServiceStatusRecord, ...] | One record per manifest-declared service |
| phases | tuple[PhaseProgressRecord, ...] | One record per execution phase |
| quality | QualitySummaryRecord | Aggregated quality metrics |
| graph | DependencyGraph | Service dependency topology |
| warnings | tuple[str, ...] | Warnings from corrupted/missing state files |
| timestamp | str | ISO 8601 generation timestamp |
| has_failures | bool | True if any service status is FAILED |

### ServiceStatusRecord

Per-service status combining data from all state files.

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service identifier (e.g., `"identity-service"`) |
| display_name | str | Human-readable name from manifest |
| features | tuple[str, ...] | Associated feature IDs (e.g., `("001",)` or `("004", "006", "007")`) |
| lifecycle | LifecyclePhases | Per-phase status breakdown |
| overall_status | str | `COMPLETE` \| `IN_PROGRESS` \| `PLANNING` \| `NOT_STARTED` \| `BLOCKED` \| `FAILED` \| `UNKNOWN` |
| phase_index | int \| None | Which execution phase this service belongs to |

### LifecyclePhases

Breakdown of where a service is in the development lifecycle.

| Field | Type | Description |
|-------|------|-------------|
| spec | str \| None | `"DONE"` \| `"WIP"` \| None |
| plan | str \| None | `"DONE"` \| `"WIP"` \| None |
| tasks | str \| None | `"DONE"` \| `"WIP"` \| None |
| impl_percent | int \| None | 0–100 implementation completion |
| tests_passed | int \| None | Number of passing tests |
| tests_total | int \| None | Total number of tests |
| docker | str \| None | `"OK"` \| `"FAIL"` \| None (microservice only) |
| boundary_compliance | str \| None | `"OK"` \| `"FAIL"` \| None (modular-monolith only) |

**Derivation rules**:
- `spec`: Derived from `PipelineState.phases["spec"].status` — `"complete"` → `"DONE"`, `"in-progress"` → `"WIP"`, else `None`
- `plan`: Derived from `PipelineState.phases["plan"].status` — same mapping
- `tasks`: Derived from `PipelineState.phases["tasks"].status` — same mapping
- `impl_percent`: Derived from `ExecutionState.tasks` — `completed_count / total_count * 100` if `total_count > 0`, else `0` (guards against division by zero when execution state exists but has no tasks)
- `tests_passed/total`: Derived from `QualityReport.gate_result.check_results` where `checker_name == "pytest"` — parsed from output
- `docker`: Derived from `ExecutionState.verification.container_built` + `QualityReport` docker check
- `boundary_compliance`: Derived from `QualityReport.gate_result.check_results` where `category == BOUNDARY`

### PhaseProgressRecord

Execution phase aggregate status.

| Field | Type | Description |
|-------|------|-------------|
| index | int | Phase number (0-based from orchestration state) |
| label | str | Display label (e.g., `"Phase 1"`) |
| services | tuple[str, ...] | Service slugs in this phase |
| completion_percent | float | 0.0–100.0 aggregate completion |
| status | str | `"complete"` \| `"in-progress"` \| `"blocked"` \| `"pending"` |
| blocked_by | int \| None | Index of blocking prerequisite phase |
| service_details | tuple[ServicePhaseDetail, ...] | Per-service status within this phase |

### ServicePhaseDetail

Per-service status within a phase (used in phase progress notes).

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service identifier |
| status | str | Same as `ServiceStatusRecord.overall_status` |
| impl_percent | int \| None | Implementation percentage |

### QualitySummaryRecord

Project-wide aggregated quality metrics.

| Field | Type | Description |
|-------|------|-------------|
| services_total | int | Total services from manifest |
| services_complete | int | Count with overall_status == COMPLETE |
| services_in_progress | int | Count with overall_status == IN_PROGRESS |
| services_planning | int | Count with overall_status == PLANNING |
| services_not_started | int | Count with overall_status == NOT_STARTED |
| services_blocked | int | Count with overall_status == BLOCKED |
| services_failed | int | Count with overall_status == FAILED |
| services_unknown | int | Count with overall_status == UNKNOWN |
| tasks_total | int | Sum of all task counts across services |
| tasks_complete | int | Sum of completed tasks |
| tasks_failed | int | Sum of failed tasks |
| coverage_avg | float \| None | Mean test coverage across implemented services (None if no data) |
| docker_built | int \| None | Successfully built Docker images (None for non-microservice) |
| docker_total | int \| None | Total expected Docker images (None for non-microservice) |
| docker_failing | int \| None | Docker images that failed to build (None for non-microservice) |
| contract_passed | int \| None | Passing contract test suites (None for non-microservice) |
| contract_total | int \| None | Total contract test suites (None for non-microservice) |
| autofix_success_rate | float \| None | Percentage of auto-fix attempts that succeeded (None if no attempts) |

### DependencyGraph

Service dependency topology for graph visualization.

| Field | Type | Description |
|-------|------|-------------|
| nodes | tuple[GraphNode, ...] | One node per service |
| phase_groups | tuple[tuple[str, ...], ...] | Services grouped by phase |

### GraphNode

Individual node in the dependency graph.

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service identifier |
| status | str | Overall service status |
| dependencies | tuple[str, ...] | Slugs of services this depends on |

## State Transitions

### Service Overall Status

```
NOT_STARTED → PLANNING → IN_PROGRESS → COMPLETE
                ↓              ↓
              FAILED         FAILED
                ↓              ↓
              (manual fix + retry)

BLOCKED → (dependency completes) → PLANNING or IN_PROGRESS

Any state → UNKNOWN (when state files are corrupted)
```

**Transition triggers**:
- `NOT_STARTED → PLANNING`: First pipeline phase (spec) transitions to `in-progress`
- `PLANNING → IN_PROGRESS`: First execution task transitions to `in-progress`
- `IN_PROGRESS → COMPLETE`: All tasks `completed` + quality gate `passed`
- `IN_PROGRESS → FAILED`: Any task `failed` beyond retry budget OR quality gate `passed == false`
- `* → BLOCKED`: Service's dependency phase is not `completed` in orchestration state
- `* → UNKNOWN`: State file read returns `Err`

## Relationship to Existing Models

| This Feature's Model | Source State File | Source Model |
|----------------------|-------------------|--------------|
| LifecyclePhases.spec/plan/tasks | `.pipeline-state.json` | `PipelineState.phases[].status` |
| LifecyclePhases.impl_percent | `.execution-state.json` | `ExecutionState.tasks[].status` counts |
| LifecyclePhases.tests_* | `.quality-report.json` | `QualityReport.gate_result.check_results` |
| LifecyclePhases.docker | `.execution-state.json` + `.quality-report.json` | `VerificationState.container_built` + docker `CheckResult` |
| PhaseProgressRecord | `.orchestration-state.json` | `OrchestrationState.phases[]` |
| QualitySummaryRecord.autofix_* | `.quality-report.json` | `QualityReport.fix_attempts[]` |

## Intermediate Types (Internal)

These types are used during data collection and are NOT part of the output schema. They exist only within `StatusCollector` to bridge raw state files to domain models.

### ManifestData

Read-only wrapper for the parsed manifest.json.

| Field | Type | Description |
|-------|------|-------------|
| project_name | str | Project name |
| architecture | str | `"microservice"` \| `"monolithic"` \| `"modular-monolith"` |
| services | tuple[ManifestServiceEntry, ...] | Declared services |
| communication | tuple[CommunicationEntry, ...] | Service dependency declarations |

### ManifestServiceEntry

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service identifier |
| display_name | str | Human-readable name |
| features | tuple[str, ...] | Associated feature IDs |

### ServiceRawState

Per-service collection of all state files (each may be absent).

| Field | Type | Description |
|-------|------|-------------|
| slug | str | Service identifier |
| pipeline | Result[PipelineState] \| None | None if file doesn't exist; Err if corrupt |
| execution | Result[ExecutionState] \| None | None if file doesn't exist; Err if corrupt |
| quality | Result[QualityReport] \| None | None if file doesn't exist; Err if corrupt |
| orchestration_phase | int \| None | Phase index from OrchestrationState, if present |

**Interpretation rules**:
- `None` → file does not exist (never created) → service has not reached that stage
- `Err(...)` → file exists but is corrupt/unreadable → service status becomes UNKNOWN, add to warnings
- `Ok(...)` → valid data available for derivation

## Aggregation Rules

### QualityReport Aggregation (task-level → service-level)

Multiple `QualityReport` files may exist at `task` level for a single service. Aggregation strategy:

1. **Service-level report takes precedence** if present (level == "service")
2. If only task-level reports exist, merge: union of all `check_results`, `passed` = all tasks passed, `fix_attempts` = concatenation of all attempt lists
3. If no quality report exists → quality fields are all `null` in output

### Multi-Feature Service Counting

Services that map to multiple features (e.g., `planning-service → 004+006+007`) are counted **once** in all aggregations:
- Phase progress: counted as 1 service, not 3 features
- Quality summary: counted as 1 service toward status counters
- `services_total` matches manifest service count, never feature count
