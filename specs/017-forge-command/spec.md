# Feature Specification: Forge Command — Zero-Interaction Full Spec Generation

**Feature Branch**: `017-forge-command`
**Created**: 2026-03-19
**Status**: Draft
**Input**: User description: "specforge forge command: single entry point that takes one prompt and produces all spec artifacts for all services with zero human interaction"

## Clarifications

### Session 2026-03-19

- Q: Should forge-state.json track per-service only or per-service + per-phase? → A: Per-service + per-phase. forge-state.json records which phase each service completed last, so resume restarts at the exact failed/incomplete phase rather than re-running all 7 phases for a partially-complete service.
- Q: Should forge auto-detect --arch from the project description? → A: No auto-detection. Default to monolithic unless `--arch` is explicitly passed. Keyword-matching is fragile and causes surprising over-decomposition. Users who want microservice architecture must state it explicitly.
- Q: Should HttpApiProvider (direct Anthropic HTTP API) be included? → A: No. Removed from scope. The forge command uses the existing SubprocessProvider for all LLM calls, keeping the provider layer unchanged. A direct HTTP API provider can be added in a future feature if performance optimization is needed.
- Q: Should --model flag be included without HttpApiProvider? → A: No. SubprocessProvider uses each CLI tool's default model. Model selection via subprocess flags varies across providers, adding provider-specific complexity with no clear benefit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Single Command Full Spec Generation (Priority: P1)

As a developer, I want to run a single `specforge forge` command with a project description and receive complete spec artifacts for all discovered services, so that I never have to manually orchestrate multiple commands or intervene during generation.

**Why this priority**: This is the core value proposition of the entire feature. Without this end-to-end orchestration, the forge command has no reason to exist. Every other story builds on this foundational flow: auto-init → decompose → parallel spec generation → validation → report.

**Independent Test**: Can be fully tested by running `specforge forge "Create a PersonalFinance webapp" --arch microservice` on a directory with `.specforge/` already initialized, and verifying that manifest.json is created, all service directories under `.specforge/features/` contain 7 complete artifacts each, and a forge-report.md is generated.

**Acceptance Scenarios**:

1. **Given** a project directory with `.specforge/` initialized and a configured AI provider, **When** the user runs `specforge forge "Create a PersonalFinance webapp" --arch microservice`, **Then** the system discovers services via LLM, creates manifest.json, runs 7-phase spec pipelines for all services in parallel, and generates a forge-report.md summarizing all created artifacts.
2. **Given** a project with 8 discovered services and 4 default parallel workers, **When** the forge command runs the spec generation stage, **Then** up to 4 services run their pipelines concurrently, each producing all 7 artifacts independently without cross-service contamination.
3. **Given** the forge command completes all stages successfully, **When** the user inspects `.specforge/features/`, **Then** every discovered service has: spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, and tasks.md — all with substantive content (not empty templates).
4. **Given** the forge command is running, **When** a live progress display is shown, **Then** the user sees the current stage, per-service phase progress, overall progress bar, and elapsed time — all updating in real time.

---

### User Story 2 — Auto-Initialization for New Projects (Priority: P2)

As a developer starting from scratch, I want the forge command to automatically initialize the project if `.specforge/` does not exist, so that I never need to run `specforge init` separately before forging.

**Why this priority**: Eliminating the separate init step removes a friction point for new users and enables true single-command operation. Without this, the "zero interaction" promise breaks for first-time use.

**Independent Test**: Can be tested by running `specforge forge "Build a TODO app" --arch monolithic` in an empty directory (no `.specforge/`) and verifying that `.specforge/` is created with detected agent, config.json with defaults, and then the full forge pipeline proceeds.

**Acceptance Scenarios**:

1. **Given** a project directory without `.specforge/`, **When** the user runs `specforge forge "Build a TODO app" --arch monolithic`, **Then** the system creates `.specforge/` with auto-detected agent and stack, creates config.json with defaults, and proceeds to the decompose stage without any prompts.
2. **Given** a project directory with an existing `.specforge/` and config.json, **When** the user runs `specforge forge`, **Then** the init stage is skipped entirely and the system proceeds directly to decompose.
3. **Given** a project directory without `.specforge/` and the `--skip-init` flag is passed, **When** the user runs `specforge forge --skip-init`, **Then** the system reports an error indicating that `.specforge/` must be initialized first.

