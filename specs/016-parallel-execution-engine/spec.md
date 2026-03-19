# Feature Specification: Parallel Execution Engine

**Feature Branch**: `016-parallel-execution-engine`
**Created**: 2026-03-19
**Status**: Draft
**Input**: User description: "Build parallel execution engine for concurrent spec generation and implementation across services/modules with topological dependency ordering"

## Clarifications

### Session 2026-03-19

- Q: How many concurrent workers by default? → A: Fixed default of 4, configurable via `parallel.max_workers` in config.json. Not tied to CPU cores (workload is I/O-bound, not CPU-bound).
- Q: Should decompose --parallel wait for all services or stream updates? → A: Wait for all services to finish before returning, but stream per-service progress inline to the console during execution (phase completions, errors, service done).
- Q: What happens if one service in a parallel group fails during implement? → A: Continue other services by default (resilient mode). Add `--fail-fast` flag to stop all workers on first failure for CI/strict workflows.
- Q: Should we add --max-parallel CLI flag? → A: Yes, `--max-parallel N` CLI flag overrides `parallel.max_workers` from config.json for the current invocation. Essential for users with rate-limited AI providers.
- Q: In monolith mode, should parallel be used or fall back to sequential? → A: Parallel by default. Monolith modules are independent (no inter-module dependency graph), so sequential adds no safety benefit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parallel Spec Generation via Decompose (Priority: P1)

As a developer, I want to run `specforge decompose "Personal Finance App" --auto --parallel` so that the system uses my configured AI provider to discover all services/modules and then generates all 7-phase spec artifacts (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) for every service simultaneously, reducing total wait time proportionally to the number of services.

**Why this priority**: This is the primary value proposition. Today, decompose discovers services but the spec pipeline runs one service at a time. For a project with 6 services, parallel execution cuts wall-clock time by up to 6x. The `--auto` flag removes all interactive prompts, enabling fully automated end-to-end generation.

**Independent Test**: Can be fully tested by running `specforge decompose "Test App" --auto --parallel` on a fresh project directory and verifying that all service directories under `.specforge/features/` contain complete 7-phase artifacts, generated concurrently without corruption.

**Acceptance Scenarios**:

1. **Given** a fresh project directory with a configured AI provider, **When** the user runs `specforge decompose "Personal Finance App" --auto --parallel`, **Then** the system discovers services via AI, creates manifest.json, and launches parallel spec pipelines for all independent services simultaneously.
2. **Given** a microservice architecture with 6 services, **When** parallel spec generation runs, **Then** services with no inter-service dependencies start their pipelines at the same time, and each service's 7-phase pipeline completes independently.
3. **Given** a monolithic architecture, **When** `--parallel` is used, **Then** modules are run in parallel where their feature scopes do not overlap, respecting shared-resource boundaries.
4. **Given** a service whose pipeline fails mid-generation, **When** other services are still running, **Then** the failed service is marked as failed in pipeline state, other services continue unaffected, and a summary shows which services succeeded and which failed.
5. **Given** a project with an existing manifest.json and partial pipeline state, **When** `--auto --parallel` is run, **Then** the system resumes only incomplete services, skipping those already fully generated.
6. **Given** parallel execution is running, **When** a service completes a phase or encounters an error, **Then** a progress line is streamed to the console inline (e.g., "identity-service: completed research [2/7]"), and the command blocks until all services finish before printing the final summary.
7. **Given** the user passes `--max-parallel 2`, **When** parallel execution starts, **Then** at most 2 services run concurrently regardless of the value in config.json.

---

### User Story 2 - Parallel Implementation with Dependency Ordering (Priority: P2)

As a developer, I want `specforge implement --all --parallel` to read the dependency graph from manifest.json and run independent services simultaneously using isolated sub-agents, executing in topologically sorted waves so that foundational services complete before dependent ones begin.

**Why this priority**: Implementation is the most time-consuming phase. Running independent services in parallel while respecting dependency order ensures correctness (contracts exist before consumers) and dramatically reduces total implementation time.

**Independent Test**: Can be tested by creating a manifest with known dependency relationships, running `specforge implement --all --parallel`, and verifying that wave-1 services complete before wave-2 services start, with each service's implementation isolated.

**Acceptance Scenarios**:

1. **Given** a manifest with services: identity-service (no deps), admin-service (no deps), ledger-service (depends on identity), portfolio-service (depends on identity), **When** `specforge implement --all --parallel` runs, **Then** identity-service and admin-service run in wave 1 simultaneously, and ledger-service and portfolio-service run in wave 2 after wave 1 completes.
2. **Given** a monolithic architecture with modules, **When** `--parallel` is used, **Then** independent modules run simultaneously without Docker or contract generation, using shared-database boundaries instead.
3. **Given** a service in wave 2 whose dependency (wave 1) failed, **When** the wave transition occurs, **Then** the dependent service is skipped with status "blocked", and a clear message explains which dependency failed.
4. **Given** the `--parallel` flag with a configurable worker count, **When** max_workers is set to 2 in config.json, **Then** at most 2 services execute simultaneously regardless of how many are independent in a wave.
5. **Given** `--fail-fast` is passed alongside `--parallel`, **When** a service in wave 1 fails, **Then** all other running services in wave 1 are cancelled, subsequent waves are skipped, and the summary shows which services completed, which were cancelled, and which were never started.
6. **Given** `--fail-fast` is not passed, **When** a service fails, **Then** other services in the same wave continue, and only direct dependents in subsequent waves are blocked.

