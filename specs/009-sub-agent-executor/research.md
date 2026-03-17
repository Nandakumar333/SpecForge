# Research: Sub-Agent Execution Engine

**Feature**: 009-sub-agent-executor  
**Date**: 2026-03-17

## R1: Token Budget Estimation Strategy

**Decision**: Use character-count / 4 as a rough token estimate, with configurable budget (default 100K tokens).

**Rationale**: Token counting is model-specific (GPT tokenizer ≠ Claude tokenizer). A character-based heuristic (~4 chars/token for English text) provides a practical upper bound that works across models. The budget is configurable via `CONTEXT_TOKEN_BUDGET` in config.py, so users can tune for their specific model.

**Alternatives considered**:
- `tiktoken` library for precise GPT token counting — adds external dependency for minimal benefit; doesn't generalize to non-GPT models
- No budget tracking — risks exceeding model context window silently, causing truncation or errors
- Per-section hard limits — too rigid; wastes budget when some sections are naturally small

## R2: Git Operations for Auto-Commit and Revert

**Decision**: Use GitPython (existing dependency) for commit and revert operations. Commits are atomic per-task. Reverts use `git checkout -- <files>` for auto-fix regression rollback.

**Rationale**: GitPython is already a project dependency (used in `git_ops.py` for scaffold). Subprocess-based git is an alternative but loses the structured error handling that GitPython provides. The auto-fix revert strategy uses `git checkout` on specific files rather than `git reset` because we want to preserve the original task changes and only revert the fix attempt.

**Alternatives considered**:
- `subprocess.run(["git", ...])` — works but loses structured error objects; requires manual parsing of git stderr
- `git stash` for fix attempts — more complex state management; stash conflicts are harder to debug than checkout
- Full `git reset --hard` on regression — too aggressive; destroys the original task work

## R3: Mode B Agent Integration Pattern

**Decision**: Agent call via subprocess with stdin/stdout piping. Agent detection reuses existing `agent_detector.py` (shutil.which-based). Retry with exponential backoff (1s, 2s, 4s), fallback to Mode A.

**Rationale**: SpecForge already has agent detection infrastructure. Each supported agent (claude, copilot, gemini, cursor, windsurf, codex) has a known CLI binary. The subprocess approach is agent-agnostic — any agent with a CLI interface works. Feature 009 provides the prompt; the agent's CLI handles the rest.

**Alternatives considered**:
- HTTP API integration per agent — requires API keys, rate limiting, and per-agent adapters; much higher complexity
- Plugin-based agent system — overkill for v1; can evolve later using existing plugin architecture
- Mode B only (no Mode A) — excludes users who prefer manual control; Mode A is simpler and always works

## R4: Pact Consumer-Driven Contract Testing

**Decision**: Generate Pact consumer tests in the service directory, with provider verification against shared contract stubs (not live services).

**Rationale**: Pact is the industry standard for consumer-driven contract testing in microservice architectures. Consumer tests capture what the service *expects* from its dependencies. Provider stubs are derived from shared contract definitions (Feature 008 cross-service-infra). This enables testing without running dependent services.

**Alternatives considered**:
- Schema-only validation (JSON Schema / OpenAPI) — validates structure but not behavior (e.g., missing error responses)
- Integration tests against live services — requires all services to be running; fragile and slow
- Custom stub generation — reinvents what Pact already provides

## R5: Docker-Compose Test Profile Lifecycle

**Decision**: Integration test tasks invoke `docker-compose --profile test up -d` before execution and `docker-compose --profile test down` after quality checks. The test profile is defined in the shared infrastructure phase.

**Rationale**: Docker Compose profiles allow separating test infrastructure (database, message broker stubs) from production services. The `test` profile spins up only what integration tests need. Lifecycle is managed per-task rather than per-session to avoid leaving stale containers.

**Alternatives considered**:
- Testcontainers library — adds Python dependency; docker-compose is already available and language-agnostic
- Keep compose running for entire implementation session — risk of stale containers, port conflicts, and resource exhaustion
- In-memory test doubles (SQLite, fake broker) — faster but doesn't validate real infrastructure behavior

## R6: File-Based Lock Implementation

**Decision**: Reuse the atomic lock pattern from `pipeline_lock.py` (O_CREAT|O_EXCL) with stale detection (60-minute threshold) and PID validation.

**Rationale**: The pipeline lock implementation is battle-tested in Features 005-008. The same cross-platform atomic locking approach works for execution locks. The stale threshold is longer (60 min vs 30 min) because implementation tasks take longer than spec generation tasks.

**Alternatives considered**:
- fcntl.flock / msvcrt.locking — platform-specific; existing O_EXCL approach is cross-platform
- Database-based locking — overkill for a CLI tool
- No locking (advisory only) — risks corrupted execution state from concurrent runs

## R7: Quality Checker as Thin Wrapper

**Decision**: QualityChecker runs exactly 3 checks: build (configurable command), ruff (lint), pytest (test). Feature 010 will replace with full implementation including coverage, mutation testing, and configurable pipelines.

**Rationale**: The sub-agent executor needs *some* quality gate to validate generated code. But Feature 010 is specifically designed for comprehensive quality checking. Building a full quality system here would be duplicated effort. The thin wrapper provides the interface contract that Feature 010 will implement.

**Alternatives considered**:
- No quality checking (defer entirely to Feature 010) — leaves generated code unvalidated; defeats the purpose of the execution loop
- Full quality system now — duplicates Feature 010 scope; violates single-responsibility
- Only build check (no lint/test) — insufficient; lint catches style violations and test catches logic errors

## R8: Execution State Schema Design

**Decision**: Single JSON file per service (`.execution-state.json`) with per-task records, verification state, and schema versioning. Follows the same patterns as `pipeline_state.py`.

**Rationale**: Consistency with existing state management in the codebase. The schema tracks enough information for resume, diagnostics, and verification without being overly complex. Schema versioning (starting at "1.0") allows future evolution.

**Alternatives considered**:
- SQLite database per service — more queryable but overkill; JSON is human-readable for debugging
- Separate file per task — scattered state is harder to reason about and atomically update
- Git-based state (tags/branches) — couples state to git history; doesn't survive branch switches
