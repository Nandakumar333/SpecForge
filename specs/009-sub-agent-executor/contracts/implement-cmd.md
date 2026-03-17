# CLI Contract: specforge implement

**Feature**: 009-sub-agent-executor  
**Date**: 2026-03-17

## Command Signature

```
specforge implement <target> [--shared-infra] [--resume] [--mode MODE] [--max-fix-attempts N]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `target` | Conditional | Service slug or module name. Required unless `--shared-infra` is used. |

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--shared-infra` | flag | false | Build cross-service infrastructure from `cross-service-infra/tasks.md` |
| `--resume` | flag | false | Resume from last completed task (requires `target`) |
| `--mode` | choice | `prompt-display` | Execution mode: `prompt-display` (show prompt) or `agent-call` (call agent) |
| `--max-fix-attempts` | int | 3 | Maximum auto-fix retry attempts per task |

## Mutual Exclusion

- `target` and `--shared-infra` are mutually exclusive: provide exactly one.
- `--resume` requires `target` (cannot resume shared infrastructure).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tasks completed successfully |
| 1 | Execution halted: auto-fix loop exhausted for a task |
| 2 | Invalid arguments (missing target, invalid options) |
| 3 | Prerequisites missing (spec artifacts, shared infra) |
| 4 | Lock conflict (another implementation is running for this service) |

## Example Usage

```bash
# Implement a single service (Mode A — prompts displayed for manual execution)
specforge implement ledger-service

# Implement with agent-call mode
specforge implement ledger-service --mode agent-call

# Build shared infrastructure first
specforge implement --shared-infra

# Resume after interruption
specforge implement --resume ledger-service

# Custom retry limit
specforge implement ledger-service --max-fix-attempts 5
```

## Output Behavior

### Mode A (prompt-display)

For each task:
1. Rich panel displaying the implementation prompt
2. Interactive prompt: `Task complete? [y/n/skip]`
3. On `y`: runs quality checks, shows pass/fail results
4. On failure: displays auto-fix prompt, repeats confirmation
5. On success: shows commit message, advances to next task

### Mode B (agent-call)

For each task:
1. Progress spinner with task description
2. Agent invocation (subprocess)
3. Quality check results displayed
4. On failure: auto-fix loop runs automatically
5. On success: commit message displayed, advances

### Shared Infrastructure

Same as service implementation, but:
- Context is project-wide (all service specs)
- Commits land on current working branch
- Output: shared contracts, docker-compose, gateway skeleton

### Completion Summary

After all tasks (or on halt):
```
Implementation Summary: ledger-service
  Tasks completed: 12/14
  Tasks failed: 1 (T013 — contract tests)
  Tasks skipped: 1 (T014 — gateway config)
  Auto-fix attempts: 5 (3 successful, 2 exhausted)
  Commits created: 12
  Verification: Docker ✓ | Health ✓ | Contracts ✗
```
