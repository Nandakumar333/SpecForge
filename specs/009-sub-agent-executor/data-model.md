# Data Model: Sub-Agent Execution Engine

**Feature**: 009-sub-agent-executor  
**Date**: 2026-03-17

## Entities

### ExecutionState

Persistent record of implementation progress for a service.

| Field | Type | Description |
|-------|------|-------------|
| schema_version | str | Always "1.0" |
| service_slug | str | Target service slug (e.g., "ledger-service") |
| architecture | str | "monolithic" \| "microservice" \| "modular-monolith" |
| mode | str | "prompt-display" \| "agent-call" |
| tasks | tuple[TaskExecution, ...] | Per-task execution records |
| shared_infra_complete | bool | Whether --shared-infra has been run |
| verification | VerificationState \| None | Post-implementation results (microservice only) |
| created_at | str | ISO 8601 timestamp |
| updated_at | str | ISO 8601 timestamp |

**Identity**: Unique per (service_slug). One state file per service.  
**Lifecycle**: created → tasks progress → verification (optional) → complete  
**Persistence**: `.specforge/features/<slug>/.execution-state.json`

### TaskExecution

Per-task progress record within ExecutionState.

| Field | Type | Description |
|-------|------|-------------|
| task_id | str | Task ID from tasks.md (e.g., "T001") |
| status | str | "pending" \| "in-progress" \| "completed" \| "failed" \| "skipped" |
| attempt | int | Current attempt number (1-based) |
| started_at | str \| None | ISO 8601 when task started |
| completed_at | str \| None | ISO 8601 when task finished |
| commit_sha | str \| None | Git commit SHA on success |
| error_output | str \| None | Last quality check error output |
| fix_attempts | tuple[str, ...] | Error outputs from each auto-fix attempt |

**Identity**: Unique per (task_id) within a service.  
**Lifecycle**: pending → in-progress → completed \| failed \| skipped  
**State transitions**:
- pending → in-progress: Task execution begins
- in-progress → completed: Quality checks pass, commit created
- in-progress → failed: Auto-fix loop exhausted (3 attempts)
- pending → skipped: User chose "skip" in Mode A

### VerificationState

Post-implementation verification results (microservice only).

| Field | Type | Description |
|-------|------|-------------|
| container_built | bool | Docker image built successfully |
| health_check_passed | bool | Health endpoint responded correctly |
| contract_tests_passed | bool | Pact consumer tests passed |
| compose_registered | bool | Service entry added to docker-compose.yml |
| errors | tuple[str, ...] | Verification error outputs |

**Identity**: One per service (embedded in ExecutionState).  
**Lifecycle**: All false → progressively set to true as checks pass.

### ExecutionContext

Assembled read-only context for a task execution (not persisted).

| Field | Type | Description |
|-------|------|-------------|
| constitution | str | constitution.md content |
| governance_prompts | str | Concatenated governance prompts (from PromptContextBuilder) |
| service_spec | str | spec.md content |
| service_plan | str | plan.md content |
| service_data_model | str | data-model.md content |
| service_edge_cases | str | edge-cases.md content |
| service_tasks | str | tasks.md content |
| dependency_contracts | dict[str, str] | dep-slug → contract content |
| architecture_prompts | str | Extra prompts for microservice architecture |
| current_task | str | Current task description |
| estimated_tokens | int | Approximate token count |

**Identity**: Ephemeral — rebuilt per task.  
**Isolation rule**: Only files from the allowlist are included. No cross-service implementation code.

### QualityCheckResult

Outcome of build + lint + test after a task.

| Field | Type | Description |
|-------|------|-------------|
| passed | bool | All checks passed |
| build_output | str | Build command stdout/stderr |
| lint_output | str | Ruff check stdout/stderr |
| test_output | str | Pytest stdout/stderr |
| failed_checks | tuple[str, ...] | Names of failed checks |
| is_regression | bool | New failures not in original error set |

### AutoFixAttempt

Single retry cycle record.

| Field | Type | Description |
|-------|------|-------------|
| attempt_number | int | 1, 2, or 3 |
| error_input | str | Error that triggered the fix |
| fix_prompt | str | Generated fix prompt |
| files_changed | tuple[str, ...] | Files modified by fix |
| check_result | QualityCheckResult \| None | Result after fix |
| reverted | bool | True if regression detected and rolled back |

### ServiceLock

File-based lock to prevent concurrent execution.

| Field | Type | Description |
|-------|------|-------------|
| service_slug | str | Locked service |
| pid | int | Process ID of lock holder |
| started_at | str | ISO 8601 timestamp |
| current_task_id | str | Task currently being processed |
| hostname | str | Machine name |

**Persistence**: `.specforge/features/<slug>/.execution-lock`  
**Stale threshold**: 60 minutes (configurable via `EXECUTION_LOCK_STALE_MINUTES`)

### ImplementPrompt

Assembled prompt for a single task execution (not persisted).

| Field | Type | Description |
|-------|------|-------------|
| system_context | str | Governance + architecture constraints |
| task_description | str | What to implement |
| file_hints | tuple[str, ...] | Target file paths |
| dependency_context | str | Relevant contracts |
| prior_task_commits | tuple[str, ...] | Recent commit messages |

## Relationships

```
ExecutionState 1──* TaskExecution     (one state holds many task records)
ExecutionState 1──? VerificationState (optional, microservice only)
ExecutionState ──> ServiceLock        (lock protects state from concurrent access)

ExecutionContext ──> ExecutionState    (context built for current pending task)
ExecutionContext ──> ImplementPrompt   (context rendered into prompt)

AutoFixAttempt ──> QualityCheckResult (each fix attempt produces a check result)
TaskExecution ──> AutoFixAttempt      (failed task triggers fix attempts)
```

## Validation Rules

- `service_slug` must match a slug in manifest.json
- `task_id` values must match IDs in the corresponding tasks.md
- `attempt` must be ≥1 and ≤ MAX_FIX_ATTEMPTS (default 3)
- `schema_version` must be "1.0"
- `mode` must be one of IMPLEMENTATION_MODES
- `architecture` must be one of VALID_ARCHITECTURES
- `estimated_tokens` must not exceed CONTEXT_TOKEN_BUDGET (warning only, not blocking — truncation is logged)
- ServiceLock `pid` must correspond to a running process (stale if process dead)
- On resume, `detect_committed_task()` checks git log before re-executing in-progress tasks (crash-window recovery)
