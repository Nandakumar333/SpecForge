# CLI Contract — generate-tasks

**Feature**: 008-task-generation-engine  
**Date**: 2026-03-17

---

## Command

Task generation is triggered via the existing `specforge specify` command, which runs the 7-phase pipeline. The tasks phase (phase 7) uses the new `TaskGenerator` internally. No new CLI command is added.

### Pipeline Phase Integration

```
specforge specify <target> [--force] [--from tasks]
```

**Arguments**:
- `target` — Service slug, module name, or `all` for full-project generation

**Options**:
- `--force` — Regenerate all artifacts including tasks
- `--from tasks` — Start pipeline from the tasks phase only (skip spec, research, etc.)

### Output Files

```
.specforge/features/<service-slug>/tasks.md       # Per-service task file
.specforge/features/cross-service-infra/tasks.md   # Cross-service infra (microservice only)
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success — all task files generated |
| `1` | Error — manifest not found, invalid architecture, or circular dependencies |
| `2` | Partial — some services skipped due to missing plan.md (warnings emitted) |

### Output Format (tasks.md)

```markdown
# Tasks — ProjectName

**Service**: ledger-service (`ledger-service`)
**Architecture**: microservice
**Generated**: 2026-03-17

## Cross-Service Dependencies

- [XDEP: cross-service-infra/X-T001] Shared contracts library

---

## Phase 1: Scaffolding

T001 [US1] [Layer:scaffolding] Set up ledger-service project scaffold
  Service: ledger-service
  Files: src/ledger-service/
  Depends: —
  Effort: S
  Commit: feat(ledger): scaffold project structure

## Phase 2: Domain

T002 [P] [US1] [Layer:domain] Create Account entity
  Service: ledger-service
  Files: src/ledger-service/domain/models/Account.cs
  Depends: T001
  Effort: M
  Prompt-rules: ARCH-001
  Commit: feat(ledger): add Account entity

T003 [P] [US1] [Layer:domain] Create Transaction value object
  Service: ledger-service
  Files: src/ledger-service/domain/models/Transaction.cs
  Depends: T001
  Effort: S
  Prompt-rules: ARCH-001
  Commit: feat(ledger): add Transaction value object

...

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 28 |
| Effort breakdown | S:8, M:10, L:6, XL:4 |
| Parallelizable | 12 (43%) |
| Cross-service deps | 2 |
```

### Rich Console Output

On successful generation:
```
✅ Generated tasks for ledger-service (28 tasks)
   S:8  M:10  L:6  XL:4  |  12 parallel  |  2 cross-deps
```

On full-project generation:
```
✅ Task generation complete
   identity-service:  22 tasks
   ledger-service:    28 tasks
   notification-svc:  18 tasks
   cross-service-infra: 5 tasks
   ─────────────────────────
   Total: 73 tasks across 4 files
```
