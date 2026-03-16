# CLI Contract — Spec Generation Pipeline

## New Commands

### `specforge specify <target>`

Runs the full pipeline (all 6 phases) for a service or module.

```text
Usage: specforge specify [OPTIONS] TARGET

  Generate specification artifacts for a service or module.

Arguments:
  TARGET    Service slug (e.g., "ledger-service") or feature number (e.g., "002")

Options:
  --force         Regenerate all artifacts from scratch
  --from PHASE    Start from a specific phase (spec|research|datamodel|plan|checklist|tasks)
  --help          Show this message and exit
```

**Resolution behavior**:
- If TARGET matches a service slug in manifest.json → use that service
- If TARGET is a numeric pattern (e.g., "002") → resolve to owning service, display message: "Feature 002 belongs to ledger-service, generating specs for entire service"
- If TARGET not found → error with list of available services/modules

**Output**:
```text
$ specforge specify ledger-service
  Loading manifest.json...
  Service: Ledger Service (2 features: accounts, transactions)
  Architecture: microservice

  Phase 1/6: Generating spec.md... done (1.2s)
  Phase 2/6: Generating research.md... done (0.8s)
  Phase 3/6: Generating data-model.md + edge-cases.md... done (1.5s)
  Phase 4/6: Generating plan.md... done (1.1s)
  Phase 5/6: Generating checklist.md... done (0.3s)
  Phase 6/6: Generating tasks.md... done (0.5s)

  All artifacts written to .specforge/features/ledger-service/
```

**Error cases**:
```text
$ specforge specify nonexistent
  Error: Service "nonexistent" not found in manifest.json
  Available services: identity-service, ledger-service, planning-service

$ specforge specify ledger-service  # while another terminal is running it
  Error: Pipeline already running for ledger-service (started 2m ago, PID 12345)
  Use --force to override if the previous run crashed.

$ specforge specify plan ledger-service  # prerequisites not met
  Error: Cannot run phase "plan" — prerequisites not complete.
  Missing: spec (phase 1), research (phase 2), datamodel (phase 3a)
  Run: specforge specify ledger-service

$ specforge specify ledger-service  # no manifest
  Error: manifest.json not found at .specforge/manifest.json
  Run: specforge decompose <description> first
```

### `specforge pipeline-status [TARGET]`

Show pipeline state for a service or all services.

```text
Usage: specforge pipeline-status [OPTIONS] [TARGET]

  Show pipeline completion status.

Arguments:
  TARGET    Optional service slug. If omitted, shows all services.

Options:
  --help    Show this message and exit
```

**Output**:
```text
$ specforge pipeline-status
  identity-service: 6/6 phases complete
  ledger-service:   4/6 phases complete (next: checklist)
  planning-service: not started

$ specforge pipeline-status ledger-service
  Service: Ledger Service
  Phase 1 (spec):      complete  (2026-03-16 10:00)
  Phase 2 (research):  complete  (2026-03-16 10:01)
  Phase 3a (datamodel): complete  (2026-03-16 10:02)
  Phase 3b (edgecase):  complete  (2026-03-16 10:02)
  Phase 4 (plan):      complete  (2026-03-16 10:03)
  Phase 5 (checklist): pending
  Phase 6 (tasks):     pending
```

## Modified Commands

### `specforge decompose` (Feature 004)

No changes to the command itself. The pipeline reads its output (manifest.json) as input.

## Pipeline State File Contract

### `.pipeline-state.json`

```json
{
  "schema_version": "1.0",
  "service_slug": "ledger-service",
  "created_at": "2026-03-16T10:00:00+00:00",
  "updated_at": "2026-03-16T10:03:00+00:00",
  "phases": [
    {
      "name": "spec",
      "status": "complete",
      "started_at": "2026-03-16T10:00:00+00:00",
      "completed_at": "2026-03-16T10:00:01+00:00",
      "artifact_paths": ["spec.md"],
      "error": null
    },
    {
      "name": "research",
      "status": "complete",
      "started_at": "2026-03-16T10:01:00+00:00",
      "completed_at": "2026-03-16T10:01:01+00:00",
      "artifact_paths": ["research.md"],
      "error": null
    },
    {
      "name": "datamodel",
      "status": "in-progress",
      "started_at": "2026-03-16T10:02:00+00:00",
      "completed_at": null,
      "artifact_paths": ["data-model.md"],
      "error": null
    },
    {
      "name": "edgecase",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "artifact_paths": ["edge-cases.md"],
      "error": null
    },
    {
      "name": "plan",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "artifact_paths": ["plan.md"],
      "error": null
    },
    {
      "name": "checklist",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "artifact_paths": ["checklist.md"],
      "error": null
    },
    {
      "name": "tasks",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "artifact_paths": ["tasks.md"],
      "error": null
    }
  ]
}
```

### `.pipeline-lock`

```json
{
  "service_slug": "ledger-service",
  "pid": 12345,
  "timestamp": "2026-03-16T10:00:00+00:00"
}
```

## Stub Contract Format

### `api-spec.stub.json`

```json
{
  "service": "identity-service",
  "stub": true,
  "generated_by": "ledger-service",
  "generated_at": "2026-03-16T10:00:00+00:00",
  "endpoints": [
    {
      "method": "GET",
      "path": "/users/{id}",
      "description": "Retrieve user by ID (inferred from sync-rest dependency)",
      "request": {},
      "response": {"id": "string", "name": "string"}
    }
  ]
}
```

### `api-spec.json` (real contract)

```json
{
  "service": "ledger-service",
  "stub": false,
  "generated_at": "2026-03-16T10:00:00+00:00",
  "endpoints": [
    {
      "method": "GET",
      "path": "/accounts",
      "description": "List all accounts for the authenticated user",
      "request": {},
      "response": [{"id": "string", "name": "string", "balance": "number"}]
    },
    {
      "method": "POST",
      "path": "/transactions",
      "description": "Create a new transaction",
      "request": {"account_id": "string", "amount": "number", "category": "string"},
      "response": {"id": "string", "status": "string"}
    }
  ]
}
```
