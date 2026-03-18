# Feature Specification: Project Status Dashboard

**Feature Branch**: `012-project-status-dashboard`  
**Created**: 2026-03-18  
**Status**: Draft  
**Input**: User description: "Build specforge status that shows project-wide progress"

## Clarifications

### Session 2026-03-18

- Q: Should Docker column only show in microservice mode? → A: Yes — Docker column is visible only in microservice architecture. Both monolith and modular-monolith omit Docker columns entirely since Docker orchestration is a microservice concern. Modular monolith shows module boundary compliance instead.
- Q: Should status auto-detect which services exist and which are new? → A: Manifest-authoritative — display all services declared in the manifest. Services with zero artifacts show as "NOT STARTED" (no separate "NEW" status). The manifest is the single source of truth; no filesystem guessing.
- Q: Should there be a --watch mode for auto-refresh? → A: Yes, as P3 — `--watch` flag with configurable interval (default 5 seconds) for real-time monitoring during orchestration runs. Terminal-only (not applicable to markdown/JSON file output).
- Q: How should status.json handle services with no spec yet (just in manifest)? → A: Include all manifest services in JSON. Services with no artifacts have all lifecycle fields set to `null` (not omitted), `"status": "NOT_STARTED"`, and `"implementation_percent": 0`. This ensures CI/CD can enumerate all expected services.
- Q: Should specforge status return a non-zero exit code when any service is FAILED? → A: Yes — exit 0 when no service is FAILED, exit 1 when any service is FAILED. Enables simple CI/CD gating without JSON parsing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Per-Service Progress Overview (Priority: P1)

As a developer working on a multi-service (or multi-module) project, I want to run `specforge status` and immediately see a table showing every service or module with its current progress across all lifecycle phases (spec, plan, tasks, implementation, tests, Docker, overall status), so I can understand at a glance where the entire project stands without inspecting each service individually.

The command reads the project manifest to determine architecture type and displays an architecture badge (e.g., [MICROSERVICE], [MONOLITH], or [MODULAR]) at the top of the output. Below the badge, a service status table lists every declared service/module with columns for associated features, spec completion, plan status, task status, implementation percentage, test pass counts, Docker build status (microservice only), and an overall status label (COMPLETE, IN PROGRESS, PLANNING, NOT STARTED, BLOCKED, FAILED).

**Why this priority**: This is the core value proposition — a single command that answers "where is my project right now?" Without this, developers must manually check each service's state files, read task completion counts, and mentally assemble the overall picture. This story alone delivers a viable MVP.

**Independent Test**: Can be fully tested by running `specforge status` on a project with at least 3 services in different states (one complete, one in progress, one not started). Delivers value by showing a formatted table with accurate per-service progress.

**Acceptance Scenarios**:

1. **Given** a microservice project with 8 services declared in the manifest, where 2 are fully implemented, 1 is in progress, and 5 have not started, **When** the developer runs `specforge status`, **Then** the output begins with a `[MICROSERVICE]` architecture badge followed by a table with one row per service showing correct lifecycle phase status for each.
2. **Given** a monolithic project with 4 modules, **When** the developer runs `specforge status`, **Then** the output begins with a `[MONOLITH]` badge and the table omits Docker-specific columns (Docker build, health check) since they do not apply.
3. **Given** a modular monolith project, **When** the developer runs `specforge status`, **Then** the output begins with a `[MODULAR]` badge and the table includes module boundary compliance status instead of Docker columns.
4. **Given** a service has a completed spec, a work-in-progress plan, and no tasks yet, **When** its row is displayed, **Then** the spec column shows "DONE", the plan column shows "WIP", and all subsequent columns (tasks, implementation, tests, Docker) show "-" to indicate they are not yet applicable.
5. **Given** a service has completed all lifecycle phases and passed all quality checks, **When** its row is displayed, **Then** the overall status column shows "COMPLETE" and all intermediate columns show their completion indicators (DONE, 100%, pass counts, OK).

---

### User Story 2 - Phase Progress Visualization (Priority: P1)

As a developer, I want `specforge status` to display phase-level progress bars showing how each dependency phase is progressing, so I can understand sequencing bottlenecks and which phases are blocked.

Below the service table, the command displays a phase progress section. Each phase (as determined by the dependency graph from the manifest) is shown with a visual progress bar, a completion percentage, and a parenthetical note listing which services are complete, in progress, or blocked. Phases that cannot start because a prerequisite phase is incomplete are marked as blocked with the blocking phase identified.

