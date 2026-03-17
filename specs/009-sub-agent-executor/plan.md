# Implementation Plan: Sub-Agent Execution Engine

**Branch**: `009-sub-agent-executor` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-sub-agent-executor/spec.md`

## Summary

Build the sub-agent execution engine that implements one service at a time by processing its `tasks.md` in dependency order. For each task, the engine assembles an isolated context (constitution + governance prompts + service spec artifacts + dependency contracts), generates an implementation prompt, executes it (Mode A: display for user, Mode B: call agent), runs quality checks (build, lint, test), and commits on success. An auto-fix loop retries failed quality checks up to 3 times. Cross-service infrastructure (`--shared-infra`) is processed before any service. Execution state is persisted per-service for resume capability.

The implementation adds 9 new modules in `src/specforge/core/` and a new `implement` CLI command. The engine integrates with existing infrastructure: `PromptContextBuilder` (Feature 003) for governance context, `ServiceContext` (Feature 005) for manifest data, `PipelineState`/`PipelineLock` patterns for state and locking, and `TaskFile`/`TaskItem` models (Feature 008) for task parsing. Quality checker and auto-fix loop are thin wrappers here — Feature 010 will provide full implementations. Docker operations are microservice-only.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (prompt template rendering), GitPython 3.x (commit operations) — all existing  
**Storage**: File system — `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (read spec artifacts, write execution state), project source tree (write generated code)  
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)  
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)  
**Project Type**: CLI tool extension (new core modules + new CLI command)  
**Performance Goals**: Per-task execution is I/O-bound (agent call + quality checks); context assembly <2s per task  
**Constraints**: Functions ≤30 lines, classes ≤200 lines, frozen dataclasses, Result[T] for errors, constructor injection, type hints everywhere  
**Scale/Scope**: Projects with 1–20 services, up to 50 tasks per service, context budget ~100K tokens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md complete with 6 user stories, 30 FRs, 8 SCs, 10 edge cases. Clarifications resolved. |
| II. Architecture | ✅ PASS | New modules in `core/` (zero external deps for domain logic). Prompt templates via Jinja2. No string concat for output. |
| III. Code Quality | ✅ PASS | All functions ≤30 lines. Frozen dataclasses. Result[T] returns. Constructor injection. |
| IV. Testing | ✅ PASS | TDD: unit tests per module, integration tests for CLI, snapshots for prompt rendering. |
| V. Commit Strategy | ✅ PASS | One conventional commit per task. Engine itself generates conventional commits. |
| VI. File Structure | ✅ PASS | New modules in `src/specforge/core/`. CLI in `src/specforge/cli/`. Tests in `tests/unit/` and `tests/integration/`. |
| VII. Governance | ✅ PASS | No conflicts. Engine reads governance files via PromptContextBuilder (read-only). |

## Project Structure

### Documentation (this feature)

```text
specs/009-sub-agent-executor/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: usage guide
├── contracts/
│   └── implement-cmd.md # CLI contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   └── implement_cmd.py          # specforge implement <service> [--shared-infra] [--resume] [--mode]
├── core/
│   ├── executor_models.py        # ExecutionContext, ExecutionState, TaskExecution, QualityCheckResult, AutoFixAttempt, ServiceLock (frozen dataclasses)
│   ├── execution_state.py        # State persistence: create, load, save, mark_task_complete, mark_task_failed, validate_against_tasks
│   ├── context_builder.py        # ContextBuilder — assembles per-task context with isolation enforcement
│   ├── task_runner.py            # TaskRunner — executes single task (Mode A display, Mode B agent call)
│   ├── quality_checker.py        # QualityChecker — thin wrapper: build + ruff + pytest (Feature 010 replaces)
│   ├── auto_fix_loop.py          # AutoFixLoop — error → fix prompt → retry (Feature 010 replaces)
│   ├── sub_agent_executor.py     # SubAgentExecutor — main orchestrator per service
│   ├── shared_infra_executor.py  # SharedInfraExecutor — cross-service infrastructure tasks
│   ├── contract_resolver.py      # ContractResolver — loads contracts from dependent services
│   ├── docker_manager.py         # DockerManager — container build, health check, compose lifecycle (microservice only)
│   ├── config.py                 # + EXECUTION_STATE_FILENAME, MAX_FIX_ATTEMPTS, CONTEXT_TOKEN_BUDGET, etc.
│   └── templates/base/prompts/
│       └── implement-task.md.j2  # Jinja2 template for implementation prompt generation
│
tests/
├── unit/
│   ├── test_executor_models.py
│   ├── test_execution_state.py
│   ├── test_context_builder.py
│   ├── test_task_runner.py
│   ├── test_quality_checker.py
│   ├── test_auto_fix_loop.py
│   ├── test_sub_agent_executor.py
│   ├── test_shared_infra_executor.py
│   ├── test_contract_resolver.py
│   └── test_docker_manager.py
├── integration/
│   ├── test_implement_cmd.py
│   ├── test_implement_microservice.py
│   ├── test_implement_monolith.py
│   └── test_implement_resume.py
└── snapshots/
    └── test_implement_prompt_rendering.py
```

