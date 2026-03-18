# Feature 011: Implementation Orchestrator — Technical Context Summary

## OVERVIEW
Feature 011 implements a multi-service orchestrator that coordinates implementation of generated task.md files across services. It follows patterns established by PipelineOrchestrator (Feature 005) but for execution rather than specification generation.

## 1. SPEC PIPELINE ORCHESTRATOR (PipelineOrchestrator - spec_pipeline.py)
**Class**: PipelineOrchestrator (lines 47-139)
**Constructor**:
  - renderer: TemplateRenderer
  - registry: TemplateRegistry
  - prompt_context: str (default "")

**Main Methods**:
1. run(target, project_root, force=False, from_phase=None) → Result
   - Resolves target to service slug
   - Loads ServiceContext
   - Executes _execute() with lock safety

2. _execute(service_ctx, force, from_phase) → Result
   - Acquires lock at: service_ctx.output_dir/.pipeline-lock
   - Uses O_CREAT|O_EXCL for atomic cross-platform lock
   - Lock JSON contains: {service_slug, pid, timestamp}
   - Calls _run_phases() in try/finally for safety
   - Releases lock in finally block
   - Stale lock detection: 30 minute threshold (config.LOCK_STALE_THRESHOLD_MINUTES)

3. _run_phases(service_ctx, force, from_phase) → Result
   - Loads/creates state from .pipeline-state.json
   - detect_interrupted() resets in-progress phases to pending
   - Loops 7 phases: spec → research → datamodel ∥ edgecase → plan → checklist → tasks
   - Marks each phase: in-progress → save state → run phase → complete/failed → save state
   - Special: datamodel+edgecase run in parallel (ThreadPoolExecutor, 2 workers)
   - Final steps: generate api-spec.json, generate stub contracts (microservice only)
   - Returns Ok(output_dir) on success

**State Model**:
  Location: pipeline_state.py
  - PipelineState: service_slug, schema_version, phases: tuple[PhaseStatus], created_at, updated_at
  - PhaseStatus: name, status (pending|in-progress|complete|failed), started_at, completed_at, artifact_paths, error
  - All state transitions return new state (immutable)
  - State saved atomically: tempfile + fsync + os.replace()

**Pattern**: 
  - No concurrent execution (lock-based)
  - Resume support: --from-phase to restart from specific phase
  - Parallel capability: 2 independent phases can run concurrently
  - Artifact accumulation: phases pass artifacts dict to downstream phases

---

## 2. SUB-AGENT EXECUTOR (sub_agent_executor.py - lines 45-410)

**Class**: SubAgentExecutor
**Constructor**:
  - context_builder: ContextBuilder
  - task_runner: TaskRunner
  - quality_checker_factory: callable
  - auto_fix_loop: AutoFixLoop | None
  - docker_manager: DockerManager | None (for microservice verification)
  - project_root: Path

**Main Method**: execute(service_slug, mode, resume=False) → Result[ExecutionState, str]

**Flow**:
1. Load manifest from .specforge/manifest.json
2. Resolve service from manifest
3. Validate tasks.md exists
4. Acquire execution lock at: .specforge/features/{service_slug}/.execution-lock
5. Load or create ExecutionState
6. Task loop (while get_next_pending_task()):
   a. Mark task in-progress → save state
   b. ContextBuilder.build(service_ctx, task) → ExecutionContext
   c. Build ImplementPrompt from context
   d. TaskRunner.run(prompt, mode) → list[Path] (changed files)
   e. If empty: mark skipped → save state
   f. Else: QualityChecker.check(changed_files)
   g. If passed: git commit → mark completed → save state
   h. Else if auto_fix: auto_fix_loop.fix() → if passed: git commit → mark completed
   i. Else: git commit anyway (permissive) → mark completed
7. For microservices (arch=="microservice"):
   a. Docker build check
   b. Health check endpoint
   c. Contract tests
   d. Docker-compose registration
   e. Store results in VerificationState
8. Release lock
9. Return ExecutionState

**ExecutionState Model**:
`python
@dataclass(frozen=True)
class ExecutionState:
    service_slug: str
    architecture: str
    mode: str  # "prompt-display" or "agent-call"
    schema_version: str = "1.0"
    tasks: tuple[TaskExecution, ...] = ()
    shared_infra_complete: bool = False
    verification: VerificationState | None = None
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
`

