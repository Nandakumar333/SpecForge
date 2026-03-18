# Data Model: Implementation Orchestrator

**Feature**: 011-implementation-orchestrator
**Date**: 2026-03-17

## Entities

### OrchestrationPlan (frozen dataclass)

The computed execution plan derived from the manifest's dependency graph.

| Field | Type | Description |
|-------|------|-------------|
| `architecture` | `str` | Architecture type from manifest (`microservice`, `monolithic`, `modular-monolith`) |
| `phases` | `tuple[Phase, ...]` | Ordered execution phases (index 0 = first phase) |
| `total_services` | `int` | Total number of services/modules to implement |
| `shared_infra_required` | `bool` | Whether shared infrastructure pre-phase is needed |

**Validation rules**:
- At least one phase must exist
- No service appears in more than one phase
- `shared_infra_required` is `True` only for `microservice` and `modular-monolith`

---

### Phase (frozen dataclass)

A group of independent services/modules at the same dependency depth.

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Zero-based phase number |
| `services` | `tuple[str, ...]` | Service slugs in this phase (no mutual dependencies) |
| `dependencies_satisfied` | `tuple[str, ...]` | Service slugs from prior phases that this phase's services depend on |

**Validation rules**:
- `services` must not be empty
- No slug in `services` may appear in `dependencies_satisfied`
- All slugs in `dependencies_satisfied` must belong to phases with lower index

---

### OrchestrationState (frozen dataclass, persistent)

Project-level execution progress record. Persisted in `.specforge/orchestration-state.json`.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `str` | Always `"1.0"` |
| `architecture` | `str` | Architecture type |
| `status` | `str` | Overall status: `pending` \| `in-progress` \| `completed` \| `failed` \| `halted` |
| `shared_infra_status` | `str` | Pre-phase status: `pending` \| `in-progress` \| `completed` \| `failed` \| `skipped` |
| `phases` | `tuple[PhaseState, ...]` | Per-phase progress |
| `verification_results` | `tuple[VerificationResult, ...]` | Results at each phase boundary |
| `integration_result` | `IntegrationTestResult \| None` | Final integration validation result |
| `phase_ceiling` | `int \| None` | `--to-phase` limit (None = all phases) |
| `started_at` | `str \| None` | ISO 8601 timestamp when execution began (for elapsed time calculation) |
| `created_at` | `str` | ISO 8601 timestamp |
| `updated_at` | `str` | ISO 8601 timestamp |

**State machine**:
```
pending → in-progress → completed
                     ↓
                   failed (service/verification failure)
                     ↓
                   halted (--to-phase reached or user interrupt)
```

---

### PhaseState (frozen dataclass)

Per-phase progress within OrchestrationState.

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Phase number |
| `status` | `str` | `pending` \| `in-progress` \| `completed` \| `partial` \| `failed` |
| `services` | `tuple[ServiceStatus, ...]` | Per-service status within this phase |
| `started_at` | `str \| None` | ISO 8601 timestamp |
| `completed_at` | `str \| None` | ISO 8601 timestamp |

**Status semantics**:
- `partial`: At least one service succeeded but at least one failed (continue-then-halt policy)
- `completed`: All services succeeded
- `failed`: All services failed

---

### ServiceStatus (frozen dataclass)

Per-service implementation status within a phase.

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | Service slug |
| `status` | `str` | `pending` \| `in-progress` \| `completed` \| `failed` \| `skipped` |
| `error` | `str \| None` | Error message if failed |
| `tasks_completed` | `int` | Number of tasks completed |
| `tasks_total` | `int` | Total tasks for this service |
| `started_at` | `str \| None` | ISO 8601 |
| `completed_at` | `str \| None` | ISO 8601 |

---

### VerificationResult (frozen dataclass)

Outcome of inter-phase contract/boundary verification.

| Field | Type | Description |
|-------|------|-------------|
| `after_phase` | `int` | Phase index after which this verification ran |
| `passed` | `bool` | Overall pass/fail |
| `contract_results` | `tuple[ContractCheckResult, ...]` | Per-pair contract check results |
| `boundary_results` | `tuple[BoundaryCheckResult, ...]` | Shared entity boundary results |
| `infra_health` | `bool \| None` | docker-compose health (microservice only; None for monolith) |
| `timestamp` | `str` | ISO 8601 |

---

### ContractCheckResult (frozen dataclass)

Result of contract verification between a specific service pair.

| Field | Type | Description |
|-------|------|-------------|
| `consumer` | `str` | Consumer service slug |
| `provider` | `str` | Provider service slug |
| `passed` | `bool` | Whether contracts match |
| `mismatches` | `tuple[ContractMismatch, ...]` | Specific mismatches found |