**Structure Decision**: Single project layout (existing SpecForge structure). All new modules in `src/specforge/core/` with one module per concern. New CLI command `implement` registered in `main.py`. Prompt template in `templates/base/prompts/`.

## Design Decisions

### D1: Execution Data Model

Nine frozen dataclasses model the execution domain:

```
ExecutionMode (Literal["prompt-display", "agent-call"])

ServiceLock (frozen dataclass)
├── service_slug: str             # e.g., "ledger-service"
├── pid: int                      # Process ID of lock holder
├── started_at: str               # ISO 8601 timestamp
├── current_task_id: str          # Task currently being processed
└── hostname: str                 # Machine name for multi-machine detection

TaskExecution (frozen dataclass)
├── task_id: str                  # e.g., "T001"
├── status: str                   # "pending" | "in-progress" | "completed" | "failed" | "skipped"
├── attempt: int                  # Current attempt number (1-based)
├── started_at: str | None        # ISO 8601
├── completed_at: str | None      # ISO 8601
├── commit_sha: str | None        # Git commit SHA on success
├── error_output: str | None      # Last quality check error
└── fix_attempts: tuple[str, ...] # Error outputs from each fix attempt

QualityCheckResult (frozen dataclass)
├── passed: bool
├── build_output: str             # Stdout/stderr from build command
├── lint_output: str              # Stdout/stderr from ruff
├── test_output: str              # Stdout/stderr from pytest
├── failed_checks: tuple[str, ...] # Which checks failed: ("build",) or ("lint", "test")
└── is_regression: bool           # True if new failures not in original error set

AutoFixAttempt (frozen dataclass)
├── attempt_number: int           # 1, 2, or 3
├── error_input: str              # Error output that triggered the fix
├── fix_prompt: str               # Generated fix prompt
├── files_changed: tuple[str, ...]# Files modified by the fix
├── check_result: QualityCheckResult | None  # Result after fix applied
└── reverted: bool                # True if regression detected and reverted

ExecutionState (frozen dataclass)
├── schema_version: str           # "1.0"
├── service_slug: str             # Target service
├── architecture: str             # "monolithic" | "microservice" | "modular-monolith"
├── mode: str                     # "prompt-display" | "agent-call"
├── tasks: tuple[TaskExecution, ...]  # Per-task execution records
├── shared_infra_complete: bool   # True if --shared-infra has been run
├── verification: VerificationState | None  # Post-implementation (microservice only)
├── created_at: str               # ISO 8601
└── updated_at: str               # ISO 8601

VerificationState (frozen dataclass)
├── container_built: bool         # Docker image built successfully
├── health_check_passed: bool     # Health check endpoint responded
├── contract_tests_passed: bool   # Pact consumer tests passed
├── compose_registered: bool      # Service entry in docker-compose updated
└── errors: tuple[str, ...]       # Verification error outputs

ExecutionContext (frozen dataclass)
├── constitution: str             # constitution.md content
├── governance_prompts: str       # PromptContextBuilder.build() output
├── service_spec: str             # spec.md content
├── service_plan: str             # plan.md content
├── service_data_model: str       # data-model.md content
├── service_edge_cases: str       # edge-cases.md content
├── service_tasks: str            # tasks.md content
├── dependency_contracts: dict[str, str]  # slug → contract content
├── architecture_prompts: str     # Extra prompts for microservice (container, grpc, events)
├── current_task: str             # Current task description from tasks.md
└── estimated_tokens: int         # Approximate token count of assembled context

ImplementPrompt (frozen dataclass)
├── system_context: str           # Governance + architecture constraints
├── task_description: str         # What to implement
├── file_hints: tuple[str, ...]   # Target file paths from task
├── dependency_context: str       # Relevant contracts and specs
└── prior_task_commits: tuple[str, ...]  # Recent commit messages for continuity
```