**TaskExecution**:
`python
@dataclass(frozen=True)
class TaskExecution:
    task_id: str
    status: str = "pending"  # pending|in-progress|completed|skipped|failed
    attempt: int = 1
    started_at: str | None = None
    completed_at: str | None = None
    commit_sha: str | None = None  # From 'git rev-parse --short HEAD'
    error_output: str | None = None
    fix_attempts: tuple[str, ...] = ()
`

**Resume Behavior**:
- If resume=True: load_state() → validate_against_tasks(current_task_ids)
- Syncs state: removes orphaned tasks, adds new tasks from tasks.md
- Resets in-progress tasks to pending (restart from scratch)
- Uses regex: ^- \[[ Xx]\]\s+(T\d+)\s+(.+)$ to parse tasks.md

**Git Commit**:
- Command: git add -A && git commit -m "feat({service_slug}): {desc} [{task_id}]"
- Stores short SHA in execution state
- Allow-empty commits permitted

---

## 3. SHARED INFRA EXECUTOR (shared_infra_executor.py - lines 46-268)

**Class**: SharedInfraExecutor
**Constructor**: (same as SubAgentExecutor but NO docker_manager)

**Main Method**: execute(mode) → Result[ExecutionState, str]

**Differences from SubAgentExecutor**:
1. Validates architecture: only microservice|modular-monolith (monolithic returns error)
2. No resume support
3. No docker_manager (no post-execution verification)
4. Slug hardcoded: _INFRA_SLUG = "cross-service-infra"
5. Creates synthetic ServiceContext with empty features/dependencies
6. Task loop identical to SubAgentExecutor
7. At end: state = replace(state, shared_infra_complete=True)
8. Skipped for monolithic architecture

---

## 4. EXECUTION STATE PERSISTENCE (execution_state.py)

**State Functions** (all pure, return new state):
1. create_initial_state(service_slug, architecture, mode, task_ids) → ExecutionState
2. mark_task_in_progress(state, task_id) → ExecutionState
3. mark_task_completed(state, task_id, commit_sha) → ExecutionState
4. mark_task_failed(state, task_id, error, fix_attempts) → ExecutionState
5. get_next_pending_task(state) → str | None
6. validate_against_tasks(state, current_task_ids) → ExecutionState

**Persistence**:
- save_state(path, state) → Result
  - Atomic write: mkstemp → write → fsync → os.close → Path.replace()
  - Safe on power loss or interrupt
- load_state(path) → Result[ExecutionState | None, str]
  - Returns Ok(None) if missing
  - JSON deserialization with full validation

---

## 5. QUALITY GATE ORCHESTRATION (quality_gate.py + quality_checker.py)

**QualityGate** (architecture-aware orchestrator):
Constructor:
  - architecture: str  (microservice|modular-monolith|monolithic)
  - project_root: Path
  - service_slug: str
  - checkers: tuple[CheckerProtocol, ...]
  - prompt_loader: PromptLoader | None

**Main Methods**:
1. run_task_checks(changed_files, service_context) → Result[QualityGateResult, str]
   - Filters checkers by: is_applicable(architecture) AND level==TASK
   - Runs all applicable checkers
   - Aggregates via _aggregate_results()

2. run_service_checks(service_context) → Result[QualityGateResult, str]
   - Same but level==SERVICE, empty changed_files

3. run_selective_checks(failed_checkers, changed_files, service_context) → Result[QualityGateResult, str]

**QualityCheckResult** (backward-compat from Feature 009):
  - passed: bool
  - build_output, lint_output, test_output: str
  - failed_checks: tuple[str, ...] ⊆ {"build", "lint", "test"}

**QualityGateResult** (new in Feature 010):
  - passed: bool
  - check_results: tuple[CheckResult, ...]
  - failed_checks: tuple[str, ...] (checker names)
  - skipped_checks: tuple[str, ...]
  - architecture: str
  - level: CheckLevel (TASK|SERVICE)

**15 Checkers**:
BuildChecker, LintChecker, TestChecker, CoverageChecker, LineLimitChecker,
SecretChecker, TodoChecker, PromptRuleChecker, DockerBuildChecker,
DockerServiceChecker, ContractChecker, UrlChecker, InterfaceChecker,
BoundaryChecker, MigrationChecker

