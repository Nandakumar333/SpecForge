# Contract: forge-state.json

## Location

`.specforge/forge-state.json`

## Schema

```json
{
  "schema_version": "1.0",
  "description": "string — original project description",
  "architecture": "monolithic | microservice | modular-monolith",
  "model": "string | null — model override if specified",
  "init_complete": "boolean",
  "decompose_complete": "boolean",
  "services": {
    "<service-slug>": {
      "phases_complete": ["spec", "research", ...],
      "phases_failed": ["edgecase"],
      "retry_count": 0,
      "error": "string | null",
      "last_update": "2026-03-19T10:30:00Z"
    }
  },
  "started_at": "2026-03-19T10:00:00Z",
  "last_update": "2026-03-19T10:30:00Z"
}
```

## Field Constraints

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| schema_version | string | yes | Must be "1.0" |
| description | string | yes | Non-empty |
| architecture | string | yes | One of: monolithic, microservice, modular-monolith |
| model | string | null | no | Model ID or null |
| init_complete | boolean | yes | — |
| decompose_complete | boolean | yes | — |
| services | object | yes | Keys are service slugs |
| services.*.phases_complete | string[] | yes | Subset of PIPELINE_PHASES |
| services.*.phases_failed | string[] | yes | Subset of PIPELINE_PHASES |
| services.*.retry_count | integer | yes | 0 ≤ n ≤ 3 |
| services.*.error | string | null | no | Last error message |
| services.*.last_update | string | yes | ISO 8601 timestamp |
| started_at | string | yes | ISO 8601 timestamp |
| last_update | string | yes | ISO 8601 timestamp |

## Valid Phase Names

Ordered pipeline phases: `spec`, `research`, `datamodel`, `edgecase`, `plan`, `checklist`, `tasks`

## Lifecycle

1. **Created**: At forge start (after determining description and architecture)
2. **Updated**: After each stage/phase completion or failure
3. **Read**: On `--resume` to determine what to skip
4. **Deleted**: Not auto-deleted; user may delete manually or `--force` overwrites

## Atomicity

Written via `os.replace()` (write to `.forge-state.json.tmp`, then atomic rename). Only the `ForgeOrchestrator` writes this file — no concurrent write contention.

## Resume Logic

When `--resume` is used:
1. Load `forge-state.json`
2. If `init_complete` is true, skip init
3. If `decompose_complete` is true, skip decompose
4. For each service: if all 7 phases are in `phases_complete`, skip the service
5. For incomplete services: start from the first phase not in `phases_complete`
6. If `retry_count >= 3`, mark as permanently failed and skip

## Corrupt State Handling

If `forge-state.json` exists but cannot be parsed (invalid JSON, missing required fields):
- Log warning: "Corrupt forge state detected, starting fresh run"
- Create new state, do not crash