---

### ContractMismatch (frozen dataclass)

A specific contract violation between two services.

| Field | Type | Description |
|-------|------|-------------|
| `contract_file` | `str` | Path to the contract file |
| `field` | `str` | The field/endpoint/schema element that mismatches |
| `expected` | `str` | What the consumer expects |
| `actual` | `str` | What the provider publishes |
| `severity` | `str` | `error` \| `warning` |

---

### BoundaryCheckResult (frozen dataclass)

Result of shared entity boundary analysis between services.

| Field | Type | Description |
|-------|------|-------------|
| `entity` | `str` | Entity/concept name |
| `services` | `tuple[str, ...]` | Services that reference this entity |
| `violation_type` | `str` | `ownership_conflict` \| `direct_access` \| `schema_overlap` |
| `details` | `str` | Human-readable description |

---

### IntegrationTestResult (frozen dataclass)

Result of final integration validation.

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Overall pass/fail |
| `health_checks` | `tuple[HealthCheckResult, ...]` | Per-service health check results |
| `gateway_routes` | `tuple[RouteCheckResult, ...]` | Gateway route verification results |
| `request_flow` | `RequestFlowResult \| None` | Cross-service request flow test |
| `event_propagation` | `EventPropagationResult \| None` | Event bus test |
| `timestamp` | `str` | ISO 8601 |

---

### HealthCheckResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `service` | `str` | Service slug |
| `passed` | `bool` | Health check pass/fail |
| `status_code` | `int \| None` | HTTP status code if available |
| `response_time_ms` | `int \| None` | Response time in ms |
| `error` | `str \| None` | Error details |

---

### RouteCheckResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `route` | `str` | Gateway route path |
| `target_service` | `str` | Expected target service |
| `passed` | `bool` | Whether route resolves correctly |
| `error` | `str \| None` | Error details |

---

### RequestFlowResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Whether request flowed end-to-end |
| `steps` | `tuple[str, ...]` | Ordered steps the request took |
| `error` | `str \| None` | Error details |

---

### EventPropagationResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Whether events propagated correctly |
| `events_tested` | `tuple[str, ...]` | Event names tested |
| `failed_events` | `tuple[str, ...]` | Event names that failed |
| `error` | `str \| None` | Error details |

---

### IntegrationReport (frozen dataclass)

Final summary report covering the entire orchestration run.

| Field | Type | Description |
|-------|------|-------------|
| `architecture` | `str` | Architecture type |
| `total_phases` | `int` | Number of phases executed |
| `total_services` | `int` | Total services implemented |
| `succeeded_services` | `int` | Services that completed successfully |
| `failed_services` | `int` | Services that failed |
| `skipped_services` | `int` | Services skipped (missing artifacts or dep on failed) |
| `phase_results` | `tuple[PhaseState, ...]` | Per-phase outcomes |
| `verification_results` | `tuple[VerificationResult, ...]` | Per-boundary verification |
| `integration_result` | `IntegrationTestResult \| None` | Final integration |
| `verdict` | `str` | `pass` \| `fail` \| `partial` |
| `created_at` | `str` | ISO 8601 |

## Entity Relationships

```
OrchestrationPlan
    └── 1..* Phase
              └── 1..* service slugs (str)

OrchestrationState
    ├── 1..* PhaseState
    │         └── 1..* ServiceStatus
    ├── 0..* VerificationResult
    │         ├── 0..* ContractCheckResult
    │         │         └── 0..* ContractMismatch
    │         └── 0..* BoundaryCheckResult
    └── 0..1 IntegrationTestResult
              ├── 1..* HealthCheckResult
              ├── 0..* RouteCheckResult
              ├── 0..1 RequestFlowResult
              └── 0..1 EventPropagationResult

IntegrationReport (aggregates OrchestrationState for final output)
```

## Cross-Feature Integration

| This Feature Entity | Consumes From | Via |
|---------------------|---------------|-----|
| `OrchestrationPlan.architecture` | Feature 004 Manifest | `manifest.json["architecture"]` |
| `Phase.services` | Feature 004 Manifest | `manifest.json["services"][*]["slug"]` |
| `Phase.dependencies_satisfied` | Feature 004 Manifest | `manifest.json["services"][*]["communication"]` |
| `ServiceStatus` | Feature 009 `ExecutionState` | `.specforge/features/<slug>/.execution-state.json` |
| `ContractCheckResult` | Feature 009 contracts | `.specforge/features/<slug>/contracts/` |
| `BoundaryCheckResult` | Feature 006 `BoundaryAnalyzer` | In-memory analysis of manifest |
| `HealthCheckResult` | Feature 009 `DockerManager` | HTTP health check via subprocess |
