# CLI Contract: Parallel Execution Engine

**Feature**: 016-parallel-execution-engine
**Date**: 2026-03-19

## Enhanced Commands

### `specforge decompose`

```text
specforge decompose <DESCRIPTION> [OPTIONS]

Arguments:
  DESCRIPTION          Project description for AI decomposition

Existing Options:
  --arch TEXT           Architecture type (microservice|monolithic|modular-monolith)
  --remap TEXT          Re-map features to new architecture
  --no-warn            Suppress over-engineering warnings
  --template-mode      Force rule-based decomposition (no LLM)
  --dry-run-prompt     Write prompt without calling LLM

New Options (Feature 016):
  --auto               Suppress all interactive prompts; use LLM output directly
  --parallel           Run spec pipeline concurrently across all discovered services
  --max-parallel N     Override parallel.max_workers from config.json (integer >= 1)
  --fail-fast          Cancel all workers on first service failure

Constraints:
  --parallel requires a configured AI provider in .specforge/config.json
  --max-parallel requires --parallel (ignored without it)
  --fail-fast requires --parallel (ignored without it)
  --auto can be used independently of --parallel
  --parallel can be used independently of --auto
```

**Exit codes**:
- 0: All services completed successfully
- 1: One or more services failed (partial success)
- 2: Fatal error (no services started, e.g., cycle detected, no provider configured)

**Output format** (when --parallel):
```text
Decomposing "Personal Finance App" with 6 services (max 4 parallel)...

  identity-service: completed spec [1/7]
  admin-service: completed spec [1/7]
  identity-service: completed research [2/7]
  ...
  identity-service: DONE (45.2s)
  admin-service: DONE (52.1s)
  ...

Parallel decompose complete: 6/6 services succeeded (2m 15s total)
```

### `specforge implement`

```text
specforge implement <TARGET> [OPTIONS]

Arguments:
  TARGET               Service slug or "all" for all services

Existing Options:
  --all                Implement all services
  --phase-ceiling N    Limit implementation phases

New Options (Feature 016):
  --parallel           Run independent services concurrently within each wave
  --max-parallel N     Override parallel.max_workers from config.json (integer >= 1)
  --fail-fast          Cancel all workers on first service failure

Constraints:
  --parallel requires --all (single-service runs are inherently sequential)
  --max-parallel requires --parallel
  --fail-fast requires --parallel
```

**Exit codes**: Same as decompose.

**Output format** (when --parallel):
```text
Implementing 6 services in 3 waves (max 4 parallel)...

Wave 1/3: identity-service, admin-service
  identity-service: completed task 1/12
  admin-service: completed task 1/8
  ...
  identity-service: DONE (3m 22s)
  admin-service: DONE (2m 45s)

Wave 2/3: ledger-service, portfolio-service
  ...

Parallel implement complete: 6/6 services succeeded (8m 30s total)
```

## Config Schema

```json
{
  "agent": "claude",
  "llm": { ... },
  "parallel": {
    "max_workers": 4
  }
}
```

| Key | Type | Default | CLI Override |
|-----|------|---------|-------------|
| parallel.max_workers | int | 4 | --max-parallel N |
