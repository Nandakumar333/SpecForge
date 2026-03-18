# Research: Implementation Orchestrator

**Feature**: 011-implementation-orchestrator
**Date**: 2026-03-17

## R-001: Topological Sort for Dependency Phasing

**Decision**: Use Kahn's algorithm (BFS-based topological sort) to compute execution phases from the service dependency graph.

**Rationale**: Kahn's algorithm naturally produces the topological ordering in layers (phases) — each BFS iteration yields all nodes with zero in-degree, which corresponds exactly to "services whose dependencies are all satisfied." It also detects cycles as a side effect (if not all nodes are processed, there's a cycle). This is simpler than DFS-based approaches for the phase-grouping use case.

**Alternatives considered**:
- DFS-based topological sort: produces a linear ordering but doesn't naturally group into phases. Would require a separate pass to compute the longest path from each node to determine phase assignment.
- External library (networkx): Would add a dependency to `core/` which must have zero external dependencies per Constitution Principle II.

**Implementation pattern**: Pure function `compute_phases(services, dependencies) → Result[tuple[Phase, ...], str]` operating on frozen dataclasses. Cycle detection via `detect_cycles()` returns the specific cycle path for error reporting.

## R-002: Inter-Phase Contract Verification Strategy

**Decision**: Compare contract files (.json schema, .md specs) from publisher services against consumer expectations using structural comparison. Verification is declarative (file-based), not behavioral (no running services needed).

**Rationale**: Contract files are already produced by Feature 009's sub-agent executor during service implementation. Each service publishes its API contracts in `.specforge/features/<slug>/contracts/`. The enforcer loads consumer-side expectations (declared in tasks.md or generated during implementation) and compares against provider-side published contracts.

**Alternatives considered**:
- Pact-style consumer-driven contract testing: Requires running services and a broker. Too heavyweight for the pre-deployment verification phase. Better suited for the final integration validation.
- Code inspection: Would require language-specific parsers and couples the enforcer to implementation details. Contracts are the abstraction layer.
- Schema comparison only: Too narrow — misses behavioral contracts (response codes, error formats). Using both schema and markdown-based contract comparison.

## R-003: docker-compose Integration Validation

**Decision**: Use subprocess calls to `docker compose up -d` with the project's own docker-compose files. Health check polling via HTTP requests. Teardown via `docker compose down`.

**Rationale**: The shared infra pre-phase (Feature 009 US4) already generates docker-compose configuration. Using the same files for validation ensures test fidelity. The existing `DockerManager` class provides `build_image()` and `health_check()` but operates on individual services — `IntegrationTestRunner` extends this to orchestrate all services together.

**Alternatives considered**:
- Testcontainers: Adds Java/language-specific dependency. Violates Clean Architecture (external dependency in core). Not needed since docker-compose files already exist.
- Manual container orchestration (docker run per service): More complex, doesn't test the actual compose topology (networking, volumes, etc.).

## R-004: Orchestration State Persistence Pattern

**Decision**: Follow the atomic-write pattern established by `pipeline_state.py` and `execution_state.py`: write to temp file → fsync → atomic rename via `os.replace()`.

**Rationale**: Consistent with existing codebase patterns. Atomic writes prevent corruption on interrupt. The state file is small (JSON, < 100KB even for 20 services) so full-write is simpler than incremental updates.

**State file location**: `.specforge/orchestration-state.json` at project root (distinct from per-service state files in `.specforge/features/<slug>/`).

**State schema**: Tracks phases (with status), services per phase (with status and result), verification results per phase boundary, and overall status. Supports `--resume` by loading state and skipping completed phases/services.

## R-005: Monolith Mode Simplification

**Decision**: In monolith mode, the orchestrator uses the same core loop (compute phases → execute → verify → report) but substitutes: (1) no shared-infra pre-phase, (2) boundary compliance checks instead of contract verification, (3) single-app integration test instead of docker-compose.

**Rationale**: Using the same orchestration loop with architecture-specific behavior injected via the adapter pattern keeps the codebase DRY while allowing each mode to have its own verification and integration strategy. The `ArchitectureAdapter` protocol already exists for this purpose.

**Alternatives considered**:
- Separate `MonolithOrchestrator` class: Would duplicate the core phase loop. The behavioral differences are in 3 specific methods (pre-phase, verify, integrate), not in the overall flow.
- Feature flags within methods: Would lead to scattered if/else blocks. Adapter pattern localizes all mode-specific decisions.

## R-006: Database-per-Service Enforcement

**Decision**: In microservice mode, each service owns its own database. The contract enforcer verifies no cross-service direct database access by checking that services don't reference other services' database connection strings or table names. In monolith mode, modules own distinct schemas — boundary compliance checks (Feature 010's `BoundaryChecker`) verify this.

**Rationale**: Database-per-service is the canonical microservice pattern. It enforces data ownership and prevents tight coupling. The existing `BoundaryAnalyzer` (Feature 006) already detects shared entities; the contract enforcer extends this to verify database isolation.

## R-007: Progress Display Strategy

**Decision**: Use Rich's `Tree` and `Table` widgets for real-time progress display. Phase map shown as a tree with status indicators (✅ ⏳ ❌ ⏸). Per-service progress within active phase shown as a table.

**Rationale**: Rich is already a project dependency used throughout the CLI. `Tree` naturally represents the hierarchical phase → service structure. `Table` provides clean columnar layout for service status within a phase.

## R-008: --to-phase Partial Execution

**Decision**: `--to-phase N` limits execution to phases 0 through N (inclusive). Shared infra pre-phase always runs (it's phase 0). Integration validation is skipped unless all phases complete (or `--to-phase` equals the total phase count).

**Rationale**: Incremental execution enables developers to build and verify in stages. Shared infra must always run because all services depend on it. Skipping final integration when not all services are built avoids false failures.
