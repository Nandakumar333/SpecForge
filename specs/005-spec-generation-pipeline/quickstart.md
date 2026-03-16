# Quickstart — Spec Generation Pipeline

## Prerequisites

1. Feature 004 complete: `specforge decompose` has been run and `.specforge/manifest.json` exists
2. Python 3.11+ with `specforge` installed (`uv tool install specforge`)

## Usage

### Generate all artifacts for a service

```bash
specforge specify ledger-service
```

### Generate using feature number

```bash
specforge specify 002
# Resolves to ledger-service, generates for entire service
```

### Resume from a specific phase

```bash
specforge specify ledger-service --from plan
# Skips spec, research, datamodel/edgecase; runs plan, checklist, tasks
```

### Force regenerate everything

```bash
specforge specify ledger-service --force
```

### Check pipeline status

```bash
specforge pipeline-status              # all services
specforge pipeline-status ledger-service  # specific service
```

## Output

All artifacts are written to `.specforge/features/<service-slug>/`:

```text
.specforge/features/ledger-service/
├── .pipeline-state.json    # Phase completion tracking
├── spec.md                 # Service specification (all features unified)
├── research.md             # Technical research
├── data-model.md           # Entities scoped to service boundary
├── edge-cases.md           # Failure scenarios (architecture-aware)
├── plan.md                 # Implementation plan (architecture-aware)
├── checklist.md            # Quality validation
├── tasks.md                # Ordered implementation tasks
└── contracts/              # Microservice only
    └── api-spec.json       # Simplified API contract
```

## Architecture Behavior

- **Microservice**: plan.md includes Docker, health checks, circuit breakers; data-model.md is isolated; contracts/ generated
- **Monolithic**: plan.md references shared infra; data-model.md can reference shared_entities.md
- **Modular-monolith**: like monolith + interfaces.md for boundary contracts + stricter checklist