---

### User Story 3 — Resume After Interruption (Priority: P3)

As a developer whose forge run was interrupted mid-generation, I want to resume from where it left off rather than starting over, so that completed work is preserved and only remaining services are re-generated.

**Why this priority**: A full forge run can take 10-20 minutes. Losing all progress due to a network hiccup, accidental Ctrl+C, or system crash would be extremely frustrating. Resume capability protects that investment.

**Independent Test**: Can be tested by running `specforge forge`, interrupting it after decompose completes but during spec generation, then running `specforge forge --resume` and verifying that init and decompose are skipped while only incomplete services are re-processed.

**Acceptance Scenarios**:

1. **Given** a forge run was interrupted after decompose completed but during spec generation (3 of 8 services complete), **When** the user runs `specforge forge --resume`, **Then** the system skips init and decompose, reads the existing manifest, and only runs pipelines for the 5 incomplete services.
2. **Given** a service failed 3 times during a previous forge run, **When** `specforge forge --resume` runs, **Then** that service is retried up to 3 additional times. If it fails again, it is marked as permanently failed and the forge continues with other services.
3. **Given** a forge-state.json file exists and the user runs `specforge forge` without `--resume`, **When** the system detects the existing state, **Then** it prompts: "Previous forge run detected. Overwrite / Resume / Abort?" (or proceeds silently if `--force` is passed).
4. **Given** forge-state.json is corrupt or unreadable, **When** `specforge forge --resume` is run, **Then** the system logs a warning and starts a fresh forge run instead of crashing.

---

### User Story 4 — Enriched, Detailed Spec Artifacts (Priority: P4)

As a developer, I want the forge command to produce spec artifacts that are detailed and substantive rather than superficial template fill-ins, so that each artifact provides genuine value for implementation planning.

**Why this priority**: The quality of generated specs directly determines their usefulness. Thin, superficial specs mean developers still need extensive manual rework, undermining the value of automation.

**Independent Test**: Can be tested by running `specforge forge "E-commerce platform" --arch microservice`, inspecting a generated spec.md, and verifying it contains detailed user stories with acceptance scenarios, specific functional requirements, and measurable success criteria — not generic placeholder text.

**Acceptance Scenarios**:

1. **Given** the forge command runs a spec phase for a particular service, **When** the prompt is assembled for that phase, **Then** the system instructions include: explicit output structure with all required sections, architecture-specific guidance, applicable governance rules, quality thresholds, examples of good output, and anti-patterns to avoid.
2. **Given** a research phase runs after spec generation, **When** the prior spec.md is fed as context, **Then** the context includes structured extracts (user stories as bullets, FR numbers, non-functional requirements) rather than the raw 3000+ word document.
3. **Given** enriched prompts are used, **When** the LLM generates an artifact, **Then** the output is at least 1500 words for spec.md, includes domain-specific details relevant to the service, and does not contain generic placeholder text.

---

### User Story 5 — Dry Run for Prompt Preview (Priority: P5)

As a developer, I want to preview all prompts that would be sent to the LLM without actually calling it, so that I can review, adjust, and understand what the system will do before committing to a potentially costly forge run.

**Why this priority**: Transparency and cost control. A full forge run can make 56+ LLM calls. Previewing prompts lets developers verify their input before spending API credits, and helps debug prompt quality issues.

**Independent Test**: Can be tested by running `specforge forge "My App" --dry-run` and verifying that `.prompt.md` files appear for each phase of each service, no LLM calls are made, and the output explains what would happen in a real run.

**Acceptance Scenarios**:

1. **Given** the user runs `specforge forge "My App" --arch microservice --dry-run`, **When** the command completes, **Then** each service directory contains `.prompt.md` files for all 7 phases showing the exact prompts that would be sent.
2. **Given** `--dry-run` is active, **When** the forge command runs, **Then** zero LLM calls are made (verifiable by absence of API logs or subprocess invocations).
3. **Given** `--dry-run` completes, **When** the user reviews the output, **Then** a summary shows: number of services discovered, number of prompts generated, estimated token usage, and the file paths to all generated prompt files.

