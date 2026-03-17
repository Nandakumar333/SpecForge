# Feature Specification: Task Generation Engine

**Feature Branch**: `008-task-generation-engine`  
**Created**: 2026-03-17  
**Status**: Draft  
**Input**: User description: "Build the task generation engine that converts plan.md into ordered, parallelizable tasks for each service/module"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Per-Service Task Generation in Microservice Mode (Priority: P1)

As a developer working on a microservice project, I want to generate an ordered, dependency-aware task list for a single service so that I know exactly what to build and in what sequence.

When I run task generation for a specific service (e.g., `ledger-service`), the engine reads the project manifest and the service's plan, then produces a `tasks.md` file containing tasks ordered according to the microservice build sequence:

1. Project scaffolding (service project, container definition, orchestration entry)
2. Domain models and value objects
3. Database context, migrations, and seed data
4. Repository layer (interfaces and implementations)
5. Service layer (business logic, validation, mapping)
6. Communication clients for dependent services (e.g., identity-service client)
7. Controllers and middleware
8. Event publishers and consumers (message broker handlers)
9. Health check endpoints
10. Contract tests against dependent services
11. Unit tests for all layers
12. Integration tests (application factory with containerized dependencies)
13. Container build optimization (multi-stage)
14. Gateway route configuration

Each task includes a unique ID, description, file paths, dependency references, and a parallelization marker indicating whether it can run concurrently with other tasks at the same level.

**Why this priority**: This is the core value proposition — converting an abstract plan into concrete, actionable work items. Without per-service task generation, the engine has no purpose. Microservice mode is the most complex case and validates the full ordering algorithm.

**Independent Test**: Can be fully tested by providing a sample manifest with one service and its plan, running generation, and verifying the output `tasks.md` contains all 14 task categories in the correct dependency order with accurate file path references.

**Acceptance Scenarios**:

1. **Given** a manifest declaring `ledger-service` with a dependency on `identity-service`, **When** tasks are generated for `ledger-service`, **Then** the output includes a task for "Create identity-service communication client" that depends on the service layer task being complete.
2. **Given** a manifest declaring `ledger-service` with features including transaction processing, **When** tasks are generated, **Then** each task includes concrete file paths relative to the service root (e.g., `src/ledger-service/domain/models/`, `src/ledger-service/controllers/`).
3. **Given** a service with no inter-service dependencies, **When** tasks are generated, **Then** step 6 (communication clients) and step 10 (contract tests) are omitted entirely from the output.
4. **Given** a service with event-based communication declared in the manifest, **When** tasks are generated, **Then** step 8 (event publishers/consumers) includes tasks for each declared event with producer/consumer roles specified.

---

### User Story 2 — Cross-Service Infrastructure Tasks (Priority: P1)

As a developer, I want shared infrastructure tasks (contracts library, orchestration file, message broker setup, gateway configuration, shared authentication) generated exactly once in a dedicated `cross-service-infra` task file, so that these concerns are not duplicated across individual service task lists.

When generating tasks for the full project, the engine identifies cross-cutting infrastructure concerns and produces a separate `cross-service-infra/tasks.md` containing:

- Shared contracts library (communication protocol definitions, event schemas)
- Gateway configuration (routing rules for all services)
- Orchestration file (container definitions for all services and infrastructure)
- Message broker setup (broker configuration, exchange/queue definitions)
- Shared authentication middleware (token validation, identity propagation)

These cross-service tasks are generated once regardless of how many services exist. Individual service task files reference the cross-service tasks as external dependencies where needed.

**Why this priority**: Duplicated infrastructure tasks would cause confusion, merge conflicts, and wasted effort. Deduplication into a single infrastructure task file is essential for a usable output. This is equally critical as per-service generation.

**Independent Test**: Can be tested by providing a manifest with 3+ services, running full-project generation, and verifying that (a) `cross-service-infra/tasks.md` exists with all shared tasks, (b) no individual service `tasks.md` contains duplicated infrastructure tasks, and (c) service tasks reference cross-service tasks as dependencies.

**Acceptance Scenarios**:

1. **Given** a manifest with `identity-service`, `ledger-service`, and `notification-service`, **When** I generate tasks for the entire project, **Then** a `cross-service-infra/tasks.md` is produced containing shared contracts, orchestration, gateway, and message broker tasks — each appearing exactly once.
2. **Given** a cross-service-infra task for shared contracts, **When** `ledger-service` tasks are generated, **Then** the communication client task in `ledger-service` lists the shared contracts task as an external dependency.
3. **Given** a monolithic architecture, **When** tasks are generated, **Then** no `cross-service-infra/tasks.md` is produced (cross-service concerns do not apply).

---

### User Story 3 — Monolith Mode Simplified Tasks (Priority: P2)

