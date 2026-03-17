# Quickstart — Task Generation Engine

**Feature**: 008-task-generation-engine  
**Date**: 2026-03-17

---

## Prerequisites

1. SpecForge project initialized (`specforge init`)
2. Architecture decomposition complete (`specforge decompose`) — produces `manifest.json`
3. Feature spec and plan generated for target service(s) (`specforge specify <target>` through plan phase)

## Generate Tasks for a Single Service

```bash
# Run the full pipeline (spec → research → ... → tasks)
specforge specify ledger-service

# Or run only the tasks phase (if prior phases are complete)
specforge specify ledger-service --from tasks
```

Output: `.specforge/features/ledger-service/tasks.md`

## Generate Tasks for the Entire Project

```bash
# Target all services
specforge specify all
```

Output:
- `.specforge/features/<service>/tasks.md` for each service
- `.specforge/features/cross-service-infra/tasks.md` (microservice/modular-monolith only)

## Understanding the Output

### Task Format

```
T001 [P] [US1] [Layer:domain] Create Account entity
  Service: ledger-service
  Files: src/ledger-service/domain/models/Account.cs
  Depends: T000 (project scaffolding)
  Effort: S
  Prompt-rules: ARCH-001, BACK-001
  Commit: feat(ledger): add Account entity
```

| Field | Meaning |
|-------|---------|
| `T001` | Unique task ID (scoped to this file) |
| `[P]` | Can be done in parallel with other `[P]` tasks at this level |
| `[US1]` | Links to User Story 1 in the spec |
| `[Layer:domain]` | Technical layer this task belongs to |
| `Depends: T000` | Must complete T000 first |
| `Effort: S` | Estimated effort: Small |
| `Prompt-rules:` | Coding standards that apply (from governance files) |
| `Commit:` | Suggested conventional commit message |

### Cross-Service Dependencies

When a service depends on shared infrastructure:

```
[XDEP: cross-service-infra/X-T001] Shared contracts library
```

This means the task requires `X-T001` from the cross-service-infra task file to be complete first.

## Architecture Modes

| Architecture | Task categories | Cross-service tasks? |
|---|---|---|
| `microservice` | 14 steps (scaffold → gateway config) | ✅ Yes |
| `modular-monolith` | 7 steps + boundary interface | ✅ Yes (shared infra) |
| `monolithic` | 7 steps (no containers, no gRPC) | ❌ No |

## Regeneration

If you modify `plan.md` and re-run task generation, the existing `tasks.md` is backed up to `tasks.md.bak` before the new file is written.
