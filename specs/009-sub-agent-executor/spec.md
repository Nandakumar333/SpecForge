# Feature Specification: Sub-Agent Execution Engine

**Feature Branch**: `009-sub-agent-executor`  
**Created**: 2026-03-17  
**Status**: Draft  
**Input**: User description: "Build the sub-agent execution engine that implements one service at a time"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Single Service Implementation (Priority: P1)

As a developer, I want to run `specforge implement ledger-service` to execute the entire implementation workflow for one service, so that each task in the service's `tasks.md` is processed in dependency order with automated quality checks after every task.

When the command runs, the engine:
1. Loads the service's context: `constitution.md`, applicable prompt governance files (via Feature 003 PromptContextBuilder), the service's `spec.md`, `plan.md`, `data-model.md`, `edge-cases.md`, and `tasks.md`.
2. Iterates through tasks in dependency order from `tasks.md`.
3. For each task, generates an implementation prompt combining the task description with the loaded context.
4. Executes the task in the chosen mode — Mode A (display the prompt for the developer to copy into their agent) or Mode B (call an agent directly).
5. After each task completes, runs quality checks: build, lint, and test.
6. If all quality checks pass, commits the changes with a conventional commit message.
7. Advances to the next task until all tasks are complete.

The engine processes exactly one service at a time. It has NO access to other services' implementation code — only to shared contracts from services that the current service depends on.

**Why this priority**: This is the core value proposition — turning spec artifacts into working code through an automated task-by-task execution loop. Without single-service implementation, the engine has no purpose.

**Independent Test**: Can be fully tested by providing a service with 3–5 tasks in `tasks.md`, running `specforge implement ledger-service`, and verifying each task executes in order with quality checks and commits.

**Acceptance Scenarios**:

1. **Given** all spec artifacts exist for `ledger-service` (spec.md, plan.md, data-model.md, edge-cases.md, tasks.md), **When** I run `specforge implement ledger-service`, **Then** the engine processes each task from tasks.md in dependency order, running build/lint/test after each task and committing on success.
2. **Given** `ledger-service` depends on `identity-service`, **When** the engine builds context for the sub-agent, **Then** the context includes `identity-service`'s shared contracts (e.g., api-spec.json, event schemas) but excludes `identity-service`'s implementation code (controllers, services, repositories).
3. **Given** the user runs `specforge implement ledger-service` in Mode A (prompt-display), **When** a task is processed, **Then** the engine displays a single atomic implementation prompt for that one task (not batched by layer) including task description, relevant context, and file path hints — then waits for the user to confirm task completion.
4. **Given** the user runs `specforge implement ledger-service` in Mode B (agent-call), **When** a task is processed, **Then** the engine sends the prompt directly to the configured agent and captures the result without manual intervention.
5. **Given** a task completes and quality checks pass, **When** the engine commits, **Then** the commit message follows conventional commit format (e.g., `feat(ledger): add TransactionService with validation logic`) and references the task ID.

---

### User Story 2 — Auto-Fix Loop for Quality Check Failures (Priority: P1)

As a developer, I want the engine to automatically retry when build, lint, or test checks fail after a task, so that transient or simple errors are resolved without manual intervention.

When a quality check fails (build error, lint violation, or test failure), the engine:
1. Captures the full error output (compiler errors, lint violations, test failure stack traces).
2. Generates a targeted fix prompt that includes the original task context, the error output, and the file(s) that changed.
3. Sends the fix prompt for execution (Mode A: display to user, Mode B: call agent).
4. Re-runs quality checks.
5. Repeats up to a configurable maximum number of attempts (default: 3).
6. If all retry attempts are exhausted, pauses execution and reports the failure with full diagnostic output for manual resolution.

For microservice projects, the auto-fix loop also handles architecture-specific failures: container build errors (wrong base image, missing dependencies) and contract test failures (schema mismatches against dependent service stubs).

**Why this priority**: Quality check failures are expected during automated code generation. Without auto-fix, the engine stops at the first error, defeating the purpose of automation. This is equally critical as US1 because the execution loop is incomplete without error recovery.