---

## 6. ARCHITECTURE ADAPTER (architecture_adapter.py)

**ArchitectureAdapter Protocol**:
`python
def get_context(ctx: ServiceContext) -> dict[str, Any]
def get_datamodel_context(ctx: ServiceContext) -> dict[str, Any]
def get_research_extras() -> list[dict[str, str]]
def get_plan_sections() -> list[dict[str, str]]
def get_task_extras() -> list[dict[str, str]]
def get_edge_case_extras() -> list[dict[str, str]]
def get_checklist_extras() -> list[dict[str, str]]
`

**Three Implementations**:

**MicroserviceAdapter**:
- get_context: {dependencies, communication_patterns, events}
- get_datamodel_context: {entity_scope: "isolated", cross_service_ref: "api_contract"}
- get_research_extras: 3 topics (service mesh, API versioning, distributed tracing)
- get_plan_sections: 5 sections (Containerization, Health Checks, Service Registration, Circuit Breakers, API Gateway)
- get_task_extras: 3 tasks (Container build, Service registration, Contract tests)
- get_edge_case_extras: 4 cases (Service Down, Network Partition, Eventual Consistency, Timeout Handling)
- get_checklist_extras: 2 items (API contract, deployment + health checks)

**MonolithAdapter**:
- get_context: {module_context, shared_infrastructure}
- get_datamodel_context: {entity_scope: "module", cross_service_ref: "shared_table", shared_entities: true}
- get_research_extras: 2 topics (contention analysis, dependency analysis)
- get_plan_sections: 2 sections (Shared Database, Shared Auth Middleware)
- get_task_extras: 1 task (Module integration)
- get_edge_case_extras: 2 cases (Module Boundary Violation, Resource Contention)
- get_checklist_extras: 1 item (Module isolation verified)

**ModularMonolithAdapter** (extends MonolithAdapter):
- Adds strict_boundaries to context
- Adds no_cross_module_db to datamodel
- Additional research topics: boundary enforcement, interface versioning
- Additional plan section, task, edge case, checklist items

**Factory**: create_adapter(architecture: str) → ArchitectureAdapter

---

## 7. PIPELINE STATE & LOCK (pipeline_state.py + pipeline_lock.py)

**PipelineState**:
- 7 phases: spec, research, datamodel, edgecase, plan, checklist, tasks
- Each phase has: name, status, started_at, completed_at, artifact_paths, error
- Persisted to .pipeline-state.json (atomic writes)

**PipelineLock**:
- Atomic via os.open(O_CREAT|O_EXCL|O_WRONLY)
- Stores JSON: {service_slug, pid, timestamp}
- Stale detection: 30 minutes
- Safe to --force override if stale

---

## 8. CONFIG CONSTANTS (config.py - Selected)

**Paths**:
- MANIFEST_PATH = ".specforge/manifest.json"
- FEATURES_DIR = ".specforge/features"
- EXECUTION_STATE_FILENAME = ".execution-state.json"
- EXECUTION_LOCK_FILENAME = ".execution-lock"
- PIPELINE_STATE_FILENAME = ".pipeline-state.json"
- PIPELINE_LOCK_FILENAME = ".pipeline-lock"

**Execution**:
- IMPLEMENTATION_MODES = ("prompt-display", "agent-call")
- MAX_FIX_ATTEMPTS = 3
- EXECUTION_LOCK_STALE_MINUTES = 60
- LOCK_STALE_THRESHOLD_MINUTES = 30
- CONTEXT_TOKEN_BUDGET = 100_000
- CHARS_PER_TOKEN_ESTIMATE = 4

**Pipeline Phases**:
- PIPELINE_PHASES = ["spec", "research", "datamodel", "edgecase", "plan", "checklist", "tasks"]

**Context Priority** (for truncation):
1. edge_cases (lowest priority - truncate first)
2. architecture_prompts
3. dependency_contracts
4. data_model
5. plan
6. governance_prompts
7. spec
8. constitution
9. current_task (highest priority - truncate last/never)

---

## 9. RESULT TYPE (result.py)

**Result[T, E]** = Ok[T] | Err[E]