As a developer working on a monolithic or modular-monolith project, I want task generation to produce a simpler, appropriately-scoped task list per module — without container orchestration, inter-service communication clients, message broker handlers, or gateway configuration tasks — so that my task list reflects the actual architecture.

In monolith mode, the engine generates tasks following a shorter ordering per module:

1. Module folder structure
2. Domain models
3. Database migrations (referencing the shared database context)
4. Repository and service layers
5. Controllers
6. Module boundary interface (for modular monolith only)
7. Unit and integration tests

Container orchestration, inter-service communication clients, message broker handlers, contract tests, gateway configuration, and health check endpoints are excluded. Database tasks reference a shared context rather than a per-service context.

**Why this priority**: Monolith mode is simpler but essential for projects that don't use microservices. Generating microservice-style tasks for a monolith would be confusing and wasteful. This story ensures the engine adapts its output to the declared architecture.

**Independent Test**: Can be tested by providing a manifest with `architecture: monolithic` and a module definition, running generation, and verifying the output contains only the 7 monolith task categories with no container or inter-service concerns.

**Acceptance Scenarios**:

1. **Given** a manifest with `architecture: monolithic` and an `auth` module, **When** tasks are generated, **Then** the output contains exactly 7 task categories (folder structure through tests) with no container, communication client, gateway, or broker tasks.
2. **Given** a monolithic architecture with an `auth` module, **When** database tasks are generated, **Then** tasks reference a shared database context (e.g., `AppDbContext`) rather than a per-service context.
3. **Given** a manifest with `architecture: modular-monolith`, **When** tasks are generated for a module, **Then** step 6 includes a "Module boundary interface" task defining the module's public contract. For plain `monolithic`, step 6 is omitted.
4. **Given** a monolith module with no database entities, **When** tasks are generated, **Then** step 3 (database migrations) is omitted.

---

### User Story 4 — Dependency Ordering and Parallelization Markers (Priority: P2)

As a developer, I want each task to declare its dependencies and whether it can be parallelized with other tasks, so that I (or an automated executor) can determine the optimal execution order and identify which tasks can run concurrently.

Every task in the generated `tasks.md` includes:
- A unique task ID (e.g., `T001`, `T002`)
- A dependency list (IDs of tasks that must complete before this one can start)
- A parallelization marker `[P]` when the task has no ordering conflict with sibling tasks at the same dependency level
- A user story reference linking back to the spec

The engine computes a topological ordering based on declared dependencies and marks tasks as parallelizable when they operate on independent files/concerns at the same depth level.

**Why this priority**: Without dependency information and parallelization markers, the task list is just a flat checklist. Dependency ordering prevents developers from starting work that depends on incomplete prerequisites. Parallelization markers enable concurrent work streams and faster delivery.

**Independent Test**: Can be tested by generating tasks for a service with known dependencies, then verifying that (a) the topological order is correct (no task appears before its dependencies), (b) sibling tasks at the same level that touch different files are marked `[P]`, and (c) tasks with shared file concerns at the same level are NOT marked `[P]`.

**Acceptance Scenarios**:

1. **Given** a service where the repository layer depends on domain models, **When** tasks are generated, **Then** the repository task declares a dependency on the domain models task, and the domain models task has no dependency on the repository task.
2. **Given** two independent modules in a monolith (e.g., `auth` and `billing`), **When** tasks are generated for both, **Then** their respective tasks at the same phase level are marked `[P]` indicating they can execute in parallel.
3. **Given** a task for unit tests and a task for integration tests within the same service, **When** tasks are generated, **Then** unit tests are ordered before integration tests (unit tests are a dependency of integration tests).
4. **Given** tasks for event publishers and controllers within the same service, **When** tasks are generated, **Then** both depend on the service layer but are marked `[P]` relative to each other (they can be built concurrently).

---

### User Story 5 — Full Project Task Generation (Priority: P3)

As a developer, I want to generate tasks for the entire project in a single command, producing a `tasks.md` per service/module plus the cross-service infrastructure tasks, so that I get a complete project-wide work breakdown.

When running task generation at the project level, the engine iterates over all services/modules declared in the manifest, generates per-service/module task files, generates the cross-service infrastructure task file (for microservice/modular-monolith only), and produces a top-level summary listing all generated files and cross-file dependency relationships.

**Why this priority**: Single-service generation (US1) delivers the core value. Full-project generation is a convenience that orchestrates multiple single-service runs. It depends on US1, US2, and US3 being complete.

**Independent Test**: Can be tested by providing a manifest with 3 services, running project-level generation, and verifying that 3 service task files + 1 cross-service infra file + 1 summary file are produced.

**Acceptance Scenarios**:

