# Feature Specification: Edge Case Analysis Engine

**Feature Branch**: `007-edge-case-engine`
**Created**: 2026-03-17
**Status**: Draft
**Input**: User description: "Build the edge case analysis engine that produces edge-cases.md per service"

## User Scenarios & Testing

### User Story 1 — Microservice Edge Cases with Inter-Service Failures (Priority: P1)

As a developer building a microservice-based application, I want the edge case engine to automatically generate edge cases that cover inter-service failure scenarios specific to my service's dependency map so that I know exactly what resilience patterns to implement before writing code.

The engine reads `manifest.json` to discover which services the target depends on (via `communication[]` entries) and what events it produces/consumes. It then generates context-specific edge cases — not generic placeholders but real failure scenarios grounded in the service topology. For example, if ledger-service has a `sync-rest` required dependency on identity-service, it produces "identity-service down during token validation" with a circuit breaker recommendation, not just "dependent service unavailable."

**Why this priority**: Inter-service failures are the #1 cause of production incidents in microservice architectures. Without explicit edge case coverage, developers discover these failure modes in production.

**Independent Test**: Can be fully tested by providing a microservice manifest with known dependencies and verifying the generated edge-cases.md contains dependency-specific failure scenarios with recommended patterns.

**Acceptance Scenarios**:

1. **Given** architecture=microservice in manifest.json and ledger-service has a required sync-rest dependency on identity-service, **When** edge-cases.md is generated for ledger-service, **Then** it includes a "Service Unavailability" edge case mentioning identity-service with circuit breaker / cached token / fail-closed as handling strategies
2. **Given** ledger-service produces `transaction.created` events consumed by analytics-service, **When** edge-cases.md is generated for ledger-service, **Then** it includes an "Eventual Consistency" edge case covering the propagation delay window with stale-data handling strategies
3. **Given** ledger-service has both sync and async dependencies, **When** edge-cases.md is generated, **Then** sync dependencies produce timeout/circuit-breaker cases and async dependencies produce message-loss/ordering cases
4. **Given** a service with no external dependencies, **When** edge-cases.md is generated, **Then** it omits inter-service failure categories and only includes standard categories

---

### User Story 2 — Monolith Mode with Standard Categories (Priority: P1)

As a developer in monolith mode, I want simpler edge cases focused on concurrency, data boundaries, security, and state management — without distributed system concerns — so that the generated edge cases match my architecture's actual failure modes.

The engine detects `architecture=monolithic` from the manifest and generates edge cases from a standard category set: concurrency, data boundaries, state machine, UI/UX, security, and data migration. It does NOT include service-down, network partition, or eventual consistency scenarios.

**Why this priority**: Equal to P1 because monolith support is the other half of the architecture-aware design. An engine that only handles microservices is incomplete.

**Independent Test**: Can be fully tested by providing a monolith manifest and verifying the generated edge-cases.md contains only standard categories and zero distributed system scenarios.

**Acceptance Scenarios**:

1. **Given** architecture=monolithic in manifest.json, **When** edge-cases.md is generated for an auth module, **Then** it includes concurrency, data boundary, security, and state machine edge cases
2. **Given** architecture=monolithic, **When** edge-cases.md is generated, **Then** it does NOT contain "Service Down", "Network Partition", "Eventual Consistency", or "Distributed Transaction" categories
3. **Given** architecture=modular-monolith, **When** edge-cases.md is generated, **Then** it includes standard monolith categories PLUS interface contract violation edge cases

---

### User Story 3 — Machine-Parseable YAML Frontmatter for Sub-Agent Consumption (Priority: P2)

As the Feature 009 sub-agent, I need each edge case in a machine-parseable format with structured metadata so I can cross-reference edge cases during implementation to ensure each one has corresponding test coverage.

Each edge case in edge-cases.md includes YAML frontmatter with fields: `id`, `category`, `severity`, `affected_services`, `handling_strategy`, and `test_suggestion`. The sub-agent can parse these blocks to build a checklist of edge-case tests that must pass before a service is considered complete.

**Why this priority**: Machine parseability is required for downstream automation but doesn't block human use of the edge case output.