---

### User Story 6 — Provider-Agnostic Operation (Priority: P6)

As a developer using any supported LLM provider (Claude, Copilot, Gemini, Codex), I want the forge command to work identically regardless of which provider is configured, so that I am not locked into a specific vendor.

**Why this priority**: Provider flexibility ensures the forge command works across the entire existing user base without requiring migration or special configuration.

**Independent Test**: Can be tested by configuring different agents in config.json (claude, copilot, gemini) and verifying that `specforge forge` produces equivalent artifacts with each provider.

**Acceptance Scenarios**:

1. **Given** config.json has `"agent": "gemini"`, **When** `specforge forge` runs, **Then** the system uses SubprocessProvider for Gemini CLI and generates all artifacts identically to any other provider.
2. **Given** config.json has `"agent": "claude"`, **When** `specforge forge` runs, **Then** the system uses SubprocessProvider for Claude CLI and generates all artifacts correctly.
3. **Given** config.json has `"agent": "copilot"`, **When** `specforge forge` runs, **Then** the system uses SubprocessProvider for Copilot CLI and generates all artifacts correctly.

---

### Edge Cases

- What happens when the LLM returns invalid JSON during the decompose stage?
  - The system retries the LLM call up to 3 times with adjusted prompting. If all retries fail, it falls back to the rule-based DomainAnalyzer to produce a manifest from the project description.
- What happens when one service's spec phase fails 3 times consecutively?
  - The service is marked as permanently failed in forge-state.json, the remaining services continue, and the forge-report.md includes diagnostic details for the failed service.
- What happens when assembled context exceeds the LLM's token budget?
  - The ArtifactExtractor switches from full structured extraction to compressed summaries (key-value pairs, bullet lists) for prior artifacts, reducing token usage while preserving critical information.
- What happens when the user runs forge twice on the same project?
  - If forge-state.json exists from a previous run, the system asks: "Previous forge run detected. Overwrite / Resume / Abort?" The `--force` flag silently overwrites, and `--resume` picks up from the last successful stage.
- What happens when the LLM provider rate-limits concurrent requests?
  - Each parallel worker's LLM provider instance applies independent exponential backoff. If sustained rate limiting occurs, workers queue naturally, and the live dashboard reflects slower progress.
- What happens when all services fail during spec generation?
  - The forge-report.md is still generated, listing all failures with per-service diagnostic information. The exit code is non-zero and the summary clearly indicates total failure.
- What happens when forge-state.json is corrupt or unreadable?
  - The `--resume` flag logs a warning about the corrupt state file and starts a fresh forge run rather than crashing.
- What happens when network connectivity is lost mid-generation?
  - In-progress artifacts are saved as `.draft.md` files. The forge-state.json is updated to mark affected services as incomplete. On resume, these services are retried from the last incomplete phase.
- What happens when the user passes `--arch` but the LLM decompose response ignores the architecture type?
  - The system enforces the user-specified architecture type via post-parse validation of the LLM response, overriding any architecture type returned by the LLM.
- What happens when `--dry-run` is combined with `--resume`?
  - The system generates prompt files only for services that would be re-run on resume (incomplete/failed), skipping completed services.
- What happens when no AI provider is available (no CLI tools installed, no API key)?
  - The system reports a clear error message listing the supported providers and how to configure them, then exits with exit code 2.
- What happens when `--max-parallel` is set to 0 or a negative number?
  - Click's type validation rejects the value (IntRange min=1). The user sees a standard Click error: "Invalid value for '--max-parallel': 0 is not in the range x>=1."
- What happens when the LLM decompose returns zero services?
  - The system falls back to the DomainAnalyzer. If DomainAnalyzer also produces zero services (possible for very vague descriptions), the forge run fails with exit code 2 and a clear message: "No services could be identified from the provided description."
