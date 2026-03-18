# Feature 011 Architecture Diagram

## CLASS HIERARCHY & DEPENDENCIES

┌─────────────────────────────────────────────────────────────────────┐
│                         CLI LAYER                                   │
│ specforge implement [TARGET] [--shared-infra] [--resume] [--mode]  │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ├─────────────────────────────────────────────────────────┐
             │                                                         │
             ▼                                                         ▼
┌──────────────────────────┐                    ┌──────────────────────────┐
│  SubAgentExecutor        │                    │  SharedInfraExecutor     │
│  (per-service impl)      │                    │  (cross-service)         │
│                          │                    │                          │
│  .execute(service_slug,  │                    │  .execute(mode)          │
│            mode,         │                    │                          │
│            resume=False) │                    │  Validates: microservice │
│                          │                    │  OR modular-monolith     │
│  Returns:                │                    │  (skips monolithic)      │
│  Result[ExecutionState]  │                    │                          │
└────────────┬─────────────┘                    └────────────┬─────────────┘
             │                                               │
             │ ├─────────────────────────────────────────────┘
             │ │
             ▼ ▼
   ┌────────────────────────┐
   │  CORE TASK LOOP        │
   │  (identical in both)   │
   │                        │
   │ 1. Load ExecutionState │
   │ 2. For each task:      │
   │    a. ContextBuilder   │
   │    b. TaskRunner       │
   │    c. QualityGate      │
   │    d. AutoFixLoop      │
   │    e. Git commit       │
   │    f. Save state       │
   │ 3. [Microservice]      │
   │    Docker verify       │
   └────┬───────────────────┘
        │
        ├────────────────────────────────────────────────────────┐
        │                                                        │
        ▼                                                        ▼