**Immutability**: All dataclasses are frozen. State transitions produce new instances via `dataclasses.replace()`.

### D2: SubAgentExecutor — Main Orchestrator

```
SubAgentExecutor(
    context_builder: ContextBuilder,
    task_runner: TaskRunner,
    quality_checker: QualityChecker,
    auto_fix_loop: AutoFixLoop,
    docker_manager: DockerManager | None,   # None for monolith
    project_root: Path,
)

execute(service_slug: str, mode: ExecutionMode, resume: bool = False) -> Result[ExecutionState, str]
├── Step 1: Load manifest, resolve ServiceContext
├── Step 2: Validate spec artifacts exist (spec.md, plan.md, data-model.md, edge-cases.md, tasks.md)
├── Step 3: Check shared infra prerequisite (microservice/modular-monolith only)
├── Step 4: Acquire ServiceLock (Err if already locked)
├── Step 5: Load or create ExecutionState
│   ├── If resume=True: load existing state, validate against tasks.md
│   ├── If state exists and resume=False: warn + ask resume or fresh
│   └── If no state: create fresh
├── Step 6: Parse tasks.md into ordered TaskItem list (reuse Feature 008 parser)
├── Step 7: For each pending task in dependency order:
│   ├── 7a: Update state → in-progress
│   ├── 7b: Build ExecutionContext via ContextBuilder.build(service_ctx, task)
│   │   └── Context is rebuilt per-task (current_task field varies; token budget re-evaluated)
│   ├── 7c: Generate ImplementPrompt from ExecutionContext
│   ├── 7d: Execute via TaskRunner (Mode A or Mode B)
│   ├── 7e: Run QualityChecker (build + ruff + pytest)
│   ├── 7f: If checks pass: git commit, save state → completed (atomic: commit then state)
│   │   └── Crash recovery: on resume, check git log for task's commit message before re-executing
│   ├── 7g: If checks fail: run AutoFixLoop (max 3 attempts)
│   │   ├── If fix succeeds: commit combined changes, save state → completed
│   │   └── If fix exhausted: save state → failed, halt execution
│   └── 7h: Save state after each task (in-progress saved at 7a, completed/failed saved at 7f/7g)
├── Step 8: If all tasks complete AND microservice: run verification
│   ├── 8a: DockerManager.build_image()
│   ├── 8b: DockerManager.health_check()
│   ├── 8c: DockerManager.run_contract_tests()
│   ├── 8d: DockerManager.register_in_compose()
│   └── 8e: Auto-fix loop for verification failures
├── Step 9: Release ServiceLock
└── Step 10: Return final ExecutionState
```

**Constructor injection**: All dependencies injected via `__init__`. No global state. DockerManager is optional (None for monolith/modular-monolith).

### D3: ContextBuilder — Isolated Context Assembly

