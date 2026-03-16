# Feature Specification: Spec Generation Pipeline

**Feature Branch**: `005-spec-generation-pipeline`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "Build the spec generation pipeline that creates all artifacts for each SERVICE (microservice mode) or MODULE (monolith mode)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Service Specification Generation (Priority: P1)

As a developer, I want to run `specforge specify <service-or-module>` to generate a complete specification covering all features mapped to that service or module, so that I have a single unified document describing everything the service must do.

The pipeline reads the existing `manifest.json` (produced by Feature 004) to determine which features belong to the target service. It then generates `spec.md` containing user stories for every mapped feature, organized by domain capability (not by original feature number). For microservice architectures, a "Service Dependencies" section lists consumed services and communication patterns.

The command accepts both service slugs (e.g., `specforge specify ledger-service`) and feature numbers (e.g., `specforge specify 002`). When a feature number is provided, it auto-resolves to the owning service via manifest.json lookup.

For services containing 4 or more features, user stories in spec.md are grouped into domain capability sub-sections to maintain readability (e.g., a Planning Service with budgets, bills, and goals would have sub-sections for "Budget Management", "Bill Tracking", and "Goal Planning").

**Why this priority**: Without the ability to generate a spec for a service, no other pipeline phases can run. This is the foundational capability that everything else depends on.

**Independent Test**: Can be fully tested by running `specforge specify identity-service` against a manifest that maps authentication features to identity-service. Delivers a complete spec.md in the service's feature directory.

**Acceptance Scenarios**:

1. **Given** a manifest.json mapping Feature 001 (auth) to identity-service, **When** I run `specforge specify identity-service`, **Then** spec.md is created in `.specforge/features/identity-service/` containing user stories for authentication, login, sessions, and profile management.
2. **Given** a manifest.json mapping Features 002 (Accounts) and 003 (Transactions) to ledger-service, **When** I run `specforge specify ledger-service`, **Then** spec.md contains unified user stories organized by domain capability (Account Management, Transaction Processing), not by feature number.
3. **Given** a manifest.json with architecture=microservice, **When** spec.md is generated for ledger-service, **Then** it includes a "Service Dependencies" section listing identity-service as a dependency with the communication pattern (sync-rest).
4. **Given** a manifest.json with architecture=monolithic, **When** spec.md is generated for the auth module, **Then** it describes the module within the monolith context without service dependency sections.
5. **Given** a manifest.json mapping Feature 002 to ledger-service, **When** I run `specforge specify 002`, **Then** the system resolves 002 to ledger-service and generates spec.md for the entire ledger-service (not just Feature 002).
6. **Given** a Planning Service containing 3 features (budgets, bills, goals), **When** spec.md is generated, **Then** user stories are grouped into sub-sections: "Budget Management", "Bill Tracking", and "Goal Planning".

---

### User Story 2 - Full Pipeline Execution with Phase Tracking (Priority: P1)

As a developer, I want the pipeline to execute all 6 phases sequentially (spec, research, data-model + edge-cases, plan, checklist, tasks) and track completion state, so that I can resume from any point if interrupted and re-run individual phases without redoing completed work.

Each phase writes its artifact(s) to the service's feature directory and updates `.pipeline-state.json` with completion status and timestamps. When re-running, the pipeline checks state and skips already-completed phases. A per-service lock file (`.pipeline-lock`) prevents concurrent runs against the same service while allowing different services to be processed in parallel.

**Why this priority**: Pipeline state tracking is essential for developer experience. Without it, every interruption forces a full restart, wasting time and potentially producing inconsistent artifacts.

**Independent Test**: Can be tested by running the full pipeline, verifying all 7 artifacts exist, then deleting one artifact and re-running to confirm only the missing phase executes.

**Acceptance Scenarios**:

1. **Given** no prior pipeline state for ledger-service, **When** I run `specforge specify ledger-service`, **Then** all 6 phases execute in order, producing spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, and tasks.md.
2. **Given** phases 1-2 are marked complete in `.pipeline-state.json`, **When** I run `specforge plan ledger-service`, **Then** it skips phases 1-2 and runs phase 4 (plan) directly, using existing spec.md and research.md as inputs.
3. **Given** phase 3 is in-progress (data-model.md exists but edge-cases.md does not), **When** I resume the pipeline, **Then** it re-runs only the incomplete artifacts of phase 3 before proceeding.
4. **Given** all phases are complete, **When** I run `specforge specify ledger-service --force`, **Then** it regenerates all artifacts from scratch.
5. **Given** terminal A is running the pipeline for ledger-service, **When** terminal B runs `specforge specify ledger-service`, **Then** terminal B displays an error that ledger-service pipeline is already in progress.
6. **Given** terminal A is running the pipeline for ledger-service, **When** terminal B runs `specforge specify identity-service`, **Then** terminal B proceeds normally since different services have independent locks.

---

### User Story 3 - Architecture-Conditional Artifact Generation (Priority: P2)

As a developer, I want the pipeline to adapt artifact content based on the architecture type declared in manifest.json, so that microservice artifacts include deployment and communication concerns while monolith artifacts remain simpler.

The architecture type (microservice, monolithic, modular-monolith) affects every artifact. Microservice plans include containerization, health checks, and circuit breakers. Monolith plans reference shared infrastructure. Modular-monolith plans add strict module boundary enforcement and generate an `interfaces.md` document describing module boundary contracts in a technology-agnostic way (no code generation).

**Why this priority**: Architecture-aware generation is the key differentiator of this tool. Without it, the pipeline produces generic artifacts that miss critical deployment and communication concerns.

**Independent Test**: Can be tested by generating plan.md for the same service under both microservice and monolithic architectures and comparing the sections present in each.

**Acceptance Scenarios**:

1. **Given** architecture=microservice, **When** plan.md is generated for ledger-service, **Then** it includes sections for containerization, health check endpoints, service registration, circuit breaker patterns, and inter-service communication setup.
2. **Given** architecture=monolithic, **When** plan.md is generated for the auth module, **Then** it does NOT include containerization, service discovery, or circuit breakers, and references shared infrastructure (single database, shared auth middleware).
3. **Given** architecture=microservice, **When** tasks.md is generated, **Then** it includes tasks for container build, service registration, and contract testing against dependent services.
4. **Given** architecture=modular-monolith, **When** plan.md and checklist.md are generated, **Then** plan.md includes module boundary enforcement rules, checklist.md verifies no cross-module direct database access, and interfaces.md describes the module's public contract in technology-agnostic terms.

---

### User Story 4 - Data Model Scoping by Service Boundary (Priority: P2)

As a developer, I want data-model.md to be scoped to the service's bounded context, so that microservice data models are isolated while monolith modules can reference shared entities through a dedicated shared entities document.

In microservice mode, each service's data-model.md contains only entities owned by that service. Cross-service data access is expressed through API contracts, not shared tables. In monolith mode, each module gets its own data-model.md scoped to module-owned entities, plus a project-level `shared_entities.md` (at `.specforge/shared_entities.md`) listing entities that span multiple modules (e.g., users table).

**Why this priority**: Proper data boundary enforcement prevents the most common microservice anti-pattern (shared databases). This is critical for architectural integrity.

**Independent Test**: Can be tested by generating data-model.md for ledger-service in microservice mode and verifying it contains only account/transaction entities, with no user/identity tables.

**Acceptance Scenarios**:

1. **Given** architecture=microservice and ledger-service owns Features 002+003, **When** data-model.md is generated, **Then** it contains entities for accounts, transactions, and categories only, with no cross-service tables.
2. **Given** architecture=monolithic and the auth module, **When** data-model.md is generated, **Then** it contains auth-owned entities and references shared entities via the project-level shared_entities.md.
3. **Given** architecture=monolithic and multiple modules reference the users table, **When** data-model.md is generated for any module, **Then** users is documented in `.specforge/shared_entities.md` (created or updated if it doesn't exist) and each module's data-model.md references it rather than redefining it.
4. **Given** architecture=microservice, **When** data-model.md references data from another service, **Then** it describes the dependency as an API contract reference, not a direct table join.

---

### User Story 5 - Edge Cases Include Architecture-Specific Concerns (Priority: P3)

As a developer, I want edge-cases.md to include architecture-specific failure scenarios, so that microservice edge cases cover distributed systems concerns while monolith edge cases focus on module boundaries.

**Why this priority**: Architecture-specific edge cases catch the failure modes that developers most commonly miss. Distributed systems edge cases (network partitions, eventual consistency) are especially important for microservices.

**Independent Test**: Can be tested by generating edge-cases.md for a microservice and verifying it includes service-down, network partition, and eventual consistency scenarios.

**Acceptance Scenarios**:

1. **Given** architecture=microservice, **When** edge-cases.md is generated for ledger-service, **Then** it includes scenarios for: service-down (identity-service unavailable), network partition, eventual consistency, and timeout handling.
2. **Given** architecture=monolithic, **When** edge-cases.md is generated for the auth module, **Then** it focuses on module boundary violations, shared resource contention, and circular dependency detection.
3. **Given** architecture=modular-monolith, **When** edge-cases.md is generated, **Then** it includes both module boundary violations AND interface contract violations.

---

### User Story 6 - Parallel Phase Execution (Priority: P3)

As a developer, I want phases 3a (data-model.md) and 3b (edge-cases.md) to execute in parallel, so that the pipeline completes faster when both artifacts are independent.

**Why this priority**: Performance optimization. These two artifacts have no dependency on each other and can be generated simultaneously.

**Independent Test**: Can be tested by measuring pipeline execution time and verifying phases 3a and 3b overlap rather than running sequentially.

**Acceptance Scenarios**:

1. **Given** phase 2 (research.md) is complete, **When** the pipeline enters phase 3, **Then** data-model.md and edge-cases.md generation begin concurrently.
2. **Given** one of the parallel artifacts fails, **When** the other succeeds, **Then** the successful artifact is retained and only the failed one needs re-running.

---

### User Story 7 - Dependency Stub Contract Generation (Priority: P3)

As a developer, I want the pipeline to generate stub API contract placeholders when a dependent service hasn't been specified yet, so that I can proceed with planning without waiting for all services to complete.

When ledger-service's plan.md references identity-service's API, but identity-service hasn't been through the pipeline yet, the system generates a stub contract derived from the manifest's communication patterns. This stub contains the expected interface shape (endpoints, data types) that the dependent service should provide.

**Why this priority**: In a real workflow, services are specified incrementally. Blocking on dependency ordering creates bottlenecks. Stubs allow parallel team progress.

**Independent Test**: Can be tested by running the pipeline for ledger-service before identity-service, verifying a stub contract is generated and plan.md references it.

**Acceptance Scenarios**:

1. **Given** ledger-service depends on identity-service and identity-service has no contracts/ directory, **When** plan.md is generated for ledger-service, **Then** a stub contract file is created at `.specforge/features/identity-service/contracts/api-spec.stub.json` with the expected interface shape.
2. **Given** identity-service is later specified and generates its real api-spec.json, **When** ledger-service's plan is re-generated, **Then** it references the real contract and the stub is no longer used.
3. **Given** a stub contract exists, **When** identity-service generates its real contract, **Then** the pipeline warns if the real contract deviates from the stub's expected interface.

---

### Edge Cases

- What happens when the target service/module name doesn't exist in manifest.json?
- What happens when manifest.json is missing or corrupted?
- What happens when a service has zero features mapped to it?
- What happens when the pipeline is interrupted mid-phase (e.g., process killed)?
- What happens when a previous artifact is manually edited and a later phase is re-run?
- What happens when the architecture type changes between pipeline runs (e.g., manifest updated from monolith to microservice)?
- What happens when two services share the same feature ID (manifest validation error)?
- What happens when a service depends on another service that hasn't been specified yet?
- What happens when the user runs a later phase (e.g., `specforge plan`) without completing earlier phases?
- What happens when a feature number resolves to a service but the feature is one of several in that service?
- What happens when `.pipeline-lock` is stale (owning process crashed without cleanup)?
- What happens when shared_entities.md conflicts arise (two modules claim ownership of the same entity)?

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline Orchestration**

- **FR-001**: System MUST read manifest.json to resolve which features belong to the target service or module
- **FR-002**: System MUST execute pipeline phases in dependency order: spec (1) -> research (2) -> data-model + edge-cases (3) -> plan (4) -> checklist (5) -> tasks (6)
- **FR-003**: System MUST support running individual phases by name (e.g., `specforge plan <service>`) while enforcing prerequisite completion
- **FR-004**: System MUST generate all 7 artifacts (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) per service or module
- **FR-005**: System MUST execute phases 3a (data-model.md) and 3b (edge-cases.md) in parallel when both need generation
- **FR-006**: System MUST create the service/module output directory under `.specforge/features/<service-slug>/` if it does not exist
- **FR-007**: System MUST refuse to run a phase if its prerequisite phases are not complete, displaying which phases need to run first

**Pipeline State Management**

- **FR-008**: System MUST persist pipeline state in `.pipeline-state.json` within the service's feature directory
- **FR-009**: System MUST record for each phase: status (pending, in-progress, complete, failed), start timestamp, and completion timestamp
- **FR-010**: System MUST skip already-completed phases when re-running the pipeline, unless `--force` flag is provided
- **FR-011**: System MUST update phase status to "in-progress" before starting a phase and to "complete" or "failed" upon finishing
- **FR-012**: System MUST allow `--force` flag to regenerate all artifacts from scratch regardless of state
- **FR-013**: System MUST detect and recover from interrupted phases (status = "in-progress" with no completion timestamp) by re-running them

**Concurrency Control**

- **FR-014**: System MUST create a `.pipeline-lock` file in the service's feature directory before starting pipeline execution
- **FR-015**: System MUST remove the `.pipeline-lock` file upon pipeline completion (success or failure)
- **FR-016**: System MUST refuse to start a pipeline run if `.pipeline-lock` already exists for the target service, displaying an error with the lock owner's timestamp
- **FR-017**: System MUST allow concurrent pipeline runs for different services (each service has an independent lock)
- **FR-018**: System MUST detect stale lock files (lock age exceeding 30 minutes) and allow override with a warning

**Spec Generation (Phase 1)**

- **FR-019**: System MUST generate spec.md containing user stories for ALL features mapped to the target service
- **FR-020**: System MUST organize user stories by domain capability (e.g., "Account Management", "Transaction Processing"), NOT by original feature number
- **FR-021**: System MUST group user stories into domain capability sub-sections when the service contains 4 or more features
- **FR-022**: System MUST include a "Service Dependencies" section in spec.md when architecture is microservice, listing consumed services and their communication patterns
- **FR-023**: System MUST omit the "Service Dependencies" section when architecture is monolithic
- **FR-024**: System MUST include module context information when architecture is monolithic or modular-monolith

**Research Generation (Phase 2)**

- **FR-025**: System MUST generate research.md that identifies and resolves technical unknowns specific to the service's feature set
- **FR-026**: System MUST use spec.md as input when generating research.md

**Data Model Generation (Phase 3a)**

- **FR-027**: System MUST generate data-model.md scoped to the service's bounded context
- **FR-028**: System MUST limit data-model.md to entities owned by the service when architecture is microservice (no cross-service tables)
- **FR-029**: System MUST generate per-module data-model.md when architecture is monolithic, with module-owned entities only
- **FR-030**: System MUST create or update a project-level `.specforge/shared_entities.md` listing entities that span multiple modules in monolithic and modular-monolith architectures
- **FR-031**: System MUST express cross-service data dependencies as API contract references in microservice mode
- **FR-032**: System MUST cover entities from ALL features in the service within a single unified schema

**Edge Cases Generation (Phase 3b)**

- **FR-033**: System MUST generate edge-cases.md covering failure scenarios across all features in the service
- **FR-034**: System MUST include distributed systems edge cases (service-down, network partition, eventual consistency, timeouts) when architecture is microservice
- **FR-035**: System MUST include module boundary violation scenarios when architecture is monolithic or modular-monolith
- **FR-036**: System MUST include interface contract violation scenarios when architecture is modular-monolith

**Plan Generation (Phase 4)**

- **FR-037**: System MUST generate plan.md using spec.md, research.md, data-model.md, and applicable prompt files as inputs
- **FR-038**: System MUST include containerization, health checks, service registration, circuit breaker patterns, and API gateway route configuration in plan.md when architecture is microservice
- **FR-039**: System MUST reference shared infrastructure (single database, shared auth middleware) in plan.md when architecture is monolithic
- **FR-040**: System MUST include module boundary enforcement rules in plan.md when architecture is modular-monolith
- **FR-041**: System MUST design the service as one deployable unit in plan.md
- **FR-042**: System MUST include API contract design and inter-service communication setup in plan.md when architecture is microservice

**Checklist Generation (Phase 5)**

- **FR-043**: System MUST generate checklist.md that validates all previous artifacts for completeness and consistency
- **FR-044**: System MUST verify no cross-module direct database access in checklist.md when architecture is modular-monolith

**Tasks Generation (Phase 6)**

- **FR-045**: System MUST generate tasks.md with ordered implementation tasks for the entire service
- **FR-046**: System MUST include container build, service registration, and contract test tasks in tasks.md when architecture is microservice
- **FR-047**: System MUST omit container and service discovery tasks in tasks.md when architecture is monolithic

**API Contracts (Microservice Only)**

- **FR-048**: System MUST generate a `contracts/` subdirectory containing API contract definitions when architecture is microservice
- **FR-049**: System MUST generate `api-spec.json` within `contracts/` using a simplified JSON schema format (not full OpenAPI 3.0) auto-generated from the data model entities and communication patterns
- **FR-050**: System MUST generate stub contract files (`api-spec.stub.json`) for dependent services that haven't been specified yet, derived from manifest communication patterns
- **FR-051**: System MUST warn when a real contract deviates from a previously generated stub contract

**Module Interfaces (Modular-Monolith Only)**

- **FR-052**: System MUST generate `interfaces.md` describing the module's public boundary contract in technology-agnostic terms when architecture is modular-monolith
- **FR-053**: System MUST NOT generate code artifacts (no source code files like interfaces or ABCs) — interface descriptions remain in documentation form only

**Service/Module Resolution**

- **FR-054**: System MUST resolve the target name against manifest.json service slugs (microservice) or feature directory names (monolith)
- **FR-055**: System MUST accept feature numbers (e.g., `002`) as input and auto-resolve to the owning service via manifest.json lookup
- **FR-056**: System MUST display the resolved service name when a feature number is provided (e.g., "Feature 002 belongs to ledger-service, generating specs for entire service")
- **FR-057**: System MUST display a clear error listing available services/modules when the target name is not found in manifest.json
- **FR-058**: System MUST validate that manifest.json exists before running any pipeline phase
- **FR-059**: System MUST validate that the target service has at least one feature mapped to it

**Template Integration**

- **FR-060**: System MUST use Jinja2 templates (from Feature 002's TemplateRegistry) for rendering all artifacts
- **FR-061**: System MUST pass architecture type, service metadata, feature list, and communication patterns as template context variables
- **FR-062**: System MUST support user template overrides via `.specforge/templates/` directory (existing Feature 002 mechanism)

**Prompt Integration**

- **FR-063**: System MUST use PromptContextBuilder (from Feature 003) to inject applicable governance prompts into artifact generation context
- **FR-064**: System MUST pass prompt context to plan.md generation (Phase 4) where governance rules affect implementation decisions
- **FR-065**: System MUST gracefully degrade when governance prompt files (Feature 003) do not exist — plan.md generation proceeds without prompt context injection, and no error is raised

### Key Entities

- **PipelineState**: Tracks completion status of each phase for a service. Contains phase name, status (pending/in-progress/complete/failed), start and completion timestamps, and artifact file paths.
- **ServiceContext**: Resolved context for a target service. Contains service metadata from manifest.json, list of mapped features with descriptions, architecture type, dependent services with communication patterns, and the service's output directory path.
- **ArtifactPhase**: Represents one pipeline phase. Contains phase number, name, input artifact dependencies, output artifact paths, and execution logic. Phases 3a and 3b share the same phase number but produce different artifacts.
- **PipelineOrchestrator**: Coordinates phase execution for a service. Reads manifest, resolves ServiceContext, checks PipelineState, and executes phases in dependency order with parallel support for phase 3.
- **PipelineLock**: Per-service lock for concurrency control. Contains owning process timestamp and service slug. Stale after 30 minutes.
- **SharedEntities**: Project-level document listing entities that span multiple modules in monolithic/modular-monolith architectures. Referenced by per-module data-model.md files.
- **StubContract**: Placeholder API contract for unspecified dependent services. Contains expected interface shape derived from manifest communication patterns. Replaced when real contract is generated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can generate all 7 artifacts for a service with a single command in under 60 seconds for a typical 5-feature service
- **SC-002**: Pipeline correctly scopes artifacts to the service boundary — microservice data models contain zero cross-service entities
- **SC-003**: Re-running the pipeline after completion skips all phases (0 artifacts regenerated) unless `--force` is used
- **SC-004**: Interrupted pipeline runs resume from the last incomplete phase, regenerating at most 1 phase worth of artifacts
- **SC-005**: Microservice plan artifacts contain all 5 deployment concerns (containerization, health checks, service registration, circuit breakers, API gateway) while monolith plans contain zero of these
- **SC-006**: A service with N mapped features produces exactly 1 spec.md (not N separate specs), covering all N features in a unified narrative organized by domain capability
- **SC-007**: 100% of generated artifacts pass the checklist validation (Phase 5) without manual intervention
- **SC-008**: Pipeline state file accurately reflects actual artifact existence — no phantom "complete" states for missing files
- **SC-009**: Feature number input (e.g., `specforge specify 002`) produces identical output to service name input (e.g., `specforge specify ledger-service`) when both resolve to the same service
- **SC-010**: Two concurrent pipeline runs for different services complete without interference or data corruption

## Assumptions

- manifest.json has already been generated by Feature 004's `specforge decompose` command before the pipeline runs
- The Jinja2 template engine (Feature 002) and PromptContextBuilder (Feature 003) are available and functional
- Artifact content generation uses Jinja2 templates that will be created as part of this feature's implementation
- The pipeline orchestrator runs locally on the developer's machine (not in CI/CD)
- Service slugs in manifest.json are valid filesystem directory names
- The `--force` flag applies to all phases; there is no per-phase force override
- Phase 3 parallelism uses threading or asyncio within a single process, not multi-process execution
- API contracts use a simplified JSON schema format (service name, endpoints with method/path/description, request/response entity references) rather than full OpenAPI 3.0, auto-generated from data model entities and communication patterns
- Stub contracts contain the minimum interface shape (endpoint paths, expected data types) derived from manifest communication patterns, not full API documentation
- In monolithic mode, shared_entities.md is a project-level file at `.specforge/shared_entities.md`, not duplicated per module
- Module interface descriptions (modular-monolith) are documentation-only artifacts — no source code generation
- Lock file staleness threshold is 30 minutes; processes running longer are assumed crashed