1. **Given** a manifest with `identity-service`, `ledger-service`, and `notification-service`, **When** I run project-level task generation, **Then** task files are generated for each service and for `cross-service-infra`, plus a top-level summary.
2. **Given** a project-level generation completes, **When** I inspect the summary, **Then** it lists all generated files, total task counts per service, and cross-service dependency links.
3. **Given** a manifest with `architecture: monolithic` and 4 modules, **When** I run project-level generation, **Then** 4 module task files are generated with no cross-service infrastructure file.

---

### Edge Cases

- What happens when a service has circular dependencies in the manifest (e.g., service A depends on service B and service B depends on service A)? The engine must detect cycles and report a clear error listing the cycle path rather than entering an infinite loop or producing incorrect ordering.
- What happens when the plan.md for a service is missing or incomplete? The engine must report which required sections are missing and skip that service with a warning rather than producing a partial or incorrect task file.
- What happens when a service's dependency target does not exist in the manifest (e.g., ledger-service depends on `payment-service` but `payment-service` is not declared)? The engine must report the missing dependency and either skip the communication client task or generate it with a warning annotation.
- What happens when a manifest declares zero services or modules? The engine must produce a clear error indicating no services/modules were found and exit gracefully.
- What happens when the manifest's `architecture` field is missing or has an unsupported value? The engine must report the invalid architecture and refuse to generate tasks rather than defaulting silently.
- How does the engine handle a service with 50+ features? Task generation must cap or group tasks to keep the output readable (e.g., grouping related features into composite tasks) rather than producing an unmanageably long file.
- What happens when the engine is re-run after plan.md changes? The engine overwrites tasks.md with fresh output, renaming the prior version to `tasks.md.bak`. No merge is attempted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read the project manifest to determine architecture type (`monolithic`, `microservice`, `modular-monolith`) and adjust the task template accordingly.
- **FR-002**: System MUST read the plan.md for each target service/module to extract design decisions, integration points, and component structure.
- **FR-003**: System MUST generate a `tasks.md` file per service/module containing tasks ordered according to the architecture-specific build sequence.
- **FR-004**: System MUST assign each task a unique ID (scoped to its task file), a human-readable description, dependency references, file path hints, and a user story link.
- **FR-005**: System MUST mark tasks with a parallelization indicator `[P]` when they can execute concurrently with sibling tasks at the same dependency level.
- **FR-006**: System MUST compute a valid topological ordering of tasks based on declared dependencies, ensuring no task appears before its prerequisites.
- **FR-007**: System MUST detect circular dependencies between services in the manifest and report a clear error with the cycle path.
- **FR-008**: System MUST produce a separate `cross-service-infra/tasks.md` for shared infrastructure tasks (contracts library, orchestration file, message broker, gateway, shared authentication) when the architecture is `microservice` or `modular-monolith`. Cross-service tasks carry implicit P0 priority — they must complete before any service task that references them via XDEP. For microservice: all 5 categories (shared_contracts, docker_compose, message_broker, api_gateway, shared_auth). For modular-monolith: only shared_contracts and shared_auth (no Docker, broker, or gateway).
- **FR-009**: System MUST NOT duplicate cross-service infrastructure tasks in individual service task files.
- **FR-010**: System MUST allow individual service task files to reference cross-service tasks as external dependencies using `[XDEP: cross-service-infra/T00N]` notation, where `T00N` is the task ID in the cross-service-infra file.
- **FR-011**: In monolith mode, system MUST exclude container orchestration, inter-service communication clients, message broker handlers, contract tests, gateway configuration, and health check endpoint tasks.
- **FR-012**: In monolith mode, database tasks MUST reference a shared database context rather than per-service contexts.
- **FR-013**: In modular-monolith mode, system MUST include a "module boundary interface" task for each module.
- **FR-014**: System MUST omit task categories that do not apply to a given service (e.g., no event tasks if no events declared, no communication client tasks if no inter-service dependencies).
- **FR-015**: System MUST validate that the plan.md exists and contains required sections (Summary, Technical Context, Design Decisions — minimum) before generating tasks; missing plans or plans missing required sections produce a warning and skip that service.
- **FR-016**: System MUST support generating tasks for a single service/module or for the entire project.
- **FR-017**: When generating for the entire project, system MUST produce a top-level summary listing all generated task files, task counts, and cross-file dependencies.
- **FR-018**: System MUST cap task output per service to a reasonable limit (no more than 50 tasks per service) by grouping related concerns when feature count is high.
- **FR-019**: System MUST follow the existing tasks template format (phases, `[ID] [P?] [Story] Description`, checkpoint validations).
- **FR-020**: System MUST assign a T-shirt effort estimate (S, M, L, or XL) to each generated task, derived from the architecture-specific build sequence defaults (e.g., scaffolding=S, domain models=M, service layer=L, integration tests=XL).
- **FR-021**: System MUST read Feature 003 prompt governance files (read-only) to inform task descriptions with project coding standards (e.g., naming conventions, required patterns such as interface-based DI). The engine MUST NOT modify prompt files.
- **FR-022**: When a service/module has multiple features, tasks MUST be grouped by technical layer (all models → repositories → services → controllers) rather than by originating feature, to match the build sequence dependency order.
- **FR-023**: When a `tasks.md` file already exists for a target, the engine MUST rename the existing file to `tasks.md.bak` before generating the new output (overwrite-with-backup strategy).