**Why this priority**: Phase progress is co-equal with the service table because multi-service projects are executed in phases. Understanding which phase is the current bottleneck is essential for project management. Without phase visibility, the service table alone does not communicate sequencing constraints.

**Independent Test**: Can be fully tested by running `specforge status` on a project with at least 3 phases where Phase 1 is complete, Phase 2 is partially done, and Phase 3 is blocked. Delivers value by showing accurate phase bars with blocking information.

**Acceptance Scenarios**:

1. **Given** a project with 3 execution phases where Phase 1 (identity-service, admin-service) is fully complete, **When** `specforge status` displays the phase progress, **Then** Phase 1 shows a full progress bar at 100% with a note listing both services as complete.
2. **Given** Phase 2 has 3 services (ledger-service at 60% implementation, portfolio-service not started, integration-service not started), **When** Phase 2's progress is displayed, **Then** it shows a partial progress bar reflecting the aggregate completion and a note listing each service's status.
3. **Given** Phase 3 depends on Phase 2 and Phase 2 is incomplete, **When** Phase 3's progress is displayed, **Then** it shows 0% with a "blocked by Phase 2" indicator.
4. **Given** a monolithic project with no explicit phases (flat dependency graph), **When** the phase section would be displayed, **Then** the phase progress section is omitted or shows a single "All Modules" group since phased execution does not apply.

---

### User Story 3 - Quality Summary Dashboard (Priority: P2)

As a team lead, I want `specforge status` to include a quality summary section that aggregates key metrics across all services — total tasks complete/failed, average test coverage, Docker image build status, contract test results, and auto-fix success rate — so I can assess overall project health without drilling into individual service reports.

Below the phase progress section, the command displays a quality summary panel. This panel aggregates data from all services' quality reports (produced by Feature 010) and orchestration state (produced by Feature 011) to present project-wide metrics.

**Why this priority**: Quality metrics provide the "health" dimension that complements the "progress" dimension of the service table and phase bars. A project at 80% implementation but with 50% test failure rate is in a very different state than one at 80% with all tests passing. This story is P2 because the service table (P1) is independently useful, while quality metrics enhance rather than replace it.

**Independent Test**: Can be fully tested by running `specforge status` on a project where at least 2 services have completed quality reports. Delivers value by showing aggregated metrics that would otherwise require manually inspecting each service's quality report.

**Acceptance Scenarios**:

1. **Given** a project with 8 services, 2 complete, 1 in progress, and 5 not started, **When** the quality summary displays, **Then** it shows "Services: 8 total, 2 complete, 1 in progress, 5 not started".
2. **Given** 156 total tasks across all services with 89 complete and 3 failed, **When** the quality summary displays, **Then** it shows "Tasks: 156 total, 89 complete, 3 failed" with the failed count highlighted visually.
3. **Given** implemented services have coverage reports averaging 82%, **When** the quality summary displays, **Then** it shows "Test coverage: 82% average across implemented services" (services without coverage data are excluded from the average).
4. **Given** a microservice project with 8 declared Docker images, 2 built successfully, and 1 failing, **When** the quality summary displays, **Then** it shows "Docker: 2/8 images built, 1 failing" with the failing count highlighted.
5. **Given** a monolithic project, **When** the quality summary displays, **Then** Docker image and contract test metrics are omitted since they do not apply to monolith architectures.
6. **Given** the auto-fix loop has been used across services, **When** the quality summary displays, **Then** it shows the aggregate auto-fix success rate (e.g., "Auto-fix success rate: 78%").

---

### User Story 4 - Shareable Markdown Report (Priority: P2)

As a team lead, I want `specforge status --format markdown` to generate a shareable markdown report at `.specforge/reports/status.md`, so I can paste project status into pull requests, Slack messages, or project tracking documents.

When the `--format markdown` flag is passed, the command writes the same information displayed in the terminal (architecture badge, service table, phase progress, quality summary) as a well-formatted markdown file. The markdown report includes a generation timestamp and project name header.

**Why this priority**: Shareability extends the value of the status command beyond a single developer's terminal. Team leads and stakeholders who do not run SpecForge directly can still review project status. This is P2 because the terminal dashboard is the primary interface, while the markdown export serves a complementary collaboration use case.

**Independent Test**: Can be fully tested by running `specforge status --format markdown` on any initialized project and verifying the output file exists at the expected path, contains all dashboard sections, and renders correctly in a markdown viewer.

**Acceptance Scenarios**:

1. **Given** an initialized project, **When** the developer runs `specforge status --format markdown`, **Then** a file is created at `.specforge/reports/status.md` containing the architecture badge, service table, phase progress, and quality summary in valid markdown format.
2. **Given** the reports directory does not yet exist, **When** the command runs with `--format markdown`, **Then** it creates `.specforge/reports/` automatically before writing the report.
3. **Given** a previous `status.md` report exists, **When** the command runs again, **Then** the existing report is overwritten with the latest data.
4. **Given** the markdown report is generated, **When** it is opened in a markdown renderer, **Then** all tables render with correct alignment, progress bars are represented as text-based bars (e.g., `[========  ] 80%`), and status labels are bolded or emphasized.

---

### User Story 5 - Machine-Readable JSON Output (Priority: P2)

As a CI/CD pipeline, I need `specforge status --format json` to produce a structured JSON file at `.specforge/reports/status.json`, so I can programmatically query project status for pipeline gate decisions (e.g., "proceed only if all Phase 1 services are COMPLETE").

When the `--format json` flag is passed, the command writes a structured JSON file containing all status data in a machine-parseable schema. The JSON includes an architecture type field, an array of service status objects, phase progress data, and quality summary metrics.

**Why this priority**: Machine-readable output enables automation — CI/CD pipelines can gate deployments on project status, monitoring dashboards can ingest progress data, and custom tooling can build on top of the status API. This is P2 because it serves an integration use case rather than the primary developer experience.

**Independent Test**: Can be fully tested by running `specforge status --format json` and parsing the output file. Delivers value by enabling a CI/CD pipeline script to check whether a specific service's status is "COMPLETE" or whether a phase has reached 100%.

**Acceptance Scenarios**:

1. **Given** an initialized project, **When** the developer runs `specforge status --format json`, **Then** a valid JSON file is created at `.specforge/reports/status.json` containing architecture type, services array (including all manifest-declared services), phases array, and quality summary object.
2. **Given** a service is fully complete, **When** the JSON is inspected, **Then** that service's object contains `"status": "COMPLETE"`, `"implementation_percent": 100`, and all lifecycle phase fields populated.
3. **Given** a CI/CD script reads `status.json`, **When** it queries the phases array for Phase 1, **Then** it can determine programmatically whether all Phase 1 services have status "COMPLETE" and the phase completion is 100%.
4. **Given** both `--format json` and `--format markdown` are passed together, **When** the command runs, **Then** both output files are generated (they are not mutually exclusive).
5. **Given** a service exists in the manifest but has no artifacts yet, **When** the JSON is inspected, **Then** that service's object contains `"status": "NOT_STARTED"`, `"implementation_percent": 0`, and all lifecycle phase fields set to `null` (not omitted from the object).

---

### User Story 6 - Dependency Graph Visualization (Priority: P3)

As a developer, I want `specforge status --graph` to display a dependency graph showing which services are done, in progress, or blocked, so I can visually trace why a particular service cannot start and what unblocks it.

When the `--graph` flag is passed, the command appends a dependency graph to the terminal output (and to markdown/JSON reports if those formats are also requested). The graph can be rendered as ASCII art (default for terminal), or optionally as Mermaid syntax (useful for markdown reports that support Mermaid rendering).

**Why this priority**: The dependency graph is a powerful debugging tool for understanding blocking relationships, but the service table and phase progress already convey the essential information. The graph is a P3 enhancement that adds visual clarity for complex projects with non-obvious dependency chains.

**Independent Test**: Can be fully tested by running `specforge status --graph` on a project with at least 3 phases and verifying the output includes a graph where service nodes are labeled with their status (done/in-progress/blocked/not-started).

**Acceptance Scenarios**:

1. **Given** a project with 8 services across 3 phases, **When** the developer runs `specforge status --graph`, **Then** the terminal displays an ASCII dependency graph where each service is a node colored or labeled by status (COMPLETE, IN PROGRESS, BLOCKED, NOT STARTED).
2. **Given** a service is blocked because its dependency in a prior phase failed, **When** the graph is displayed, **Then** the edge from the failed dependency to the blocked service is visually distinct (e.g., dashed line or red color).
3. **Given** `--format markdown` and `--graph` are both passed, **When** the markdown report is generated, **Then** the dependency graph is included as a Mermaid code block that renders in GitHub/GitLab markdown viewers.
4. **Given** a monolithic project with no inter-module dependencies, **When** `--graph` is passed, **Then** the graph shows all modules as independent nodes with no edges.

---

### User Story 7 - Live Watch Mode (Priority: P3)