┌──────────────────────┐                         ┌──────────────────────┐
│  ContextBuilder      │                         │  TaskRunner          │
│  .build(ctx, task)   │                         │  .run(prompt, mode)  │
│                      │                         │                      │
│  → ExecutionContext  │                         │  Mode A: display     │
│    - constitution    │                         │  Mode B: agent call  │
│    - governance      │                         │                      │
│    - artifacts       │                         │  → list[Path]        │
│    - contracts       │                         └──────────────────────┘
│    - architecture    │
└──────────┬───────────┘                         
           │                                     
           │  Load from:                        
           │  .specforge/features/{slug}/*.md   
           │  contracts/api-spec*.json          
           │
           ▼
┌──────────────────────────────────────┐
│  QualityGate                         │
│  (Architecture-Aware)                │
│                                      │
│  .run_task_checks(files, ctx)        │
│  → QualityGateResult                 │
│                                      │
│  15 Checkers:                        │
│  - BuildChecker                      │
│  - LintChecker                       │
│  - TestChecker                       │
│  - CoverageChecker                   │
│  - LineLimitChecker                  │
│  - SecretChecker                     │
│  - TodoChecker                       │
│  - PromptRuleChecker                 │
│  - DockerBuildChecker                │
│  - DockerServiceChecker              │
│  - ContractChecker                   │
│  - UrlChecker                        │
│  - InterfaceChecker                  │
│  - BoundaryChecker                   │
│  - MigrationChecker                  │
└──────────┬───────────────────────────┘
           │
           │ If failed:
           ▼
┌──────────────────────┐
│  AutoFixLoop         │
│  .fix(prompt, qc,    │
│       files, mode)   │
│                      │
│  Max 3 attempts      │
│  Revert on failure   │
│  Escalate or mark    │
│  failed              │
└──────────────────────┘

## STATE MANAGEMENT

ExecutionState (JSON persisted):
├─ service_slug: str
├─ architecture: str
├─ mode: str (prompt-display | agent-call)
├─ tasks: tuple[TaskExecution]
│  └─ TaskExecution:
│     ├─ task_id: str
│     ├─ status: str (pending|in-progress|completed|skipped|failed)
│     ├─ attempt: int
│     ├─ started_at: str | None (ISO 8601)
│     ├─ completed_at: str | None
│     ├─ commit_sha: str | None
│     ├─ error_output: str | None
│     └─ fix_attempts: tuple[str, ...]
├─ shared_infra_complete: bool
├─ verification: VerificationState | None
│  └─ VerificationState:
│     ├─ container_built: bool
│     ├─ health_check_passed: bool
│     ├─ contract_tests_passed: bool
│     ├─ compose_registered: bool
│     └─ errors: tuple[str, ...]
├─ created_at: str (ISO 8601)
└─ updated_at: str (ISO 8601)

Persisted to:
.specforge/features/{service_slug}/.execution-state.json

## LOCK MANAGEMENT

Acquire:
1. os.open(lock_path, O_CREAT|O_EXCL|O_WRONLY)
2. Write JSON: {service_slug, pid, timestamp}
3. fsync + close
4. Cross-platform atomic (Windows + Unix)

Stale Detection:
- Lock older than 30 minutes = stale
- Can force override with --force flag

Release:
- Unlink lock file (best effort)
- Safe in try/finally

## ARCHITECTURE ADAPTATION

ArchitectureAdapter (Protocol):
├─ MicroserviceAdapter
│  ├─ Dependencies + communication patterns
│  ├─ API contract-based entity scope
│  ├─ Service mesh research topics
│  ├─ 5 deployment plan sections
│  ├─ 3 container/registration tasks
│  └─ 4 distributed failure edge cases
├─ MonolithAdapter
│  ├─ Shared module context
│  ├─ Shared table entity scope
│  ├─ Module dependency analysis
│  ├─ Shared infrastructure sections
│  ├─ Module integration task
│  └─ Module boundary edge cases
└─ ModularMonolithAdapter (extends Monolith)
   ├─ Strict boundary enforcement
   ├─ Interface-based contracts
   ├─ Boundary violation edge case
   └─ Cross-module DB restriction

## PARALLEL EXECUTION CAPABILITIES

Shared Infra First:
  specforge implement --shared-infra
  └─ Runs cross-service-infra tasks.md
  └─ Sets shared_infra_complete flag
  └─ Only for microservice|modular-monolith

Sequential Services (Feature 011):
  ImplementationOrchestrator.execute_all()
  ├─ If --shared-infra: run shared infra first
  ├─ For each service (sequentially):
  │  └─ SubAgentExecutor.execute(service_slug, mode, resume=False)
  │     └─ Sequential tasks within each service
  └─ Report aggregated results

Within-Service Parallelization:
  - Tasks in tasks.md marked with parallel: bool
  - Build sequence respects dependencies
  - Can parallelize non-dependent tasks (future)

## TOKEN BUDGET

Context Priority (for truncation):
  1. edge_cases (lowest - truncate first)
  2. architecture_prompts
  3. dependency_contracts
  4. data_model
  5. plan
  6. governance_prompts
  7. spec
  8. constitution
  9. current_task (highest - truncate last/never)

Budget: 100,000 tokens
Estimate: chars / 4
Strict enforcement: no overflow

## QUALITY GATE FLOW

Task completes (list[Path] changed_files):
  ├─ If empty: mark skipped
  └─ Else:
     └─ QualityGate.run_task_checks(files, ctx)
        ├─ Run 15 checkers (filtered by architecture)
        ├─ Aggregate results
        └─ If passed:
           ├─ git commit
           ├─ mark_task_completed(commit_sha)
           └─ save_state()
        └─ Else if auto_fix:
           ├─ AutoFixLoop.fix(prompt, qc, files, mode)
           ├─ Up to 3 attempts with rollback
           ├─ Quality check again
           └─ If passed: git commit + mark completed
           └─ Else: mark failed
        └─ Else (no auto-fix):
           ├─ git commit anyway (permissive)
           ├─ mark_task_completed()
           └─ save_state()

## FILE STRUCTURE

.specforge/
├─ manifest.json (service decomposition)
├─ features/
│  ├─ {service_slug}/
│  │  ├─ spec.md
│  │  ├─ research.md
│  │  ├─ data-model.md
│  │  ├─ edge-cases.md
│  │  ├─ plan.md
│  │  ├─ checklist.md
│  │  ├─ tasks.md (input to implementation)
│  │  ├─ .execution-state.json (progress tracking)
│  │  ├─ .execution-lock (prevents concurrent execution)
│  │  └─ contracts/
│  │     ├─ api-spec.json (generated)
│  │     └─ api-spec.stub.json (for dependencies)
│  └─ cross-service-infra/
│     ├─ tasks.md
│     └─ .execution-state.json
├─ .pipeline-state.json (spec generation progress)
└─ .pipeline-lock

## CONVENTIONAL COMMIT FORMAT

Format: feat({service_slug}): {description} [{task_id}]

Example:
  feat(ledger-service): Implement account repository [T5]

Stored in ExecutionState:
  task.commit_sha = "a1b2c3d" (short SHA via git rev-parse --short HEAD)

Traceable:
  git log --grep=T5
  git show a1b2c3d
  git log --oneline --all | grep "\[T5\]"