- What happens when `--resume` is combined with `--force`?
  - Click enforces mutual exclusion — the user sees: "Error: --resume and --force are mutually exclusive." The command does not start.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `specforge forge <description>` CLI command that orchestrates the complete spec generation pipeline: auto-init → LLM decompose → parallel spec generation → validation → report generation — in a single unattended invocation.
- **FR-002**: System MUST accept the following flags on the forge command: `--arch <type>` (architecture type, default: monolithic), `--stack <stack>` (technology stack, passed to auto-init and decompose for stack-specific guidance), `--max-parallel N` (concurrent worker limit, must be ≥1), `--dry-run` (preview prompts without LLM calls), `--resume` (continue from interrupted run), `--skip-init` (skip auto-initialization), and `--force` (overwrite existing forge state without prompting). The flags `--resume` and `--force` are mutually exclusive. An empty description string MUST produce a clear error message.
- **FR-003**: System MUST auto-initialize `.specforge/` with auto-detected agent and stack when the forge command runs and no `.specforge/` directory exists, unless `--skip-init` is passed.
- **FR-004**: System MUST call the LLM with an enriched decompose prompt to discover services/modules and produce a manifest.json. If the LLM returns invalid JSON after 3 retries, the system MUST fall back to the rule-based DomainAnalyzer.
- **FR-005**: System MUST default to monolithic architecture when `--arch` is not specified (no keyword-based auto-detection from the description). When `--arch` is specified, the system MUST enforce the user-specified type via post-parse validation of the LLM decompose response, overriding any conflicting architecture type in the LLM output.
- **FR-006**: System MUST run 7-phase spec pipelines for all discovered services concurrently using the existing ParallelPipelineRunner, with configurable worker count (default: 4, overridable via `--max-parallel`).
- **FR-007**: System MUST enrich phase prompts with detailed system instructions (50-100 lines per phase) including: explicit output structure, architecture-specific guidance, applicable governance rules, quality thresholds, examples of good output, and anti-patterns to avoid.
- **FR-008**: System MUST extract structured information from prior artifacts when assembling context for subsequent phases — user stories as bullet lists from spec.md, decision key-value pairs from research.md, entity/field/relationship details from data-model.md, edge-case IDs with severity from edge-cases.md — rather than concatenating raw artifact text.
- **FR-009**: System MUST persist forge progress in `.specforge/forge-state.json` after each stage completion and after each service phase completion, tracking: current stage (one of: init, decompose, spec_generation, validation, report), and per-service state including last completed phase (0-7 where 0=not started), status (pending/in_progress/complete/failed/permanently_failed), retry count (resets to 0 on each new `--resume` invocation), error details (string or null), and timestamp of last update — enabling resume at the exact phase that failed.
- **FR-010**: System MUST support `--resume` which reads forge-state.json, skips completed stages, and re-runs only incomplete or failed services (up to 3 retries per service per resume invocation before marking as permanently failed). Services with `.draft.md` files from a previous interruption (FR-014) MUST be retried from the phase that produced the draft.
- **FR-011**: System MUST display a live progress dashboard during the forge operation using Rich.live(), showing: current stage name, per-service progress table (service name, current phase, status), overall progress bar, and elapsed time.
- **FR-012**: System MUST generate `.specforge/reports/forge-report.md` upon completion, listing: all created artifacts per service, failed services with diagnostic info, total elapsed time, and per-stage timing breakdown.
- **FR-013**: System MUST support `--dry-run` which runs auto-init (if needed) and decompose via LLM (or reads existing manifest if one exists), generates `.prompt.md` files for each phase of each service, makes zero LLM calls for spec generation phases, and reports estimated token usage (calculated as character count / 4). The `--dry-run` flag combined with `--force` overwrites existing prompt files silently.
- **FR-014**: System MUST handle Ctrl+C gracefully during any stage: in-progress LLM calls save partial output as `.draft.md`, forge-state.json is updated with current progress, and the system exits with a message indicating how to resume.
- **FR-015**: System MUST use the existing SubprocessProvider retry logic with exponential backoff for all LLM calls. No separate retry implementation is needed — this FR confirms forge inherits existing behavior.
- **FR-016**: System MUST work identically across all supported LLM providers (Claude, Copilot, Gemini, Codex) using the existing SubprocessProvider infrastructure.
- **FR-017**: System MUST validate that all discovered services have all 7 artifacts (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) after spec generation completes, reporting any missing artifacts as errors in the forge report.
- **FR-018**: System MUST detect an existing forge-state.json when the user runs `specforge forge` without `--resume` or `--force`, and prompt: "Previous forge run detected. Overwrite / Resume / Abort?"
- **FR-019**: System MUST exit with code 0 on success (all services complete), code 1 on partial failure (some services permanently failed), code 2 on total failure (all services failed or fatal error), and code 0 on successful `--dry-run` completion.
- **FR-020**: System MUST NOT start a forge run if another forge process is already writing to the same `.specforge/` directory. Detection via forge-state.json `status: running` field with PID and timestamp; stale locks (>1 hour) are automatically cleared.

