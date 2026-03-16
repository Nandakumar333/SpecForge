# CLI Contract: specforge decompose

**Feature**: 004-architecture-decomposer
**Date**: 2026-03-15

## Command Signature

```
specforge decompose <description> [OPTIONS]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `description` | `str` | Yes | One-line application description (e.g., "Create a personal finance webapp") |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--arch` | `Choice[monolithic\|microservice\|modular-monolith]` | None | Skip interactive architecture prompt; use specified value directly (FR-035) |
| `--remap` | `Choice[monolithic\|microservice\|modular-monolith]` | None | Re-map existing features to new architecture (FR-030) |
| `--no-warn` | `Flag` | False | Suppress over-engineering warning (FR-046) |

### Mutual Exclusions

- `--arch` and `--remap` MUST NOT be used together → exit code 1 with message (FR-048)

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — manifest.json written and validated |
| 1 | Error — invalid arguments, validation failure, or user abort |

## Interactive Flow

### First Run (no existing manifest)

```
$ specforge decompose "Create a personal finance webapp"

┌─ Architecture Selection ────────────────────────────┐
│ 1. Monolithic — Single deployable, features as      │
│    modules                                          │
│ 2. Microservice — Independent services per bounded  │
│    context                                          │
│ 3. Modular Monolith — Single deployable, strict     │
│    module boundaries                                │
└─────────────────────────────────────────────────────┘
Select architecture [1/2/3] (1):

Analyzing description...
Domain detected: finance (score: 12)

Features identified:
┌─────┬─────────────────────────┬──────────┬──────────┐
│ ID  │ Name                    │ Priority │ Category │
├─────┼─────────────────────────┼──────────┼──────────┤
│ 001 │ Authentication          │ P0       │ foundation│
│ 002 │ Account Management      │ P1       │ core     │
│ ...                                                  │
└─────┴─────────────────────────┴──────────┴──────────┘

[If microservice/modular-monolith]:
Service Mapping:
┌─────────────────────┬──────────────┬────────────────────────┐
│ Service             │ Features     │ Rationale              │
├─────────────────────┼──────────────┼────────────────────────┤
│ Identity Service    │ 001          │ WHY SEPARATE: Auth ... │
│ Ledger Service      │ 002, 003     │ WHY COMBINED: Shared...│
│ ...                                                         │
└─────────────────────┴──────────────┴────────────────────────┘

Edit mapping (combine/split/rename/add/remove/done) (done):

✓ Manifest written to .specforge/manifest.json
✓ Communication map written to .specforge/communication-map.md
✓ Feature directories created under .specforge/features/
```

### Subsequent Run (existing manifest)

```
$ specforge decompose "Create a personal finance webapp"

Existing decomposition found (.specforge/manifest.json)
What would you like to do?
  1. Resume from last step
  2. Start fresh (overwrites existing)
Select [1/2] (1):
```

### With --arch Flag (non-interactive)

```
$ specforge decompose --arch microservice "Create a personal finance webapp"
# Skips architecture prompt, proceeds directly to domain analysis
```

### Over-engineering Warning

```
$ specforge decompose --arch microservice "Build a TODO app"

⚠ Warning: This project has 3 features. Microservices may be
  over-engineering. Consider Modular Monolith.
  Proceed with Microservice anyway? [y/N] (N):
```

### Re-mapping (--remap)

| Transition | Behavior |
|-----------|----------|
| monolithic → microservice | Features preserved. Service mapping runs on existing features. Directories renamed per new service slugs. |
| monolithic → modular-monolith | Features preserved. Module mapping runs. Directory structure unchanged (same layout). |
| microservice → monolithic | Service boundaries removed. All features become modules in single service. Existing spec files preserved. |
| microservice → modular-monolith | Manifest `architecture` field updated. Service structure preserved. No directory changes. |
| modular-monolith → monolithic | Module boundaries removed. Same as micro→mono. |
| modular-monolith → microservice | Manifest `architecture` field updated. Module structure preserved as services. |

In all transitions, existing spec/plan/tasks files in feature directories are NEVER deleted (FR-031).

### --no-warn

Suppressed with `--no-warn`:
```
$ specforge decompose --arch microservice --no-warn "Build a TODO app"
# No warning, proceeds directly
```

### Edit Commands (Interactive Review)

| Command | Syntax | Example |
|---------|--------|---------|
| Combine | `combine <service1> <service2>` | `combine ledger-service portfolio-service` |
| Split | `split <service> <feature_id>` | `split ledger-service 003` |
| Rename | `rename <service> <new-name>` | `rename ledger-service accounting-service` |
| Add | `add <service-name>` | `add analytics-service` |
| Remove | `remove <service>` | `remove reporting-service` (user prompted to reassign each feature) |
| Override | `override <service> <target> <pattern>` | `override ledger-service identity-service sync-grpc` |
| Done | `done` | Finalize mapping |

**Remove behavior**: When a service is removed, the system lists its features and prompts the user to reassign each one to an existing service. No feature may remain unassigned.

**Override behavior**: Changes the communication pattern between two services. Valid patterns: `sync-rest`, `sync-grpc`, `async-event`. Satisfies FR-027 user override requirement.

### Error Messages

| Condition | Message |
|-----------|---------|
| Invalid `--arch` value | `Invalid architecture '{value}'. Valid options: monolithic, microservice, modular-monolith` |
| `--arch` + `--remap` | `Cannot use --arch and --remap together. Use --arch for new projects or --remap to change existing architecture.` |
| Gibberish input | `Could not understand the description. Try something like:\n  specforge decompose "Create a personal finance webapp"\n  specforge decompose "Build an e-commerce platform"\n  specforge decompose "Create a social media app"` |
| Feature in 2 services | `Error: Feature '{id}' ({name}) is assigned to multiple services: {service1}, {service2}. Each feature must belong to exactly one service.` |
| Circular dependency | `Circular dependency detected: {service_a} → {service_b} → ... → {service_a}. Consider breaking with async events or shared contracts.` |

## Output Files

| File | Condition | Description |
|------|-----------|-------------|
| `.specforge/manifest.json` | Always | Central project descriptor |
| `.specforge/communication-map.md` | Microservice/Modular Monolith | Mermaid dependency diagram |
| `.specforge/features/{slug}/` | Always | One directory per service/module |
| `.specforge/decompose-state.json` | During flow | Temporary state file (deleted on completion) |
