# Architecture Alignment Checklist: Sub-Agent Execution Engine

**Purpose**: Validate that requirements for context isolation, crash safety, architecture-mode differentiation, and execution lifecycle are complete, clear, and consistent.
**Created**: 2026-03-17
**Feature**: [spec.md](../spec.md)
**Depth**: Standard | **Audience**: Reviewer (PR) | **Timing**: Pre-implementation gate

## Context Isolation

- [ ] CHK001 - Is the exhaustive allowlist of files the sub-agent may access explicitly enumerated, not just described narratively? [Clarity, Spec §FR-002, §FR-004]
- [ ] CHK002 - Are the exact directory paths that constitute "implementation code" (excluded) defined distinctly from "contract files" (included)? [Clarity, Spec §US3 Scenario 1]
- [ ] CHK003 - Is the isolation mechanism described as enforcement-by-construction (allowlist) rather than advisory filtering? [Completeness, Plan §D3]
- [ ] CHK004 - Are requirements defined for what happens when a dependency service has no `contracts/` directory? [Edge Case, Spec §Edge Cases]
- [ ] CHK005 - Is the context isolation requirement specified for shared-infra execution mode, where project-wide context is expected? [Consistency, Spec §US4 vs §US3]
- [ ] CHK006 - Are requirements clear on whether governance prompts are loaded for ALL 7 domains or filtered by task type? [Clarity, Spec §FR-002, Plan §D3 Step 2]

## Token Budget & Context Management

- [ ] CHK007 - Is the 100K token budget defined as a hard limit, soft warning, or configurable threshold? [Clarity, Plan §D13]
- [ ] CHK008 - Is the token estimation method (chars/4) documented with its known inaccuracy and the rationale for accepting it? [Completeness, Research §R1]
- [ ] CHK009 - Is the context truncation priority order specified for all context sections, with clear rules for what gets cut first? [Completeness, Plan §D3]
- [ ] CHK010 - Are requirements defined for notifying the user when context truncation occurs? [Gap]
- [ ] CHK011 - Is the behavior specified when the current task description alone exceeds the token budget? [Edge Case, Gap]
- [ ] CHK012 - Are requirements consistent between "estimated_tokens" as a warning-only field and the truncation behavior that actively removes content? [Consistency, Data Model vs Plan §D3 Step 7]

## Shared Infrastructure Ordering

- [ ] CHK013 - Is the prerequisite check for shared infrastructure explicitly defined as blocking (error + halt) vs advisory (warn + proceed)? [Clarity, Spec §FR-013]
- [ ] CHK014 - Are requirements specified for how the engine determines shared-infra completion status — does it check execution state, file existence, or both? [Gap, Spec §US4 Scenario 2]
- [ ] CHK015 - Is the shared-infra ordering requirement defined for modular-monolith (partial infra: contracts + auth only) in addition to microservice? [Completeness, Spec §FR-012, Feature 008 §D5]
- [ ] CHK016 - Are requirements specified for re-running `--shared-infra` after it has already completed (idempotency or overwrite)? [Gap]
- [ ] CHK017 - Is the "same working branch" commit strategy for shared infra consistent with the per-service commit strategy? [Consistency, Clarification §Q2]

## Docker & Container Verification

- [ ] CHK018 - Are the specific Docker commands (build, run, health check, compose) documented with expected inputs and outputs? [Completeness, Plan §D9]
- [ ] CHK019 - Is the timing of Docker image build explicitly defined as "after all code tasks" with no ambiguity about which tasks count as "code tasks"? [Clarity, Clarification §Q4, Spec §FR-022]
- [ ] CHK020 - Are requirements defined for Docker not being installed on the developer's machine (graceful degradation vs hard failure)? [Edge Case, Gap]
- [ ] CHK021 - Is the docker-compose test profile lifecycle (up before integration tests, down after) specified with timeout and failure handling? [Completeness, Spec §FR-029, Edge Case §docker-compose]
- [ ] CHK022 - Are health check endpoint conventions (path, expected response, timeout) explicitly specified rather than implied? [Clarity, Plan §D13]

## Contract Resolution & Dependency Contracts