```
ContextBuilder(
    project_root: Path,
    prompt_loader: PromptLoader,         # Existing Feature 003
    contract_resolver: ContractResolver,
)

build(service_ctx: ServiceContext, task: TaskItem) -> Result[ExecutionContext, str]
├── Step 1: Load constitution.md from project root
│   └── If missing: warn, use empty string (non-blocking)
├── Step 2: Build governance prompts via PromptContextBuilder.build()
│   └── Pass task_domain hint based on task.layer (e.g., "backend" for service layer)
├── Step 3: Load service spec artifacts from .specforge/features/<slug>/
│   ├── If service maps to multiple features in manifest: load from all feature dirs
│   ├── spec.md (required)
│   ├── plan.md (required)
│   ├── data-model.md (required)
│   ├── edge-cases.md (required)
│   └── tasks.md (required)
├── Step 4: Load dependency contracts via ContractResolver
│   └── Pass service_ctx.dependencies (already resolved from manifest communication field)
├── Step 5: Load architecture-specific prompts (microservice only)
│   └── Container config, inter-service communication, event bus sections
├── Step 6: Assemble current task description from TaskItem
├── Step 7: Estimate token count (chars / 4 approximation)
│   └── If > CONTEXT_TOKEN_BUDGET (100K): warn user with Rich warning, truncate lowest-priority sections
├── Step 8: Return frozen ExecutionContext
```

**Isolation enforcement**: ContextBuilder constructs the file path allowlist from the manifest. It physically cannot read paths outside: (a) constitution.md, (b) `.specforge/prompts/`, (c) `.specforge/features/<target-slug>/`, (d) `.specforge/features/<dependency-slug>/contracts/`. Any path outside this allowlist is rejected.

**Multi-feature services**: When a service maps to multiple features in the manifest (e.g., analytics-service with features ["005", "006"]), ContextBuilder loads spec artifacts from ALL feature directories. Token budget estimation accounts for the combined size. Worst case for a 2-feature service: ~50K tokens for spec artifacts, well within the 100K budget.

**Token budget calculation** (worst-case for 2-feature service):
- Spec artifacts × 2 features: ~50K tokens (2 × 25K per feature at ~100KB raw text each)
- Constitution + governance: ~6K tokens
- Dependency contracts: ~5K tokens (per dependency)
- Architecture prompts: ~2K tokens
- Current task: ~0.5K tokens
- **Total: ~63.5K tokens** — within 100K budget with 36.5K headroom

**Context priority for truncation** (lowest priority truncated first):
1. edge-cases.md (lowest)
2. architecture-specific prompts
3. dependency contracts
4. data-model.md
5. plan.md
6. governance prompts
7. spec.md
8. constitution.md (highest — never truncated)
9. current task (highest — never truncated)

### D4: TaskRunner — Mode A and Mode B

```
TaskRunner(project_root: Path)

run(prompt: ImplementPrompt, mode: ExecutionMode) -> Result[list[Path], str]
├── Mode A (prompt-display):
│   ├── Step 1: Render prompt via Jinja2 template (implement-task.md.j2)
│   ├── Step 2: Display rendered prompt with Rich formatting
│   │   └── Panel with task description, file hints, context summary
│   ├── Step 3: Optionally copy prompt to clipboard (if pyperclip available)
│   ├── Step 4: Wait for user confirmation via Rich.Prompt ("Task complete? [y/n/skip]")
│   │   ├── y: Detect changed files via git status, return changed file paths
│   │   ├── n: Return Err("User indicated task not complete")
│   │   └── skip: Return Ok([]) — mark task as skipped in state
│   └── Step 5: Return Ok(changed_files)
│
├── Mode B (agent-call):
│   ├── Step 1: Render prompt via Jinja2 template
│   ├── Step 2: Detect configured agent (reuse agent_detector.py)
│   ├── Step 3: Send prompt to agent via subprocess
│   │   └── Capture stdout/stderr for diagnostics
│   ├── Step 4: If agent unreachable: retry 3 times, then fall back to Mode A
│   ├── Step 5: Detect changed files via git status
│   └── Step 6: Return Ok(changed_files)
```

**Agent fallback**: Mode B wraps agent invocation in a retry with exponential backoff (1s, 2s, 4s). After 3 failures, automatically switches to Mode A for the current task and logs a warning.

### D5: QualityChecker — Thin Wrapper (Feature 010 Placeholder)

