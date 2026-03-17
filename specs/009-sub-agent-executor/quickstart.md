# Quickstart: Sub-Agent Execution Engine

**Feature**: 009-sub-agent-executor  
**Date**: 2026-03-17

## Prerequisites

Before running `specforge implement`, ensure:

1. **Project initialized**: `specforge init` has been run
2. **Architecture decomposed**: `specforge decompose` has been run (manifest.json exists)
3. **Spec pipeline complete**: `specforge specify <service>` has been run for the target service, producing: spec.md, plan.md, data-model.md, edge-cases.md, tasks.md
4. **For microservice projects**: Shared infrastructure tasks exist (`cross-service-infra/tasks.md`)

## Basic Usage

### 1. Build Shared Infrastructure (microservice only)

```bash
specforge implement --shared-infra
```

This creates shared contracts, docker-compose base, gateway skeleton, and message broker configuration. Must complete before any service implementation.

### 2. Implement a Service

```bash
# Mode A: prompts displayed for you to copy into your agent
specforge implement ledger-service

# Mode B: prompts sent directly to your configured agent
specforge implement ledger-service --mode agent-call
```

### 3. Resume After Interruption

```bash
specforge implement --resume ledger-service
```

### 4. Check Implementation Status

The execution state file at `.specforge/features/<slug>/.execution-state.json` tracks progress. Open it to see which tasks are completed, pending, or failed.

## Execution Flow

For each task in `tasks.md`:

```
┌─────────────────┐
│  Load Context    │ constitution + governance + service artifacts + contracts
└────────┬────────┘
         ▼
┌─────────────────┐
│ Generate Prompt  │ One prompt per task (atomic)
└────────┬────────┘
         ▼
┌─────────────────┐
│   Execute Task   │ Mode A: display prompt | Mode B: call agent
└────────┬────────┘
         ▼
┌─────────────────┐
│ Quality Checks   │ build → ruff → pytest
└────────┬────────┘
    pass │     │ fail
         ▼     ▼
┌────────┐ ┌──────────────┐
│ Commit │ │ Auto-Fix Loop│ max 3 attempts
└────────┘ └──────┬───────┘
                  │ fixed    │ exhausted
                  ▼          ▼
            ┌────────┐ ┌──────────┐
            │ Commit │ │   HALT   │ save state for resume
            └────────┘ └──────────┘
```

## Typical Session

```bash
# Step 1: Shared infra (microservice project)
$ specforge implement --shared-infra
✓ X-T001: Shared contracts library
✓ X-T002: Docker compose base
✓ X-T003: Message broker setup
✓ X-T004: API gateway skeleton
✓ X-T005: Shared authentication
Shared infrastructure complete. 5/5 tasks committed.

# Step 2: Implement identity-service first (no dependencies)
$ specforge implement identity-service
Processing 14 tasks for identity-service...
✓ T001: Project scaffolding                    [S]
✓ T002: Domain models (User, Session, Token)   [M]
...
✓ T014: Gateway route configuration            [S]
Verification: Docker ✓ | Health ✓ | Contracts ✓
identity-service complete. 14/14 tasks committed.

# Step 3: Implement ledger-service (depends on identity-service)
$ specforge implement ledger-service
Processing 14 tasks for ledger-service...
✓ T001: Project scaffolding                    [S]
✓ T002: Domain models (Account, Transaction)   [M]
...
✗ T011: Unit tests — 2 failures
  Auto-fix attempt 1/3... ✓ Fixed
✓ T011: Unit tests (after fix)                 [L]
...
ledger-service complete. 14/14 tasks committed.
```