### Key Entities

- **TaskItem**: A single actionable work item. Attributes: unique ID, description, phase, dependency list (task IDs), parallelization flag, effort size (S/M/L/XL), user story reference, file path hints, service/module scope.
- **TaskFile**: A collection of TaskItems for a single service/module or for cross-service infrastructure. Attributes: target name, architecture type, phase groupings, total task count.
- **DependencyGraph**: The directed acyclic graph of task dependencies within a task file and across task files. Used to compute topological ordering and detect cycles.
- **BuildSequence**: The architecture-specific ordered template of task categories (14 steps for microservice, 7 steps for monolith). Drives which tasks are generated and in what order.
- **CrossServiceTask**: A shared infrastructure task that belongs to `cross-service-infra` rather than any individual service. Referenced by service-level tasks as external dependencies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can generate a complete, ordered task list for any single service in under 10 seconds.
- **SC-002**: Generated task files for microservice-mode services contain all applicable task categories from the 14-step build sequence in the correct dependency order, with zero ordering violations when validated.
- **SC-003**: Generated task files for monolith-mode modules contain only the 7-step build sequence with no container, inter-service, or infrastructure tasks present.
- **SC-004**: Cross-service infrastructure tasks appear exactly once in `cross-service-infra/tasks.md` and are never duplicated in individual service task files.
- **SC-005**: 100% of tasks with dependencies have valid dependency references (no references to non-existent task IDs, no circular references within a task file).
- **SC-006**: Parallelization markers are accurate — tasks marked `[P]` have no ordering conflicts with sibling tasks at the same level; unmarked tasks have at least one sibling conflict.
- **SC-007**: Full-project task generation for a project with 5+ services completes in under 30 seconds and produces the correct number of task files plus the summary.
- **SC-008**: The engine correctly handles all 3 architecture types (monolithic, microservice, modular-monolith) without manual configuration beyond the manifest's architecture field.

## Clarifications

### Session 2026-03-17

- Q: How should cross-service infrastructure tasks be organized — separate file, inline [SHARED] markers, or hybrid? → A: Separate `cross-service-infra/tasks.md` file. Shared tasks are a first-class concern with their own dependency chain. Service-level task files reference shared tasks via `[XDEP: cross-service-infra/T00N]` notation.
- Q: Should each generated task include an effort estimate? → A: Yes, T-shirt sizes (S/M/L/XL) per task. Well-known relative complexities (scaffolding=S, service layer=L, integration tests=XL) are embedded in the architecture-specific build sequence templates.
- Q: Should the task generator consult Feature 003 prompt governance files to align task descriptions with coding standards? → A: Yes, read-only. The engine reads prompt governance files to inform task descriptions (e.g., "Create IUserService interface" when rules require interface-based DI, naming conventions) but does NOT modify prompt files. Coupling is one-directional: governance → task descriptions.
- Q: For services with multiple features (e.g., Planning Service with 3 features), should tasks be grouped by original feature or by technical layer? → A: By technical layer. All models first, then all repositories, then all services, then all controllers. This matches the build sequence dependency order, avoids redundant scaffolding, and keeps the task list aligned with the architecture-specific ordering.
- Q: When tasks.md already exists and the engine is re-run, should it overwrite or merge? → A: Overwrite with backup. The engine renames the existing file to `tasks.md.bak` before generating fresh output. Merge strategies are fragile and error-prone for generated artifacts.

### Assumptions

- Features 001–007 are complete and operational, providing the manifest, plan.md, and spec.md artifacts that this engine consumes.
- The manifest structure includes an `architecture` field and a `services` (or `modules`) array with dependency declarations and feature assignments.
- The plan.md follows the existing plan template structure with Summary, Technical Context, Design Decisions, and Integration Points sections.
- The tasks template format (`[ID] [P?] [Story] Description` with phases) defined in `.specify/templates/tasks-template.md` is the target output format.
- Communication patterns between services (synchronous vs asynchronous) are declared in the manifest's `communication` entries.
- Events (producer/consumer pairs) are declared in the manifest's `events` entries.
- The 14-step microservice sequence and 7-step monolith sequence described in the user context are the canonical build orderings. These may be refined during clarification but represent the baseline.