**Ok[T]**:
- .ok → True
- .value → T
- .map(fn) → Ok[U]
- .bind(fn) → Result

**Err[E]**:
- .ok → False
- .error → E
- .map(fn) → Err (no-op)
- .bind(fn) → Err (no-op)

---

## 10. CLI IMPLEMENT COMMAND (implement_cmd.py:16-137)

**Command**:
`
specforge implement [OPTIONS] [TARGET]
`

**Options**:
- --shared-infra: Execute SharedInfraExecutor instead of SubAgentExecutor
- --resume: Resume from last completed task (SubAgentExecutor only)
- --mode: prompt-display|agent-call (default: prompt-display)
- --max-fix-attempts: INT (default: 3)

**Arguments**:
- TARGET: service slug (mutually exclusive with --shared-infra)

**Validation**:
1. target XOR --shared-infra (not both, not neither)
2. --resume requires target

**Execution**:
- Creates: ContractResolver, ContextBuilder, TaskRunner
- If --shared-infra: SharedInfraExecutor.execute(mode)
- Else: SubAgentExecutor.execute(target, mode, resume=resume)
- Prints Rich table summary with completed/failed/skipped/total counts
- Exit 0 on success, 1 on failure

---

## 11. CONTEXT ASSEMBLY (context_builder.py)

**ContextBuilder.build(service_ctx, task)** → Result[ExecutionContext, str]

**ExecutionContext**:
`python
@dataclass(frozen=True)
class ExecutionContext:
    constitution: str
    governance_prompts: str
    service_spec: str
    service_plan: str
    service_data_model: str
    service_edge_cases: str
    service_tasks: str
    current_task: str  # "[T1] Task description"
    dependency_contracts: dict[str, str] = {}  # {service_slug: api_spec_json}
    architecture_prompts: str = ""  # Microservice constraints
    estimated_tokens: int = 0
`

**Sources**:
- constitution: root/constitution.md (warns if missing)
- governance: PromptLoader per feature/stack/domain
- Artifacts: .specforge/features/{service_slug}/{spec,plan,data-model,edge-cases,tasks}.md
- Contracts: From ContractResolver (api-spec.json files)
- Architecture: _MICROSERVICE_PROMPTS hardcoded string

**Token Budget**:
- Budget: 100,000 tokens
- Estimate: chars / 4
- Truncation priority: edge_cases → current_task (preserve current_task always)

---

## 12. TASK EXECUTION (task_runner.py)

**TaskRunner.run(prompt, mode)** → Result[list[Path], str]

**Mode A (prompt-display)**:
1. Display prompt via Rich
2. Stdin: "y" (proceed), "skip" (empty list), other (error)
3. Detect changed files: git status --porcelain
4. Return list[Path]

**Mode B (agent-call)**:
1. Detect agent: claude, copilot, gemini, cursor, windsurf, codex
2. Subprocess: agent --prompt - (input=full_prompt)
3. Retry logic: 3 attempts with exponential backoff (1, 2, 4 sec)
4. Fallback to Mode A if all attempts fail
5. Detect changed files
6. Return list[Path]

---

## 13. MANIFEST STRUCTURE

**Schema** (.specforge/manifest.json):
`json
{
  "schema_version": "1.0",
  "architecture": "microservice|modular-monolith|monolithic",
  "project_description": "...",
  "domain": "...",
  "features": [
    {
      "id": "001",
      "name": "auth",
      "display_name": "Authentication",
      "description": "...",
      "priority": "P0-P3",
      "category": "foundation|core|supporting|integration|admin"
    }
  ],
  "services": [
    {
      "name": "Identity Service",
      "slug": "identity-service",
      "features": ["001"],
      "rationale": "...",
      "communication": [
        {
          "target": "ledger-service",
          "pattern": "sync-rest|sync-grpc|async-event",
          "required": true,
          "description": "..."
        }
      ]
    }
  ],
  "events": [
    {
      "name": "txn.created",
      "producer": "ledger-service",
      "consumers": ["identity-service"],
      "payload_summary": "..."
    }
  ]
}
`

---

## 14. KEY ARCHITECTURAL PATTERNS

**1. Atomic Operations**:
- Lock: os.open(O_CREAT|O_EXCL|O_WRONLY)
- State: tempfile + fsync + os.replace()
- Safe on power loss/crash