```
QualityChecker(project_root: Path, service_slug: str)

check(changed_files: list[Path]) -> Result[QualityCheckResult, str]
├── Step 1: Run build command (from manifest or convention-based detection)
│   └── Default: no-op if no build command configured
├── Step 2: Run ruff check on changed .py files
│   └── Command: ruff check <changed_files> --no-fix
├── Step 3: Run pytest for service test directory
│   └── Command: pytest tests/<service_slug>/ -x --tb=short
├── Step 4: Aggregate results into QualityCheckResult
│   └── passed = all three checks pass
└── Step 5: Return Result

detect_regression(before: QualityCheckResult, after: QualityCheckResult) -> bool
├── Step 1: Parse test names from before.test_output (failed set A)
├── Step 2: Parse test names from after.test_output (failed set B)
├── Step 3: Return True if B has tests not in A (new failures)
└── Step 4: Return False if B ⊆ A (same or fewer failures)
```

**Feature 010 integration**: QualityChecker is intentionally minimal. It provides the `check()` and `detect_regression()` interface. Feature 010 (Quality Gate) will replace the internals with configurable check pipelines, coverage thresholds, and mutation testing. The interface contract (`check() → QualityCheckResult`, `detect_regression() → bool`) is stable — Feature 010 extends the implementation, not the signatures.

**Shared infrastructure quality**: When running in `--shared-infra` context, QualityChecker also validates generated docker-compose.yml via `docker-compose config` (syntax + schema validation). This is a no-op if docker-compose is not installed.

### D6: AutoFixLoop — Retry with Regression Detection

```
AutoFixLoop(
    task_runner: TaskRunner,
    quality_checker: QualityChecker,
    max_attempts: int = 3,              # Configurable via config.py
)

fix(
    original_task: ImplementPrompt,
    error: QualityCheckResult,
    changed_files: list[Path],
    mode: ExecutionMode,
) -> Result[tuple[list[Path], QualityCheckResult], str]
├── Step 1: For attempt in range(max_attempts):
│   ├── 1a: Generate fix prompt from error output + original task context + changed files
│   ├── 1b: Execute fix via TaskRunner (same mode as original task)
│   ├── 1c: Run QualityChecker on all changed files
│   ├── 1d: If passed: return Ok((all_changed_files, check_result))
│   ├── 1e: If regression detected: revert fix via git checkout, count as failed attempt
│   └── 1f: If failed (not regression): continue to next attempt with updated error
├── Step 2: All attempts exhausted: return Err with diagnostic summary
│   └── Include: original error, each attempt's error, files involved
└── Step 3: Caller (SubAgentExecutor) saves state and halts
```

**Revert strategy**: When regression is detected, the loop runs `git checkout -- <fix_changed_files>` to revert only the fix changes. The original task changes are preserved. This is safer than reverting all changes.

### D7: SharedInfraExecutor — Cross-Service Infrastructure

```
SharedInfraExecutor(
    context_builder: ContextBuilder,
    task_runner: TaskRunner,
    quality_checker: QualityChecker,
    auto_fix_loop: AutoFixLoop,
    project_root: Path,
)

execute(mode: ExecutionMode) -> Result[ExecutionState, str]
├── Step 1: Load manifest, validate architecture is microservice or modular-monolith
│   └── If monolithic: return Err("Shared infrastructure not applicable for monolithic")
├── Step 2: Locate cross-service-infra/tasks.md (from Feature 008)
│   └── If missing: return Err("Run task generation first")
├── Step 3: Build project-wide context (all services' specs, full manifest)
├── Step 4: Process tasks using same loop as SubAgentExecutor (steps 8a-8g)
│   └── Commits land on current working branch (no separate branch)
├── Step 5: Mark shared_infra_complete in execution state
└── Step 6: Return ExecutionState
```

**Context scope**: Unlike per-service execution, shared infra gets project-wide context (all service specs, full manifest, communication map). This is necessary because shared contracts, gateway routes, and compose configuration reference all services.

### D8: ContractResolver — Dependency Contract Loading