As a developer running a long multi-service orchestration, I want `specforge status --watch` to auto-refresh the terminal dashboard at a regular interval, so I can monitor progress in real time without re-running the command manually.

When the `--watch` flag is passed, the command clears and redraws the terminal dashboard at a configurable interval (default 5 seconds). The watch mode is terminal-only — it is incompatible with `--format markdown` and `--format json` since file outputs are not designed for continuous refresh. The command exits watch mode on Ctrl+C or when all services reach a terminal state (COMPLETE or FAILED).

**Why this priority**: Watch mode is a developer experience enhancement for long-running orchestration sessions. The core dashboard (P1/P2 stories) is fully useful as a one-shot command; watch mode adds convenience but is not required for the primary value proposition.

**Independent Test**: Can be fully tested by running `specforge status --watch` while a separate process modifies service state files. Delivers value by showing the dashboard update automatically without manual re-invocation.

**Acceptance Scenarios**:

1. **Given** the developer runs `specforge status --watch`, **When** a service's state changes from IN PROGRESS to COMPLETE, **Then** the terminal dashboard refreshes within the configured interval to reflect the updated status.
2. **Given** `--watch` is active with default 5-second interval, **When** 5 seconds elapse, **Then** the dashboard redraws with current data regardless of whether any state changed.
3. **Given** the developer passes `--watch` together with `--format markdown`, **When** the command starts, **Then** it displays an error: "--watch is only supported for terminal output" and exits.
4. **Given** all services reach COMPLETE or FAILED state, **When** the next refresh cycle runs, **Then** the watch mode exits automatically with a summary message.

---

### Edge Cases

- What happens when the project has no manifest (freshly initialized with only `specforge init` run)? The command displays a message indicating the project has not yet been decomposed and suggests running `specforge decompose` first.
- What happens when a service's state file is corrupted or missing? The command displays that service's row with a "UNKNOWN" status and a warning message, rather than crashing. Other services are still displayed normally.
- What happens when no services have been implemented yet (all are NOT STARTED)? The command displays the full table with all manifest-declared services showing `null`/"-" for implementation columns and "NOT STARTED" overall, along with 0% phase progress bars.
- What happens when the command is run in a directory that is not a SpecForge project? The command displays an error: "Not a SpecForge project. Run 'specforge init' first."
- What happens when a service belongs to multiple features? The features column shows all associated feature numbers (e.g., "004+006+007").
- What happens when orchestration state exists but quality reports do not? The quality summary section displays available metrics and shows "No data" for metrics that require quality reports.
- What happens when a service exists in the manifest but has zero artifacts (no spec, no plan, nothing)? It is displayed as "NOT STARTED" with all lifecycle columns showing "-" (terminal) or `null` (JSON). There is no separate "NEW" status.
- What happens when `--watch` is combined with `--format markdown` or `--format json`? The command displays an error: "--watch is only supported for terminal output" and exits with a non-zero code.
- What happens when any service is in FAILED state? The command exit code is 1 (instead of 0) to enable CI/CD gating. The dashboard still displays fully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect architecture type (microservice, monolith, modular monolith) from the project manifest and display the corresponding badge at the top of the status output.
- **FR-002**: System MUST display a service status table with one row per declared service/module, including columns for: associated features, spec status, plan status, task status, implementation percentage, test results (pass/total), Docker status (microservice only), and overall status.
- **FR-003**: System MUST calculate overall service status as one of: COMPLETE (all phases done, all checks pass), IN_PROGRESS (implementation underway), PLANNING (spec or plan in progress, no implementation), NOT_STARTED (no artifacts exist), BLOCKED (dependencies incomplete), FAILED (implementation or quality checks failed), or UNKNOWN (state files corrupted or unreadable). Display format uses spaces (e.g., "IN PROGRESS"); data model and JSON use underscores (e.g., `IN_PROGRESS`).
- **FR-004**: System MUST display phase progress bars with completion percentages, calculated from the aggregate status of services within each phase.
- **FR-005**: System MUST aggregate quality metrics from all services' quality reports and orchestration state into a single summary panel showing: service counts by status (all 7 statuses: COMPLETE, IN_PROGRESS, PLANNING, NOT_STARTED, BLOCKED, FAILED, UNKNOWN — must sum to services_total), task counts (total/complete/failed), average test coverage across implemented services, Docker image status (microservice only), contract test results (microservice only), and auto-fix success rate.
- **FR-006**: System MUST support `--format terminal` (default), `--format markdown`, and `--format json` output formats. Terminal and markdown/json are not mutually exclusive — multiple formats can be requested simultaneously.
- **FR-007**: System MUST write markdown reports to `.specforge/reports/status.md` and JSON reports to `.specforge/reports/status.json`, creating the reports directory if it does not exist.
- **FR-008**: System MUST support `--graph` flag to display a service dependency graph with status-labeled nodes. Terminal output uses ASCII art; markdown output uses Mermaid syntax.
- **FR-009**: System MUST show Docker columns only in microservice architecture mode. Both monolith and modular-monolith modes omit Docker columns entirely. Modular-monolith mode shows module boundary compliance instead of Docker.
- **FR-010**: System MUST gracefully handle missing or corrupted state files by displaying "UNKNOWN" status for affected services and emitting a warning, without crashing or omitting other services.
- **FR-011**: System MUST display a helpful error when run outside a SpecForge project or when the project has not been decomposed.
- **FR-012**: System MUST include a generation timestamp in both markdown and JSON reports.
- **FR-013**: System MUST read service-to-feature mappings from the manifest to populate the features column accurately, supporting services associated with multiple features.
- **FR-014**: System MUST integrate with the existing `pipeline-status` command's data sources where applicable, superseding it as the comprehensive project status view.
- **FR-015**: System MUST treat the project manifest as the authoritative source for the service list. All manifest-declared services are displayed; services with zero artifacts are shown as "NOT STARTED" with no separate "NEW" status.
- **FR-016**: System MUST support a `--watch` flag (P3, terminal-only) that refreshes the dashboard at a configurable interval (default 5 seconds). The `--watch` flag is incompatible with `--format markdown` and `--format json` (file outputs are not refreshed).
- **FR-017**: System MUST return exit code 0 when no service is in FAILED state, and exit code 1 when any service is FAILED. This enables CI/CD pipeline gating without parsing JSON.
- **FR-018**: In JSON output, services with no artifacts MUST have all lifecycle fields set to `null` (not omitted from the object), `"status": "NOT_STARTED"`, and `"implementation_percent": 0` to ensure CI/CD consumers can enumerate all expected services and distinguish "not started" from "missing data".

