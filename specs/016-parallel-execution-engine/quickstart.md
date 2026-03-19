# Quickstart: Parallel Execution Engine

**Feature**: 016-parallel-execution-engine

## Prerequisites

- SpecForge installed with Features 001-015
- AI provider configured in `.specforge/config.json` (e.g., `"agent": "claude"`)
- AI CLI tool available on PATH (e.g., `claude`)

## Parallel Spec Generation (decompose)

### Basic: Parallel with interactive prompts
```bash
specforge decompose "Personal Finance App" --parallel
```
Discovers services via AI, confirms interactively, then runs the 7-phase spec pipeline for all services concurrently.

### Fully automated: No prompts, parallel execution
```bash
specforge decompose "Personal Finance App" --auto --parallel
```
End-to-end: AI selects architecture, discovers services, generates all spec artifacts in parallel. No user interaction required.

### Rate-limited provider: Limit concurrency
```bash
specforge decompose "Personal Finance App" --auto --parallel --max-parallel 2
```
Runs at most 2 service pipelines simultaneously.

### CI mode: Stop on first failure
```bash
specforge decompose "Personal Finance App" --auto --parallel --fail-fast
```
Cancels all workers if any service fails.

## Parallel Implementation (implement)

### Dependency-ordered parallel implementation
```bash
specforge implement --all --parallel
```
Reads the dependency graph from manifest.json, groups services into waves, and runs each wave's services concurrently.

### Conservative parallel implementation
```bash
specforge implement --all --parallel --max-parallel 2 --fail-fast
```

## Monitoring Progress

### Inline progress (automatic)
Progress lines stream to the console during parallel execution. No extra setup needed.

### Dashboard (separate terminal)
```bash
specforge status --watch
```
Shows live progress bars for all services. Updates every 5 seconds.

## Configuration

In `.specforge/config.json`:
```json
{
  "parallel": {
    "max_workers": 4
  }
}
```

Override per-invocation with `--max-parallel N`.

## Resume After Interruption

If a parallel run is interrupted (Ctrl+C or failure), re-run the same command. Completed services are skipped automatically:
```bash
specforge decompose "Personal Finance App" --auto --parallel
# Resumes only incomplete services
```