**Independent Test**: Can be tested by providing a task that intentionally produces a test failure, verifying the engine generates a fix prompt, retries, and either succeeds or halts after the maximum attempts with a clear error report.

**Acceptance Scenarios**:

1. **Given** a task completes but a unit test fails, **When** the auto-fix loop activates, **Then** it generates a fix prompt containing the test failure output (assertion error, stack trace) and the file(s) modified by the task.
2. **Given** the auto-fix prompt resolves the test failure, **When** quality checks pass on retry, **Then** the engine commits the combined changes (original task + fix) and proceeds to the next task.
3. **Given** the auto-fix loop has exhausted 3 attempts without passing quality checks, **When** the engine halts, **Then** it reports the remaining errors with full diagnostic output and saves execution state so the developer can fix manually and resume.
4. **Given** a container build fails for `ledger-service` (e.g., missing dependency in the container definition), **When** the auto-fix loop activates, **Then** it analyzes the container build error and generates a targeted fix prompt addressing the specific container issue.
5. **Given** a contract test fails because `ledger-service` calls an endpoint that doesn't match `identity-service`'s contract, **When** the auto-fix loop activates, **Then** the fix prompt includes both the contract test error and the relevant shared contract definition.

---

### User Story 3 — Service-Scoped Context Isolation (Priority: P1)

As a developer, I want the sub-agent to see ONLY the context relevant to the service being implemented, so that generated code does not inadvertently depend on other services' internals.

When building context for a service, the engine assembles:
- **Always included**: constitution.md (project governance), applicable prompt governance files (loaded via PromptContextBuilder from Feature 003)
- **Service-specific**: The target service's own spec.md, plan.md, data-model.md, edge-cases.md, and tasks.md
- **Architecture-specific prompts** (microservice only): Container configuration prompts, inter-service communication prompts, event bus prompts
- **Dependency contracts only**: Shared contracts (schemas, event definitions) from services that the target service depends on — but NEVER those services' source code

The engine enforces this boundary: it physically cannot include implementation files from other services in the prompt context.

**Why this priority**: Context isolation is the architectural foundation of correct code generation. If the sub-agent sees another service's code, it may generate tight coupling, defeating the purpose of service-based decomposition. This is a hard constraint, not a nice-to-have.

**Independent Test**: Can be tested by running implementation for `ledger-service` that depends on `identity-service`, then verifying the assembled context includes identity-service contracts but zero files from identity-service's implementation directories.

**Acceptance Scenarios**:

1. **Given** `ledger-service` depends on `identity-service`, **When** the engine assembles context, **Then** the context includes `identity-service/contracts/` files (API specs, event schemas) and excludes all files from `identity-service/src/`, `identity-service/controllers/`, `identity-service/services/`, etc.
2. **Given** the project uses microservice architecture, **When** the engine builds context for `ledger-service`, **Then** it includes architecture-specific prompt sections for containerization and inter-service communication in addition to the standard prompt governance files.
3. **Given** the project uses monolithic architecture, **When** the engine builds context for the `ledger` module, **Then** it excludes container and inter-service prompt sections and includes only the standard governance prompts.
4. **Given** `ledger-service` has no declared dependencies, **When** the engine assembles context, **Then** no external contract files are included — the context contains only governance files and the service's own artifacts.

---

### User Story 4 — Shared Infrastructure Implementation (Priority: P2)

As a developer, I want to run `specforge implement --shared-infra` to build all cross-service infrastructure before any service implementation begins, so that services can depend on shared contracts, orchestration configurations, and gateway skeletons from the start.

The shared infrastructure phase produces:
- Shared contracts library (inter-service communication protocol definitions, event schemas)
- Container orchestration base file (service and infrastructure container definitions)
- Message broker configuration (exchange/queue definitions for event-driven services)
- Gateway skeleton (routing rules for all declared services)
- Shared authentication middleware (token validation, identity propagation)