### Key Entities

- **Project Status Snapshot**: A point-in-time capture of the entire project's state — architecture type, list of service statuses, phase progress, and quality metrics. Serves as the data model backing all three output formats.
- **Service Status**: Per-service record containing associated feature numbers, lifecycle phase statuses (spec, plan, tasks, implementation, tests, Docker), quality check results, and an overall status label.
- **Phase Progress**: Per-phase record containing the phase number, list of services in the phase, aggregate completion percentage, and blocking status.
- **Quality Summary**: Aggregated metrics across all services — service counts by status, task counts, average test coverage, Docker build counts, contract test results, auto-fix success rate.

## Assumptions

- The project manifest (`.specforge/manifest.json`) is the source of truth for architecture type, service declarations, service-to-feature mappings, and dependency graph. It is produced by Feature 004 (Architecture Decomposer).
- Per-service state files in `.specforge/features/<slug>/` contain spec status, plan status, task status, and implementation progress. These are produced by Features 005–009.
- Quality reports (`.quality-report.json` per service) are produced by Feature 010 (Quality Validation System) and contain test results, coverage data, Docker status, and contract test results.
- Orchestration state (`.specforge/orchestration-state.json`) is produced by Feature 011 (Implementation Orchestrator) and contains phase definitions, phase completion data, and auto-fix statistics.
- The existing `pipeline-status` command provides per-service pipeline phase information. Feature 012 supersedes it by adding phase progress, quality summary, multi-format output, and dependency graph visualization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can assess the complete project status — all services, all phases, all quality metrics — in a single command invocation taking less than 3 seconds for projects with up to 20 services.
- **SC-002**: The status dashboard accurately reflects the current state of every service, with zero discrepancies between what the dashboard reports and what the underlying state files contain.
- **SC-003**: A team lead can generate and share a markdown status report in under 10 seconds, and the report renders correctly in GitHub, GitLab, and standard markdown viewers.
- **SC-004**: A CI/CD pipeline can programmatically determine project readiness by parsing `status.json`, enabling automated gate decisions with no manual status inspection.
- **SC-005**: The status command handles projects in any state — from freshly initialized (no services) to fully complete (all services done) — without errors, always displaying an accurate representation.
- **SC-006**: When a service's state is corrupted or missing, the dashboard still displays all other services correctly and clearly identifies the problematic service, achieving graceful degradation rather than total failure.
