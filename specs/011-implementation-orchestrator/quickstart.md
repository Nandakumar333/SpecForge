# Quickstart: Implementation Orchestrator

**Feature**: 011-implementation-orchestrator

## Prerequisites

- SpecForge project initialized (`specforge init`)
- Architecture decomposed (`specforge decompose`) — manifest.json exists with services and dependencies
- All services have spec artifacts (at minimum `tasks.md` in `.specforge/features/<slug>/`)
- For microservice mode: Docker and docker-compose installed and available on PATH

## Basic Usage

### Implement all services (microservice mode)

```bash
specforge implement --all
```

This will:
1. Build shared infrastructure (contracts, docker-compose, gateway)
2. Implement services in dependency-ordered phases
3. Verify contracts between phases
4. Run full integration test at the end
5. Generate an integration report

### Implement up to a specific phase

```bash
specforge implement --all --to-phase 2
```

Implements shared infra + Phase 1 + Phase 2 only. Useful for incremental development.

### Resume after interruption

```bash
specforge implement --all --resume
```

Picks up from last completed phase/service. Already-completed work is not re-run.

### Implement all (monolith mode)

```bash
specforge implement --all
```

Same command — the orchestrator auto-detects monolith mode from the manifest and skips Docker, contract tests, and container health checks.

## Expected Output

```
╭─ Implementation Orchestrator ──────────────────────────╮
│                                                         │
│  Architecture: microservice                             │
│  Services: 8  │  Phases: 3                              │
│                                                         │
│  Pre-phase: Shared Infrastructure                       │
│    ✅ contracts library                                  │
│    ✅ docker-compose base                                │
│    ✅ API gateway skeleton                               │
│                                                         │
│  Phase 1: Foundation                                    │
│    ✅ identity-service (12/12 tasks)                     │
│    ✅ admin-service (8/8 tasks)                          │
│  Verification: ✅ contracts OK  ✅ boundaries OK         │
│                                                         │
│  Phase 2: Core                                          │
│    ✅ ledger-service (15/15 tasks)                       │
│    ✅ portfolio-service (10/10 tasks)                    │
│    ✅ integration-service (9/9 tasks)                    │
│  Verification: ✅ contracts OK  ✅ boundaries OK         │
│                                                         │
│  Phase 3: Dependent                                     │
│    ✅ planning-service (11/11 tasks)                     │
│    ✅ analytics-service (13/13 tasks)                    │
│    ✅ notification-service (7/7 tasks)                   │
│  Verification: ✅ contracts OK  ✅ boundaries OK         │
│                                                         │
│  Integration: ✅ all health checks pass                  │
│               ✅ gateway routes verified                  │
│               ✅ request flow OK                          │
│               ✅ event propagation OK                     │
│                                                         │
│  Verdict: PASS                                          │
╰─────────────────────────────────────────────────────────╯
```

## Error Scenarios

### Contract violation detected

```
Phase 2 Verification: ❌ FAILED
  Contract mismatch: ledger-service ↔ identity-service
    Field: JWT claims.role
    Expected: string enum ["admin", "user", "readonly"]
    Actual: string (unconstrained)

  Halted before Phase 3. Fix contracts and re-run with --resume.
```

### Service failure within a phase

```
Phase 2:
  ✅ ledger-service (15/15 tasks)
  ❌ portfolio-service (failed at task T07)
  ✅ integration-service (9/9 tasks)

  Phase 2 partially complete (2/3 services).
  Halted before Phase 3. See diagnostic report for portfolio-service.
```