```
ContractResolver(project_root: Path)

resolve(dependencies: tuple[ServiceDependency, ...]) -> Result[dict[str, str], str]
├── Step 1: Iterate over provided ServiceDependency objects
│   └── Dependencies pre-resolved by ServiceContext from manifest "communication" field
├── Step 2: For each dependency:
│   ├── Look for .specforge/features/<dep.target_slug>/contracts/ directory
│   ├── Read all files in contracts/ (api-spec.json, event-schemas, etc.)
│   └── Concatenate into a single string keyed by dep.target_slug
├── Step 3: Return dict mapping dep-slug → contract content
└── Fallback: If contracts/ directory missing for a dep, warn and skip (non-blocking)
```

**Non-blocking design**: Missing contracts produce a warning, not an error. The service can still be implemented — it just won't have dependency contract context. This handles the case where a dependency hasn't gone through the pipeline yet.

**Dependency source**: Uses `ServiceContext.dependencies` (resolved from manifest `communication` field by Feature 005's ServiceContextResolver). Does NOT re-parse raw manifest — this prevents drift between dependency resolution logic and the existing ServiceContext pipeline. Only loads contracts for services listed in the target's communication links, never all services.

### D9: DockerManager — Container Operations (Microservice Only)

```
DockerManager(project_root: Path, service_slug: str)

build_image() -> Result[str, str]
├── Step 1: Locate Dockerfile in service directory (convention: src/<slug>/Dockerfile)
├── Step 2: Run docker build -t <slug>:latest -f <Dockerfile> .
├── Step 3: Capture stdout/stderr
├── Step 4: Return Ok(image_tag) or Err(build_error)

health_check(timeout_seconds: int = 30) -> Result[bool, str]
├── Step 1: Run container: docker run -d --name <slug>-healthcheck <slug>:latest
├── Step 2: Poll health endpoint (convention: GET /health) with retries
├── Step 3: Stop and remove container
└── Step 4: Return Ok(True) or Err(health_error)

run_contract_tests() -> Result[QualityCheckResult, str]
├── Step 1: Locate Pact consumer test directory (tests/<slug>/contract/)
├── Step 2: Run pytest tests/<slug>/contract/ with Pact provider stubs
├── Step 3: Return QualityCheckResult

compose_up_test_profile() -> Result[bool, str]
├── Step 1: Run docker-compose --profile test up -d
├── Step 2: Wait for services to be healthy
├── Step 3: Return Ok(True) or Err(compose_error)

compose_down_test_profile() -> Result[bool, str]
├── Step 1: Run docker-compose --profile test down
└── Step 2: Return Ok(True)

register_in_compose(compose_path: Path) -> Result[bool, str]
├── Step 1: Read existing docker-compose.yml
├── Step 2: Add/update service entry for this service
├── Step 3: Write back atomically (temp + os.replace)
└── Step 4: Return Ok(True)
```

**Convention-based paths**: DockerManager uses conventions from the manifest and build sequence to locate Dockerfiles, test directories, and compose files. No configuration required — paths are derived from the same patterns used by Feature 008.

### D10: ExecutionState Persistence

Follows the established pattern from `pipeline_state.py`:

```
State file: .specforge/features/<slug>/.execution-state.json
Lock file:  .specforge/features/<slug>/.execution-lock

Functions (all pure — take state, return new state):

create_initial_state(service_slug: str, architecture: str, mode: str, task_ids: tuple[str, ...]) -> ExecutionState
mark_task_in_progress(state: ExecutionState, task_id: str) -> ExecutionState
mark_task_completed(state: ExecutionState, task_id: str, commit_sha: str) -> ExecutionState
mark_task_failed(state: ExecutionState, task_id: str, error: str, fix_attempts: tuple[str, ...]) -> ExecutionState
get_next_pending_task(state: ExecutionState) -> str | None
validate_against_tasks(state: ExecutionState, current_task_ids: tuple[str, ...]) -> ExecutionState
  └── Removes orphaned task IDs, adds new ones as pending
save_state(path: Path, state: ExecutionState) -> Result[None, str]
  └── Atomic write: temp file + os.replace()
load_state(path: Path) -> Result[ExecutionState | None, str]
  └── Returns Ok(None) if file doesn't exist
```

**Atomic write**: Same strategy as `pipeline_state.py` — write to temp file, fsync, os.replace. Ensures state is never corrupted by interruption.

**Crash-window mitigation**: There is a window between git commit (step 7f) and state save where a crash would leave the task committed but state still showing "in-progress". On resume, the engine calls `detect_committed_task(state, task_id, repo)` which checks `git log --oneline --grep="<task_id>"` for the task's conventional commit message. If found, the task is marked completed with the commit SHA from git log, avoiding duplicate execution. This adds a new pure function:

```
detect_committed_task(task_id: str, service_slug: str, repo_path: Path) -> str | None
├── Step 1: Run git log --oneline --grep="task_id" in repo
├── Step 2: If matching commit found: return commit SHA
└── Step 3: If no match: return None (task needs re-execution)
```

### D11: implement CLI Command

```
@click.command()
@click.argument("target", required=False, default=None)
@click.option("--shared-infra", is_flag=True, help="Build cross-service infrastructure first")
@click.option("--resume", is_flag=True, help="Resume from last completed task")
@click.option("--mode", type=click.Choice(["prompt-display", "agent-call"]), default="prompt-display")
@click.option("--max-fix-attempts", type=int, default=3, help="Max auto-fix retry attempts")
@click.pass_context
def implement(ctx, target, shared_infra, resume, mode, max_fix_attempts):
    """Implement a service or module by executing its tasks.md."""
    
    # Validation:
    # - target XOR --shared-infra (exactly one required)
    # - If target: resolve to service slug via manifest
    # - If --shared-infra: validate architecture is not monolithic
    # - If --resume: require target (not --shared-infra)
```

**Registration** in `main.py`:
```python
from specforge.cli.implement_cmd import implement
cli.add_command(implement)
```

### D12: Prompt Template (implement-task.md.j2)

```
# Implementation Task: {{ task.id }}

## Task Description
{{ task.description }}

## File Targets
{% for path in task.file_paths %}
- {{ path }}
{% endfor %}

## Quality Standards (Governance)
{{ governance_prompts }}

## Service Context
{{ service_spec_summary }}

## Data Model
{{ data_model_summary }}

## Dependency Contracts
{% for dep, contract in dependency_contracts.items() %}
### {{ dep }}
{{ contract }}
{% endfor %}

## Prior Tasks Completed
{% for msg in prior_commits %}
- {{ msg }}
{% endfor %}

## Constraints
- Follow conventional commit format for any files you create
- Stay within the scope of this service only
- Reference dependency contracts for inter-service communication
{{ architecture_constraints }}
```

**One prompt per task**: Each task generates exactly one prompt (clarification Q1). No batching by layer.

### D13: Config Constants

New constants added to `config.py`:

```python
# Sub-Agent Executor (Feature 009)
EXECUTION_STATE_FILENAME: str = ".execution-state.json"
EXECUTION_LOCK_FILENAME: str = ".execution-lock"
EXECUTION_LOCK_STALE_MINUTES: int = 60

MAX_FIX_ATTEMPTS: int = 3
CONTEXT_TOKEN_BUDGET: int = 100_000
CHARS_PER_TOKEN_ESTIMATE: int = 4

AGENT_RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)  # seconds
HEALTH_CHECK_TIMEOUT: int = 30
HEALTH_CHECK_ENDPOINT: str = "/health"

DOCKER_COMPOSE_TEST_PROFILE: str = "test"

IMPLEMENTATION_MODES: tuple[str, ...] = ("prompt-display", "agent-call")

# Context priority order (lowest priority first — truncated first when over budget)
CONTEXT_PRIORITY: tuple[str, ...] = (
    "edge_cases",
    "architecture_prompts",
    "dependency_contracts",
    "data_model",
    "plan",
    "governance_prompts",
    "spec",
    "constitution",
    "current_task",
)
```

## Complexity Tracking

> No constitution violations. Table intentionally empty.