---

### User Story 3 - Live Dashboard During Parallel Execution (Priority: P3)

As a developer, I want `specforge status` to show live progress bars and phase completion for each service while parallel decompose or implement operations are running, so I can monitor overall progress in real time.

**Why this priority**: Without real-time visibility, developers cannot tell which services are progressing, which are stuck, and how close the overall operation is to completion. This builds on the existing Feature 012 dashboard.

**Independent Test**: Can be tested by running a parallel operation in one terminal and `specforge status --watch` in another, verifying that service progress updates appear within the refresh interval.

**Acceptance Scenarios**:

1. **Given** a parallel spec generation is in progress, **When** the user runs `specforge status --watch`, **Then** the dashboard shows each service with its current phase (e.g., "identity-service: research [3/7]") and updates every refresh cycle.
2. **Given** multiple services running simultaneously, **When** one service completes a phase, **Then** the dashboard reflects the updated phase count within one refresh interval.
3. **Given** a service fails during parallel execution, **When** the dashboard refreshes, **Then** the failed service shows an error indicator with the phase that failed.
4. **Given** all parallel services complete, **When** the dashboard refreshes, **Then** it shows a summary with total time, per-service timing, and overall success/failure count.

---

### User Story 4 - Monolith Module Parallelism (Priority: P4)

As a monolith user, I want the same `--parallel` flag to work for my architecture, running independent modules in parallel without generating Docker configurations, service contracts, or inter-service communication artifacts that are irrelevant to monolithic projects.

**Why this priority**: Monolith users should benefit from parallelism without being forced into microservice concepts. The architecture adapter already differentiates behavior; parallel execution should respect this.

**Independent Test**: Can be tested by running `specforge decompose "Monolith App" --arch monolithic --auto --parallel` and verifying that parallel module pipelines run without generating Docker, contract, or communication artifacts.

**Acceptance Scenarios**:

1. **Given** a monolithic architecture with 4 modules, **When** `--auto --parallel` is used, **Then** all 4 modules run their spec pipelines in parallel since monolith modules share infrastructure and have no inter-module dependency graph.
2. **Given** a modular-monolith architecture, **When** `--parallel` is used, **Then** module boundaries are respected and modules with shared-entity dependencies are sequenced appropriately.
3. **Given** a monolith implementation with `--all --parallel`, **When** implementation runs, **Then** no Docker-compose, service mesh, or API gateway artifacts are generated, and modules share the same database context.

---

### Edge Cases

- What happens when two parallel services attempt to write to the same shared infrastructure file (e.g., docker-compose.yml)?
  - The shared infrastructure phase completes before any service-level parallel execution begins, as the existing orchestrator already handles this.
- What happens when the configured AI provider rate-limits concurrent requests?
  - Each service's LLM provider instance uses independent retry with exponential backoff. If rate limits persist, the worker pauses while others continue. The configurable max_workers setting lets users throttle concurrency to match their API limits.
- What happens when a circular dependency exists in the manifest?
  - The existing dependency graph builder detects cycles via DFS and returns an error before any parallel execution begins.
- What happens when the system runs out of memory with many parallel services?
  - The max_workers configuration caps concurrent processes. Each service pipeline runs in its own thread with isolated state. Memory usage scales linearly with worker count, not total service count.
- What happens when the user cancels (Ctrl+C) during parallel execution?
  - All running threads receive a shutdown signal, in-progress phases are marked as "interrupted" in pipeline state, and completed work is preserved for resume.
- What happens when `--parallel` is used without `--auto` during decompose?
  - The interactive prompts for architecture selection and feature confirmation still appear sequentially. Only the post-discovery spec pipeline phase runs in parallel.
- What happens when `--fail-fast` is used and a service fails mid-wave?
  - Running services in the current wave receive a cancellation signal. Services that have already completed in prior waves retain their artifacts. The summary distinguishes completed, cancelled, and not-started services.
- What happens when `--max-parallel` exceeds the number of services?
  - The system uses the number of services as the effective cap. No error is raised; the flag is treated as an upper bound.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add a `--parallel` flag to the `specforge decompose` command that enables concurrent spec pipeline execution across all discovered services/modules after decomposition completes.