**2. Immutable State Transitions**:
- All *_state functions return new state
- Enabled easy resume/recovery
- Functional composition

**3. Architecture Adaptation**:
- Behavior differs by architecture (via ArchitectureAdapter)
- Task quality checks vary
- Edge case analysis differs

**4. Token Budget**:
- Strict context size limit
- Truncation respects priority order
- Always preserve current_task

**5. Quality-Driven Loop**:
- Task runs → quality checks → pass/fail
- If fail: auto-fix (up to 3 attempts)
- If exhausted: mark failed (permissive)
- Git commit regardless

**6. Manifest-Driven**:
- All service context from .specforge/manifest.json
- Generated by decompose command
- Services/features/dependencies explicit

**7. Conventional Commits**:
- Format: feat({service_slug}): {description} [{task_id}]
- Short SHA stored in ExecutionState
- Each task traceable to commit

---

## 15. DATA FLOW DIAGRAM

`
Spec Pipeline (Feature 005)
  ↓ (generates)
.specforge/features/{service_slug}/*.md
  ├─ spec.md
  ├─ research.md
  ├─ data-model.md
  ├─ edge-cases.md
  ├─ plan.md
  ├─ checklist.md
  ├─ tasks.md
  └─ contracts/
      ├─ api-spec.json
      └─ api-spec.stub.json (for dependencies)

CLI: specforge implement [--shared-infra] [target] [--resume] [--mode]
  ↓
SubAgentExecutor | SharedInfraExecutor
  ├─ Load manifest
  ├─ Resolve service context
  ├─ Load/create ExecutionState
  │
  └─ For each pending task in tasks.md:
      ├─ ContextBuilder.build() → ExecutionContext
      ├─ TaskRunner.run() → list[Path] (changed files)
      ├─ QualityGate.run_task_checks() → QualityGateResult
      ├─ If fail + auto_fix: auto_fix_loop.fix()
      ├─ git commit
      ├─ mark_task_completed()
      └─ save_state()
  │
  └─ [Microservice only]
      ├─ Docker build
      ├─ Health check
      ├─ Contract tests
      ├─ Docker-compose register
      └─ Store in VerificationState

ExecutionState persisted to:
.specforge/features/{service_slug}/.execution-state.json
`

---

## 16. CRITICAL SIMILARITIES TO PIPELINE ORCHESTRATOR

1. **Lock Acquisition**: Both use atomic O_CREAT|O_EXCL locks
2. **State Persistence**: Both use tempfile + fsync + os.replace()
3. **Resume Support**: Both detect interrupted (in-progress → pending)
4. **Architecture Awareness**: Both use ArchitectureAdapter
5. **Phase/Task Loop**: Both mark in-progress → save → run → mark complete → save
6. **Try/Finally Safety**: Both ensure lock release on error
7. **Atomic Commits**: Both use conventional git commits

---

## 17. TEST PATTERNS

Tests in tests/integration/:
- test_pipeline_microservice.py: E2E spec + implementation
- test_pipeline_modular_monolith.py: Modular variant
- test_pipeline_monolith.py: Monolithic variant
- test_pipeline_resume.py: Lock/state recovery
- test_quality_integration.py: Quality gate scenarios

Pattern:
1. Write manifest to tmp_path
2. Invoke CLI (CliRunner)
3. Assert artifacts exist
4. Assert state persisted
5. Assert exit code

---

## 18. FEATURE 011 IMPLEMENTATION REQUIREMENTS

**Must Implement**:
1. ImplementationOrchestrator class (or reuse SubAgentExecutor pattern)
2. Coordinate multi-service implementation sequentially
3. Handle shared infra first (if enabled)
4. Manage locks per service (prevent concurrent execution)
5. Persist execution progress (resume support)
6. Quality gates after each task
7. Architecture-aware behavior (via ArchitectureAdapter)
8. Token budget management
9. Conventional git commits with task IDs
10. Post-execution verification (microservice only)

**Follow Pattern From**:
- PipelineOrchestrator: lock/state/resume
- SubAgentExecutor: task loop/quality/auto-fix
- SharedInfraExecutor: cross-service coordination
- ArchitectureAdapter: behavior variation