**Independent Test**: Can be tested by generating edge-cases.md and programmatically parsing all YAML frontmatter blocks, verifying each has the required fields and valid values.

**Acceptance Scenarios**:

1. **Given** edge-cases.md is generated for any service, **When** a YAML parser reads each edge case block, **Then** every case has: `id` (EC-NNN format), `category`, `severity` (critical/high/medium/low), `affected_services` (list), `handling_strategy`, `test_suggestion`
2. **Given** a microservice edge case about identity-service being down, **When** the sub-agent parses it, **Then** `affected_services` includes both the target service and the dependency service
3. **Given** a monolith edge case, **When** the sub-agent parses it, **Then** `affected_services` contains only the target module name

---

### User Story 4 — Pipeline Integration as Phase 3b (Priority: P2)

As the spec-generation pipeline (Feature 005), I need the edge case engine to execute as Phase 3b running in parallel with data-model generation (Phase 3a) so that the pipeline produces edge-cases.md without blocking other phases.

The engine integrates with the existing `PipelineOrchestrator` as a registered phase. It acquires the pipeline lock, loads service context, delegates to the edge case analyzer, renders the Jinja2 template, and updates pipeline state to `complete` with artifact paths.

**Why this priority**: Pipeline integration is the delivery mechanism but not the core analysis logic — the engine must produce correct edge cases first.

**Independent Test**: Can be tested by invoking the CLI command directly and verifying pipeline state is updated to `complete` for the `edgecase` phase with the correct artifact path.

**Acceptance Scenarios**:

1. **Given** the pipeline is running for ledger-service and Phase 2 (research) is complete, **When** Phase 3 executes, **Then** Phase 3a (datamodel) and Phase 3b (edgecase) run in parallel
2. **Given** Phase 3b completes successfully, **When** pipeline state is checked, **Then** the `edgecase` phase status is `complete` with artifact path pointing to edge-cases.md
3. **Given** Phase 3b fails (e.g., template rendering error), **When** pipeline state is checked, **Then** the `edgecase` phase status is `failed` with an error message and Phase 4 does not proceed

---

### User Story 5 — Standalone CLI Command (Priority: P3)

As a developer, I want to run the edge case engine independently via `specforge edge-cases <target>` so I can regenerate edge cases for a specific service without re-running the entire pipeline.

**Why this priority**: Standalone execution is a convenience feature for iterative development — the pipeline integration (US4) handles the primary flow.

**Independent Test**: Can be tested by invoking `specforge edge-cases ledger-service` directly and verifying edge-cases.md is produced with correct content.

**Acceptance Scenarios**:

1. **Given** manifest.json exists and ledger-service has a spec.md, **When** `specforge edge-cases ledger-service` is run, **Then** edge-cases.md is written to `.specforge/features/ledger-service/edge-cases.md`
2. **Given** a feature number "002", **When** `specforge edge-cases 002` is run, **Then** the target resolves to ledger-service and edge cases are generated for that service
3. **Given** no manifest.json exists, **When** `specforge edge-cases ledger-service` is run, **Then** exit code 1 with a clear error message

---

### Edge Cases

- What happens when manifest.json has zero services? Engine produces an error, not an empty file.
- What happens when a service has zero dependencies but architecture is microservice? Engine generates only intra-service edge cases (concurrency, data boundaries) plus architecture-generic microservice cases (container health, readiness probes) — no inter-service failure cases.
- What happens when spec.md is empty? Engine produces minimal edge cases derived from manifest features only — the spec content enriches but is not required.
- What happens when the manifest has circular dependencies (A→B→A)? Engine detects the cycle and generates a "circular dependency" edge case rather than infinite-looping.
- What happens when two services share the same entity? Engine generates a "data ownership conflict" edge case specifying the shared entity and asking who is source of truth.

## Requirements

### Functional Requirements