These artifacts are generated from the `cross-service-infra/tasks.md` produced by Feature 008. The engine processes these tasks using the same execution loop as service tasks (prompt generation → execution → quality checks → commit), but with project-wide context rather than service-scoped context.

**Why this priority**: Shared infrastructure must exist before any service can be implemented. Container orchestration, shared contracts, and gateway routing are prerequisites for service-level tasks. However, this is P2 because a monolithic project does not need it at all.

**Independent Test**: Can be tested by running `specforge implement --shared-infra` for a microservice project and verifying the shared contracts library, orchestration base, broker configuration, gateway skeleton, and auth middleware are all created and pass quality checks.

**Acceptance Scenarios**:

1. **Given** a microservice project with 3 services declared, **When** I run `specforge implement --shared-infra`, **Then** the engine processes all tasks from `cross-service-infra/tasks.md` and produces the shared contracts library, orchestration base, message broker config, gateway skeleton, and shared auth middleware.
2. **Given** shared infrastructure has NOT been built, **When** I run `specforge implement ledger-service`, **Then** the engine warns that shared infrastructure is missing and asks whether to run `--shared-infra` first or proceed without it.
3. **Given** shared infrastructure has been built, **When** I subsequently run `specforge implement ledger-service`, **Then** the service implementation can reference shared contracts and orchestration configuration produced by the infrastructure phase.
4. **Given** a monolithic project, **When** I run `specforge implement --shared-infra`, **Then** the engine reports that shared infrastructure is not applicable for monolithic architectures and exits gracefully.

---

### User Story 5 — Resume Interrupted Execution (Priority: P2)

As a developer, I want to resume implementation from the last successfully committed task after an interruption, so that I don't have to re-run already completed work.

The engine persists execution state after each committed task to an execution state file in the service's feature directory. The state tracks which tasks have been completed, which are pending, and the last committed task ID. When resuming, the engine loads this state and starts from the first incomplete task.

**Why this priority**: Interruptions are inevitable — developer stops work, machine restarts, network drops during agent calls. Without resume, every interruption forces a full restart. This is important but depends on the core execution loop (US1) being complete.

**Independent Test**: Can be tested by running implementation for 5 tasks, interrupting after task 3, then running `specforge implement --resume ledger-service` and verifying execution starts at task 4.

**Acceptance Scenarios**:

1. **Given** `ledger-service` implementation completed tasks T001–T003 before interruption, **When** I run `specforge implement --resume ledger-service`, **Then** execution resumes from T004 without re-processing T001–T003.
2. **Given** execution state exists for `ledger-service`, **When** I run `specforge implement ledger-service` without `--resume`, **Then** the engine warns that previous progress exists and asks whether to resume or start fresh.
3. **Given** a task was in the auto-fix loop when interrupted (e.g., attempt 2 of 3), **When** I resume, **Then** the engine restarts the failed task from scratch (attempt 1 of 3) rather than continuing from the interrupted attempt.
4. **Given** all tasks in `ledger-service` are marked complete in execution state, **When** I run `specforge implement --resume ledger-service`, **Then** the engine reports that implementation is already complete and no tasks remain.

---

### User Story 6 — Microservice Post-Implementation Verification (Priority: P3)

As a developer, I want the engine to perform microservice-specific verification after all tasks for a service complete, so that I know the service is deployable and contract-compliant before moving on.

After all tasks in a service's `tasks.md` have been executed and committed, the engine runs a verification sequence (microservice architecture only):
1. Build the container image for the service
2. Run the service's health check endpoint test
3. Run contract tests against dependent service stubs
4. Register/update the service entry in the orchestration configuration file

If any verification step fails, the auto-fix loop (US2) applies. The verification results are recorded in the execution state.

**Why this priority**: Post-implementation verification is the "definition of done" for a microservice. It's important but depends on the core execution loop (US1), auto-fix (US2), and shared infrastructure (US4) being complete.

**Independent Test**: Can be tested by completing all tasks for a service, then verifying the engine builds the container image, runs health checks, executes contract tests, and updates orchestration configuration.

**Acceptance Scenarios**:

1. **Given** all tasks for `ledger-service` have been executed, **When** post-implementation verification runs, **Then** the engine builds the container image, runs the health check test, executes Pact consumer-driven contract tests against dependent service stubs, and updates the orchestration configuration.
2. **Given** the container image build fails, **When** the auto-fix loop activates, **Then** it generates a fix prompt addressing the container build error (missing dependency, wrong base image, incorrect build configuration).
3. **Given** a Pact contract test fails for `ledger-service`, **When** the auto-fix loop activates, **Then** the fix prompt includes the Pact verification output and the relevant shared contract definition, and the fix is scoped to `ledger-service` consumer test code only (never modifies the contract).
4. **Given** a monolithic project, **When** all tasks complete for a module, **Then** no container or contract verification runs — only the standard build/lint/test checks.
5. **Given** an integration test task requires database access, **When** the executor reaches that task, **Then** it runs `docker-compose --profile test up -d` to spin up test dependencies before executing the task, and `docker-compose --profile test down` after quality checks complete.

---

### Edge Cases

- What happens when `tasks.md` does not exist for the target service? The engine reports a clear error listing which spec artifacts are present and which are missing, and suggests running the task generation pipeline first.
- What happens when a task references a dependency (via `[XDEP]`) on a cross-service infrastructure task that hasn't been completed? The engine checks for `--shared-infra` completion before starting service tasks and blocks with a clear message if prerequisites are unmet.
- What happens when the configured agent is unreachable in Mode B? The engine retries the connection up to 3 times with increasing wait intervals, then falls back to Mode A (prompt-display) and notifies the developer.
- What happens when the auto-fix loop produces changes that break a previously passing test? The engine detects regression (new failures that weren't in the original error output) and reverts the fix attempt, counting it as a failed retry.
- What happens when two developers simultaneously run `specforge implement` for the same service? The engine uses a file-based lock in the execution state directory. The second invocation detects the lock, reports that implementation is already in progress, and exits without running.
- What happens when a task has parallel siblings (marked `[P]`) in tasks.md? The engine executes parallel-eligible tasks sequentially by default. A future enhancement may allow concurrent execution, but the initial version processes one task at a time to ensure deterministic output.
- What happens when `constitution.md` is missing from the project? The engine warns that project governance is not configured but proceeds with reduced context (governance prompts only, no constitution). This is a warning, not a blocking error.
- What happens when execution state becomes corrupted or references task IDs that no longer exist in `tasks.md`? The engine validates execution state against the current `tasks.md` on resume. Orphaned task IDs are removed from state, and the engine resumes from the first unmatched pending task.
- What happens when `docker-compose --profile test up` fails (e.g., port conflict, image pull failure)? The engine treats this as a pre-condition failure for integration test tasks, reports the docker-compose error, and halts execution with a clear message — it does NOT enter the auto-fix loop for infrastructure-level failures outside the service's control.
- What happens when the Pact consumer test stub does not match the shared contract (e.g., contract was updated after consumer test generation)? The engine detects the contract version mismatch, reports which contract fields diverge, and enters the auto-fix loop to regenerate the consumer test against the current contract.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `specforge implement <service-or-module>` command that executes the implementation workflow for a single service or module.
- **FR-002**: System MUST load service context before execution: constitution.md, prompt governance files (via PromptContextBuilder from Feature 003), and the service's own spec.md, plan.md, data-model.md, edge-cases.md, and tasks.md.
- **FR-003**: System MUST load shared contracts (API specs, event schemas) from services that the target service depends on, as declared in the manifest.
- **FR-004**: System MUST NOT include any implementation code (source files, controllers, services, repositories) from other services in the sub-agent's context.
- **FR-005**: System MUST process tasks from tasks.md in dependency order, respecting the topological ordering produced by Feature 008.
- **FR-006**: System MUST support two execution modes: Mode A (display implementation prompt for the developer to use manually) and Mode B (send prompt directly to a configured agent). In both modes, prompts are generated one-per-task (atomic), not batched by layer.
- **FR-007**: System MUST run quality checks (build, lint, test) after each task completes. The specific commands for build, lint, and test are read from the project's manifest or a configuration file.
- **FR-008**: System MUST commit changes with a conventional commit message after all quality checks pass for a task. The commit message format is `<type>(<scope>): <description>` where scope is the service name and description is derived from the task.
- **FR-009**: System MUST implement an auto-fix loop that captures quality check errors, generates a targeted fix prompt, retries execution, and re-runs quality checks — up to a configurable maximum number of attempts (default: 3).
- **FR-010**: System MUST detect regression in the auto-fix loop (new failures not present in the original error output) and revert the fix attempt, counting it as a failed retry.
- **FR-011**: System MUST halt execution and report full diagnostic output when the auto-fix loop exhausts all retry attempts, saving execution state for manual resolution and resume.
- **FR-012**: System MUST provide `specforge implement --shared-infra` to execute cross-service infrastructure tasks from `cross-service-infra/tasks.md` before any service implementation. Shared infra commits land on the current working branch (no separate branch).
- **FR-013**: System MUST warn when a service implementation is started but shared infrastructure has not been completed (microservice and modular-monolith architectures only).
- **FR-014**: System MUST report that `--shared-infra` is not applicable for monolithic architectures.
- **FR-015**: System MUST persist execution state after each committed task to an execution state file, tracking completed tasks, pending tasks, and the current task.
- **FR-016**: System MUST support `specforge implement --resume <service>` to resume execution from the last committed task.
- **FR-017**: System MUST validate execution state against the current tasks.md on resume, handling orphaned or changed task IDs gracefully.
- **FR-018**: System MUST warn when previous execution state exists and the user runs `specforge implement` without `--resume`, offering the choice to resume or start fresh.
- **FR-019**: System MUST use a file-based lock to prevent concurrent implementation runs for the same service.
- **FR-020**: System MUST include architecture-specific prompt sections (container configuration, inter-service communication, event bus) when the project uses microservice architecture.
- **FR-021**: System MUST exclude architecture-specific sections (containers, inter-service communication, gateways) for monolithic projects.
- **FR-022**: System MUST run microservice post-implementation verification after all code tasks complete (not per-task): container image build, health check test, Pact consumer-driven contract tests against dependent service stubs, and orchestration configuration update. Container image build status is recorded in the verification phase of execution state.
- **FR-023**: System MUST apply the auto-fix loop to microservice verification failures (container build errors, contract test failures) with the same retry logic as task-level failures.
- **FR-024**: System MUST skip microservice verification for monolithic and modular-monolith projects, running only standard build/lint/test checks.
- **FR-025**: System MUST handle agent unreachability in Mode B by retrying up to 3 times, then falling back to Mode A with a notification.
- **FR-026**: System MUST execute parallel-eligible tasks (`[P]` marker) sequentially in this initial version, processing one task at a time.
- **FR-027**: System MUST read the project manifest to determine architecture type and service dependencies for context loading and verification decisions.
- **FR-028**: System MUST generate Pact consumer tests within the implementing service for each declared dependency. Provider verification runs against the dependency's shared contract definitions (stubs), not a live service instance.
- **FR-029**: System MUST manage docker-compose lifecycle for integration test tasks: invoke `docker-compose --profile test up -d` before running integration tests and `docker-compose --profile test down` after completion. The test-profile compose configuration is expected from the shared infrastructure phase.
- **FR-030**: System MUST record container image build status and verification results in the execution state's verification phase section, not as per-task state.
- **FR-031**: System MUST detect and recover from crash-window scenarios where a git commit succeeded but execution state was not updated. On resume, the engine checks git log for the task's conventional commit message before re-executing.
- **FR-032**: System MUST notify the user with a visible warning when context truncation occurs due to exceeding the token budget, listing which sections were truncated and by how much.

### Key Entities

- **ExecutionContext**: The assembled context provided to the sub-agent for a specific service. Contains governance documents, service artifacts, architecture-specific prompts, and dependency contracts. Enforces isolation by construction — only permitted files are included.
- **ExecutionState**: Persistent record of implementation progress for a service. Tracks completed task IDs, current task, retry counts, verification status, and timestamps. Stored as a file in the service's feature directory.
- **TaskExecution**: A single pass through the execution loop for one task: prompt generation → execution → quality checks → commit (or retry). Tracks attempt number, error output, and outcome (success/retry/fail).
- **QualityCheckResult**: The outcome of running build, lint, and test after a task. Contains pass/fail status, error output, and whether errors are regressions (new failures not present before the task).
- **AutoFixAttempt**: A single retry cycle within the auto-fix loop. Contains the fix prompt, the changes produced, the re-check result, and whether regressions were detected.
- **ServiceLock**: A file-based lock that prevents concurrent implementation runs for the same service. Contains the process ID, start timestamp, and the current task being processed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can implement a complete service by running a single command, with each task executed in correct dependency order and quality-checked before commit.
- **SC-002**: The sub-agent's context for any service contains zero files from other services' implementation directories — only shared contracts from declared dependencies.
- **SC-003**: The auto-fix loop resolves at least 60% of build/lint/test failures without manual intervention within 3 retry attempts.
- **SC-004**: Interrupted implementations can be resumed from the last committed task with zero re-processing of completed tasks.
- **SC-005**: Shared infrastructure is fully deployable before any service implementation begins, with all shared contracts, orchestration base, and gateway skeleton passing quality checks.
- **SC-006**: For microservice projects, every completed service has a working container image that passes health check and contract tests before being marked complete.
- **SC-007**: Concurrent implementation attempts for the same service are reliably detected and blocked, with a clear message directing the developer to the existing run.
- **SC-008**: The engine correctly adapts its context loading, verification steps, and available prompt sections to the project's declared architecture type (monolithic, microservice, modular-monolith).

## Clarifications

### Session 2026-03-17

- Q: Should Mode A (prompt-display) generate one prompt per task or batch prompts by layer? → A: One prompt per task. Each task produces an atomic prompt aligned with the per-task quality check and commit cycle. Batching by layer would increase error surface and make auto-fix less targeted.
- Q: For shared infrastructure (`--shared-infra`), should the executor create a separate git branch? → A: No — shared infra commits land on the same working branch. A separate branch adds merge complexity and delays availability for service implementations that depend on infra artifacts.
- Q: How should contract tests work — Pact consumer/provider, schema validation, or something else? → A: Pact consumer-driven contracts. The implementing service generates Pact consumer tests capturing expected interactions with dependencies. Provider verification runs against the dependency's shared contract definitions (stub/mock), not a live service. Consumer tests live in the service directory; provider stubs come from shared contracts.
- Q: Should Docker image build run after each task or only after all code tasks complete? → A: Only after all code tasks complete, as part of post-implementation verification (US6). Building per-task is wasteful — early tasks (domain models, repositories) don't produce a runnable service. Execution state records container image build status in the verification phase state, not per-task.
- Q: How should the executor handle tasks requiring docker-compose (e.g., integration tests needing a database)? → A: The executor manages docker-compose lifecycle for integration test tasks: invokes `docker-compose --profile test up -d` before running integration tests, then tears down with `docker-compose --profile test down` after. The test-profile compose configuration is produced by the shared infrastructure phase (US4).

## Assumptions

- Features 001–008 are complete and operational, providing manifest.json, constitution.md, prompt governance files, spec.md, plan.md, data-model.md, edge-cases.md, and tasks.md as inputs.
- The manifest structure includes architecture type, service/module definitions, dependency declarations, and communication patterns as established by Features 004 and 005.
- Shared contracts are stored in a known directory structure per service (e.g., `<service>/contracts/`) that the engine can discover via manifest declarations.
- The project has build, lint, and test commands configured (either in the manifest, a standard config file, or discoverable via convention).
- Conventional commit format (`type(scope): description`) is the standard for all automated commits.
- Mode B (direct agent call) requires external agent configuration that is outside the scope of this feature — this feature provides the prompt and interface; agent integration is configured separately.