### Key Entities

- **ForgeOrchestrator**: Coordinates all forge stages (init, decompose, spec generation, validation, report) in sequence. Owns the forge-state.json lifecycle and delegates to existing subsystems for each stage.
- **ForgeState**: Represents the persisted state of a forge run — current stage, per-service status including last completed phase (1-7), retry counts, timing data, and error details. Serialized to `.specforge/forge-state.json` for fine-grained resume capability.
- **ArtifactExtractor**: Reads completed spec artifacts and produces structured summaries (bullets, key-value pairs, entity lists) for use as context in subsequent phases. Replaces raw text concatenation.
- **EnrichedPromptBuilder**: Renders Jinja2 enrichment templates that output 50-100 lines of system instructions per phase, incorporating architecture guidance, governance rules, quality thresholds, and examples.
- **ForgeProgress**: A Rich Live display component that renders current stage, per-service progress table, overall progress bar, and elapsed time. Receives updates from ParallelPipelineRunner callbacks.
- **ForgeReport**: The data model for the completion report — per-service artifact inventory, failure diagnostics, timing breakdown. Rendered to `.specforge/reports/forge-report.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can produce all spec artifacts for a full multi-service project by running exactly one command with zero manual intervention at any point.
- **SC-002**: Generated spec artifacts contain at least 1500 words each for spec.md and plan.md, with domain-specific detail rather than generic template fill-in.
- **SC-003**: After an interrupted forge run, `--resume` recovers and completes the remaining work without re-doing any successfully completed services.
- **SC-004**: The live dashboard updates at least every 5 seconds during active generation, showing accurate per-service phase progress.
- **SC-005**: Token usage for phase prompts with structured artifact context (measured as prompt character count / 4) is at least 30% lower than the same prompt assembled via raw artifact concatenation, validated by comparing prompt sizes across at least 3 test projects.
- **SC-006**: 90% of forge runs complete with all services successful on the first attempt (no permanent failures), given a stable LLM provider connection.
- **SC-007**: The `--dry-run` flag produces complete prompt files for all phases of all services with zero LLM calls, enabling full prompt review before committing to a real run.

## Assumptions

- The existing ParallelPipelineRunner (Feature 016) provides the concurrent execution infrastructure needed for Stage 3. The forge command orchestrates it rather than reimplementing parallelism.
- The existing PipelineOrchestrator (Feature 005) handles the 7-phase per-service pipeline. The forge command feeds it enriched prompts and structured context but does not alter the phase execution sequence.
- Auto-initialization reuses the existing `specforge init` logic (Feature 001) in a non-interactive mode, auto-detecting agent and stack without prompts.
- The DomainAnalyzer fallback for decompose failures (Feature 004) exists and can produce a reasonable manifest from a project description alone, even without LLM assistance.
- Governance prompt files (Feature 003) are available for enriched prompt assembly. If no governance files exist for the project, enriched prompts omit governance rules gracefully.
- The existing `os.replace()` atomic write strategy is sufficient for concurrent forge-state.json updates since only the ForgeOrchestrator writes to this file (individual service states are in separate per-service files).
- All LLM calls use the existing SubprocessProvider, which shells out to CLI tools (claude, gh copilot suggest, gemini chat, etc.). A direct HTTP API provider is out of scope for this feature and can be added as a future optimization.