- [ ] CHK023 - Are the expected contract file formats explicitly listed (api-spec.json, event schemas, protobuf defs, etc.)? [Completeness, Spec §FR-003]
- [ ] CHK024 - Is the non-blocking fallback for missing contracts (warn and skip) consistent with the isolation requirement that only permitted files are included? [Consistency, Plan §D8 vs §D3]
- [ ] CHK025 - Are requirements defined for contract version mismatches between what was generated (Feature 008) and what the service expects? [Edge Case, Spec §Edge Cases]
- [ ] CHK026 - Is the Pact consumer test generation scope defined — does the executor generate tests, or only provide context for the agent to generate them? [Clarity, Spec §FR-028]

## Crash Safety & Atomic State

- [ ] CHK027 - Is the atomic write mechanism (temp file + os.replace) explicitly required, or just referenced as an implementation pattern? [Clarity, Plan §D10]
- [ ] CHK028 - Are requirements defined for execution state saved between the task-completion commit and the state-file write (the crash window)? [Edge Case, Gap]
- [ ] CHK029 - Is the lock stale threshold (60 minutes) justified relative to expected task execution durations? [Completeness, Plan §D13]
- [ ] CHK030 - Are requirements defined for lock file cleanup on normal exit (not just stale detection)? [Gap, Spec §FR-019]
- [ ] CHK031 - Is the PID-based stale detection specified for cross-platform behavior (Windows vs Unix process IDs)? [Completeness, Research §R6]

## Resume Capability

- [ ] CHK032 - Is the behavior for resumed tasks that were "in-progress" at interruption explicitly defined as "restart from scratch" rather than "continue"? [Clarity, Spec §US5 Scenario 3]
- [ ] CHK033 - Are requirements defined for validation of execution state against a modified `tasks.md` (task IDs added, removed, or reordered)? [Completeness, Spec §FR-017]
- [ ] CHK034 - Is the "orphaned task ID" handling specified with clear rules for what constitutes a match vs mismatch? [Clarity, Spec §Edge Cases]
- [ ] CHK035 - Are requirements defined for resuming when shared infrastructure has been modified since the last service task committed? [Gap]
- [ ] CHK036 - Is the user prompt behavior on resume-without-flag (warn + ask) specified with both interactive and non-interactive mode handling? [Completeness, Spec §FR-018]

## Auto-Fix Loop Termination

- [ ] CHK037 - Is the maximum attempt count (3) defined as a hard default with configurable override, and is the override mechanism specified? [Clarity, Spec §FR-009, CLI Contract]
- [ ] CHK038 - Is regression detection defined with measurable criteria (what constitutes a "new failure" vs the same failure with different output)? [Measurability, Spec §FR-010]
- [ ] CHK039 - Are requirements defined for the revert scope — does revert target only fix-attempt files, or all uncommitted changes? [Clarity, Plan §D6]
- [ ] CHK040 - Is the halt behavior after exhausted retries specified with all required outputs (diagnostic report, state file, user message)? [Completeness, Spec §FR-011]
- [ ] CHK041 - Are requirements consistent between task-level auto-fix (FR-009) and verification-level auto-fix (FR-023) regarding shared retry config? [Consistency, Spec §FR-009 vs §FR-023]

## Architecture-Mode Differentiation (Monolith Exclusions)

- [ ] CHK042 - Are ALL microservice-only features explicitly listed as excluded for monolithic mode (Docker, gRPC, contracts, gateway, health checks, compose, events)? [Completeness, Spec §FR-021, §FR-024]
- [ ] CHK043 - Is modular-monolith defined as a distinct mode with its own inclusion/exclusion rules separate from both microservice and monolith? [Clarity, Spec §FR-024, Feature 008 §D5]
- [ ] CHK044 - Are the three architecture modes' behavior differences documented in a single comparison matrix or table? [Completeness, Gap]
- [ ] CHK045 - Is the `DockerManager | None` injection pattern (None for monolith) specified as the mechanism for architectural exclusion, or is it left as an implementation detail? [Clarity, Plan §D2]
- [ ] CHK046 - Are requirements defined for what "standard build/lint/test checks" means for monolith mode — are these the same three commands (build + ruff + pytest) regardless of architecture? [Clarity, Spec §FR-024]

## Notes

- Items marked `[Gap]` identify requirements not currently addressed in spec or plan
- Items marked `[Consistency]` flag potential conflicts between spec sections
- 9 user-provided focus areas expanded into 46 traceable checklist items
- Traceability: 43/46 items (93%) include explicit section references
