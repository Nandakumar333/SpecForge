# Manifest Schema Contract: manifest.json

**Feature**: 004-architecture-decomposer
**Date**: 2026-03-15
**Location**: `.specforge/manifest.json`

## Schema Version

`"1.0"` — migration logic deferred until schema changes (FR-042).

## Full Schema

```json
{
  "schema_version": "1.0",
  "architecture": "monolithic | microservice | modular-monolith",
  "project_description": "string — original user input",
  "domain": "string — matched domain pattern name or 'generic'",
  "features": [
    {
      "id": "string — zero-padded 3-digit (001, 002, ...)",
      "name": "string — kebab-case identifier",
      "display_name": "string — human-readable name",
      "description": "string — one-line description",
      "priority": "P0 | P1 | P2 | P3",
      "category": "foundation | core | supporting | integration | admin",
      "service": "string — service/module slug this feature belongs to"
    }
  ],
  "services": [
    {
      "name": "string — service display name",
      "slug": "string — kebab-case directory name",
      "features": ["string — feature IDs"],
      "rationale": "string — WHY COMBINED or WHY SEPARATE explanation",
      "communication": [
        {
          "target": "string — target service slug",
          "pattern": "sync-rest | sync-grpc | async-event",
          "required": true,
          "description": "string — purpose of this connection"
        }
      ]
    }
  ],
  "events": [
    {
      "name": "string — e.g., ledger.transaction.created",
      "producer": "string — service slug",
      "consumers": ["string — service slugs"],
      "payload_summary": "string — brief description of event data"
    }
  ]
}
```

## Validation Rules (FR-053)

After writing `manifest.json`, the system reads it back and validates:

| Check | Rule | Error on Failure |
|-------|------|------------------|
| Valid JSON | File parses as JSON | "manifest.json is not valid JSON" |
| Schema version | `schema_version` field present and equals `"1.0"` | "Missing or invalid schema_version" |
| Architecture | `architecture` is one of 3 valid values | "Invalid architecture value: '{value}'" |
| Unique feature IDs | Every `features[].id` is unique | "Duplicate feature ID: '{id}'" |
| Service references | Every `features[].service` references an existing `services[].slug` | "Feature '{id}' references unknown service '{slug}'" |
| No feature duplication | No feature ID appears in more than one `services[].features` array | "Feature '{id}' appears in multiple services" |
| Feature coverage | Every feature has a service assignment | "Feature '{id}' has no service assignment" |
| Communication targets | Every `communication[].target` references an existing service slug | "Communication target '{slug}' does not exist" |
| Event producers | Every `events[].producer` references an existing service slug | "Event producer '{slug}' does not exist" |
| Event consumers | Every `events[].consumers[]` references an existing service slug | "Event consumer '{slug}' does not exist" |

## Architecture-Specific Behavior

### Monolithic

- `services` array contains exactly 1 entry with all feature IDs
- `services[0].slug` is the project name in kebab-case
- `services[0].rationale` = "Monolithic architecture: all features as modules within a single application"
- `services[0].communication` is empty
- `events` array is empty

### Microservice

- `services` array contains multiple entries
- Each service has 1–4 features
- `communication` links between dependent services
- `events` populated for async communication patterns

### Modular Monolith

- Same structure as Microservice (one entry per module)
- `architecture` field is `"modular-monolith"`
- `communication` links represent logical boundaries (same deployment, enforced module contracts)
- `events` may be populated for internal event-driven patterns

## Downstream Consumers

The `manifest.json` schema is the contract for all downstream SpecForge features (005–013). Changes to this schema require a `schema_version` bump and backward-compatible migration logic.

| Consumer | Fields Used |
|----------|-------------|
| Feature spec generation (005) | `features[].id`, `features[].name`, `features[].description` |
| Per-feature pipeline (006+) | `features[].service`, `services[].slug` |
| Architecture-aware prompts (future) | `architecture` |
| Dependency ordering (future) | `services[].communication`, `events` |