- **FR-002**: System MUST add an `--auto` flag to the `specforge decompose` command that suppresses all interactive prompts, using the configured AI provider for architecture selection and feature discovery without user intervention.
- **FR-003**: System MUST run independent service spec pipelines concurrently using a configurable worker pool, where the maximum number of concurrent workers is set via `parallel.max_workers` in `.specforge/config.json` (default: 4). The `--max-parallel N` CLI flag MUST override the config.json value for the current invocation.
- **FR-004**: System MUST respect the topological ordering from the manifest.json dependency graph when running `specforge implement --all --parallel`, executing services in dependency-sorted waves where all services in a wave run concurrently and a wave completes before the next begins.
- **FR-005**: System MUST maintain per-service isolation during parallel execution: each service gets its own pipeline lock, pipeline state, output directory, and LLM provider instance.
- **FR-006**: System MUST update pipeline state files atomically (via the existing tempfile + os.replace strategy) during concurrent execution to prevent state corruption.
- **FR-007**: System MUST handle individual service failures gracefully by default (resilient mode): a failed service does not stop other running services, dependent services in subsequent waves are marked as "blocked", and a final summary reports success/failure per service.
- **FR-008**: System MUST support resuming parallel execution: when re-run, only services with incomplete pipelines are re-executed, and already-completed services are skipped.
- **FR-009**: System MUST update the dashboard-readable state files during parallel execution so that `specforge status --watch` reflects live progress across all concurrent services.
- **FR-010**: System MUST use the AI provider configured in `.specforge/config.json` for all phases across all parallel services, with no fallback to template-based generation unless the AI provider is unavailable.
- **FR-011**: System MUST respect architecture type when determining parallelism: microservice uses per-service parallelism with dependency ordering, monolith uses per-module parallelism without inter-module dependency constraints, modular-monolith uses per-module parallelism with boundary-aware sequencing.
- **FR-012**: System MUST add a `--parallel` flag to `specforge implement --all` that enables concurrent sub-agent execution across independent services within each dependency wave.
- **FR-013**: System MUST propagate cancellation signals (e.g., Ctrl+C / SIGINT) to all running parallel workers, marking in-progress services as "cancelled" in parallel state and relying on existing `detect_interrupted()` to reset per-service phase state to "pending" for resume.
- **FR-014**: System MUST report a completion summary after parallel execution finishes, showing per-service status, timing, phase completion counts, and any errors encountered. The command MUST block until all services complete (or fail) before returning.
- **FR-015**: System MUST add a `--fail-fast` flag to both `specforge decompose --parallel` and `specforge implement --all --parallel` that cancels all running workers and skips remaining waves on the first service failure.
- **FR-016**: System MUST add a `--max-parallel N` CLI flag to both `specforge decompose` and `specforge implement` that overrides the `parallel.max_workers` config.json value for the current invocation.
- **FR-017**: System MUST stream per-service progress updates inline to the console during parallel execution (phase completions, errors, service completion), providing real-time visibility without requiring a separate `specforge status --watch` session.

### Key Entities

- **ParallelPipelineRunner**: Coordinates concurrent spec pipeline execution across multiple services, managing worker allocation, progress aggregation, and error isolation.
- **TopologicalParallelExecutor**: Computes dependency waves from the manifest graph and executes each wave's services concurrently, blocking between waves until all services in the current wave complete.
- **ParallelExecutionState**: Tracks the overall status of a parallel run including per-service progress, wave assignments, timing, and error information. Persisted for resume capability.
- **ThreadPoolExecutor (stdlib)**: Used directly inside ParallelPipelineRunner with configurable max_workers, graceful shutdown on cancellation, and per-worker error isolation. No separate abstraction needed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a project with N independent services, parallel spec generation completes in approximately 1/min(N, max_workers) of the time compared to sequential execution, with no more than 15% overhead from coordination.
- **SC-002**: All generated artifacts across parallel services are identical in content quality to those produced by sequential single-service execution (no truncation, no cross-service contamination, no missing sections).
- **SC-003**: The system successfully resumes after interruption, re-executing only incomplete services and completing within the expected time for the remaining work.
- **SC-004**: Dashboard updates reflect parallel service progress within one refresh interval (default 5 seconds) of a phase completing.
- **SC-005**: A developer can go from `specforge decompose "App Name" --auto --parallel` to having all spec artifacts for all services generated in a single unattended command.
- **SC-006**: Implementation via `specforge implement --all --parallel` correctly sequences services so that no service begins implementation before all its dependencies have completed.
- **SC-007**: Individual service failures do not cascade: if 1 of 6 services fails, the remaining 5 (that don't depend on the failed one) complete successfully.
- **SC-008**: The system operates correctly on projects with up to 20 services without deadlocks, resource exhaustion, or state corruption.

## Assumptions

- The configured AI provider can handle concurrent requests from multiple pipeline workers. If rate-limited, exponential backoff in the existing LLM provider handles throttling gracefully.
- The existing per-service locking mechanism (atomic file locks with O_CREAT | O_EXCL) is sufficient for thread-level concurrency within a single process. No cross-process locking is needed since parallel execution runs within one specforge process.
- The existing pipeline state and orchestration state JSON files provide sufficient isolation since each service writes to its own directory (`.specforge/features/<slug>/`).
- ThreadPoolExecutor (not ProcessPoolExecutor) is appropriate since the workload is I/O-bound (waiting for LLM subprocess calls), not CPU-bound.
- The `--auto` flag for decompose will use the AI provider to select architecture type and discover features/services without interactive prompts, using reasonable defaults for any decisions that would normally require user input.
- Monolith modules are treated as fully independent for parallel execution since they share infrastructure and have no explicit dependency graph in the manifest.
