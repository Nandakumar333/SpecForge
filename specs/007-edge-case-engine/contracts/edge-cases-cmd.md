# Contract: specforge edge-cases CLI Command

**Feature**: 007-edge-case-engine

## Command Signature

```
specforge edge-cases <target>
```

**Arguments**:
- `target` (required): Service slug (e.g., `ledger-service`) or feature number (e.g., `002`)

**Options**: None (Phase 1 — future: `--format yaml|markdown`, `--severity-filter`)

## Behavior

### Success Path (exit code 0)

1. Resolves `target` to service slug via `resolve_target()`
2. Loads `ServiceContext` from `manifest.json`
3. Acquires pipeline lock
4. Loads YAML patterns, filters by architecture, runs analyzer
5. Renders `edge-cases.md` to `.specforge/features/<slug>/edge-cases.md`
6. Updates pipeline state: `edgecase` phase → `complete`
7. Releases lock
8. Prints summary: count, severity breakdown, output path

### Error Paths (exit code 1)

| Condition | Error Message |
|-----------|--------------|
| No manifest.json | `Error: manifest.json not found at .specforge/manifest.json` |
| Unknown service slug | `Error: Service 'X' not found in manifest.json` |
| No spec.md | `Error: spec.md not found at .specforge/features/<slug>/spec.md` |
| Pipeline lock held | `Error: Pipeline lock held by another process` |
| Template rendering failure | `Error: Template error: <details>` |

### Output Format

```
Analyzing edge cases for ledger-service...
Architecture: microservice (2 dependencies, 1 event)
Generated 14 edge cases (3 critical, 5 high, 4 medium, 2 low)
Written to: .specforge/features/ledger-service/edge-cases.md
```

## Pipeline Integration

When invoked by `PipelineOrchestrator` as Phase 3b:
- Runs in parallel with Phase 3a (datamodel)
- Receives `input_artifacts` dict with prior phase outputs
- Returns `Ok(artifact_path)` or `Err(message)`
- Orchestrator handles state updates