- **FR-001**: System MUST read `manifest.json` to determine the architecture type and produce architecture-appropriate edge case categories
- **FR-002**: For microservice architecture, system MUST generate inter-service failure edge cases derived from actual `communication[]` entries: service unavailability, network partition, eventual consistency, distributed transaction failure, version skew, and data ownership conflict
- **FR-003**: For monolith architecture, system MUST generate edge cases from standard categories only: concurrency, data boundaries, state machine, UI/UX, security, and data migration
- **FR-004**: For modular-monolith architecture, system MUST generate standard monolith categories PLUS interface contract violation edge cases
- **FR-005**: Each generated edge case MUST include: scenario description, severity level, affected service(s), recommended handling strategy, and test suggestion
- **FR-006**: Each edge case MUST include a YAML frontmatter block with machine-parseable fields: `id`, `category`, `severity`, `affected_services`, `handling_strategy`, `test_suggestion`
- **FR-007**: Edge case IDs MUST follow the pattern `EC-NNN` with sequential numbering per service
- **FR-008**: For microservice edge cases, the system MUST use the actual service dependency graph from `communication[]` to name the specific dependent service in the edge case scenario (e.g., "identity-service down" not "a dependent service down")
- **FR-009**: For microservice edge cases involving events, the system MUST use the actual `events[]` entries to name the specific event and its consumers in eventual consistency scenarios
- **FR-010**: System MUST render edge-cases.md via the existing `edge-cases.md.j2` Jinja2 template (enhanced to support YAML frontmatter)
- **FR-011**: System MUST update pipeline state to `complete` for the `edgecase` phase after successful generation
- **FR-012**: System MUST be invocable as a standalone CLI command `specforge edge-cases <target>` where target is a service slug or feature number
- **FR-013**: System MUST acquire and release the pipeline lock during execution to prevent concurrent modification
- **FR-014**: System MUST detect shared entities across service boundaries (using BoundaryAnalyzer patterns) and generate "data ownership conflict" edge cases for each shared entity
- **FR-015**: System MUST skip inter-service failure categories when the target service has zero external dependencies, even in microservice architecture
- **FR-016**: Severity levels MUST be one of: `critical`, `high`, `medium`, `low` — derived from the dependency's `required` flag and communication pattern
- **FR-017**: System MUST use the existing `ArchitectureAdapter.get_edge_case_extras()` for architecture-generic edge cases and layer service-specific edge cases on top

### Key Entities

- **EdgeCase**: Represents a single edge case with id, category, severity, scenario, affected services, handling strategy, and test suggestion
- **EdgeCaseCategory**: The classification of an edge case — microservice categories (service_unavailability, network_partition, eventual_consistency, distributed_transaction, version_skew, data_ownership) or standard categories (concurrency, data_boundary, state_machine, ui_ux, security, data_migration)
- **EdgeCaseReport**: The aggregate of all edge cases for a service, consumed by the template renderer to produce edge-cases.md

## Success Criteria

### Measurable Outcomes

- **SC-001**: Edge cases generated for a microservice with N dependencies include at least 2×N inter-service failure scenarios (covering primary failure modes per dependency)
- **SC-002**: Edge cases generated for a monolith contain zero distributed-system categories (no service-down, network partition, eventual consistency references)
- **SC-003**: 100% of generated edge cases have valid YAML frontmatter parseable by a standard YAML parser with all required fields present
- **SC-004**: Edge case generation for a 5-service PersonalFinance manifest completes in under 2 seconds
- **SC-005**: The Feature 009 sub-agent can programmatically extract all edge case IDs, categories, and test suggestions from the generated file without manual intervention
- **SC-006**: Developers reviewing edge-cases.md can identify the specific services, events, and failure scenarios relevant to their service without cross-referencing other documents

## Assumptions

- The `manifest.json` schema from Feature 004 is stable and all `communication[]` and `events[]` fields are populated
- The existing `edge-cases.md.j2` template will be enhanced (not replaced) to support YAML frontmatter per edge case block
- The `ArchitectureAdapter` protocol from Feature 005 provides base edge case extras that this engine enriches with service-specific context
- Feature 005 pipeline orchestrator handles Phase 3a/3b parallelism; this engine only needs to function as a callable phase
- The `BoundaryAnalyzer` from Feature 006 provides the shared-entity detection capability reusable for data ownership conflict edge cases
