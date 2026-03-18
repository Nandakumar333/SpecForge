# Implementation Plan: Implementation Orchestrator

**Branch**: `011-implementation-orchestrator` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-implementation-orchestrator/spec.md`

## Summary

Build the multi-service implementation orchestrator that reads the project manifest, computes a phased execution plan from the dependency graph, and orchestrates `SubAgentExecutor` (Feature 009) across all services with inter-phase contract verification and final integration validation. In microservice mode: shared infra → dependency-ordered phases → contract verification per phase → full integration test. In monolith mode: topological module ordering → build/test per module → single-app integration test. The orchestrator introduces new core modules for dependency graph computation, phase execution, contract enforcement, and integration reporting, following existing patterns from `PipelineOrchestrator` and `SubAgentExecutor`.

## Technical Context

**Language/Version**: Python 3.11+ (existing)
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (report rendering), GitPython 3.x (commit ops) — all existing
**Storage**: File system — `.specforge/orchestration-state.json` (project-level), `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (per-service state, read/write)
**Testing**: pytest + pytest-cov + syrupy + ruff — existing toolchain
**Target Platform**: Cross-platform CLI (Windows + macOS + Linux)
**Project Type**: CLI tool (extension of existing `specforge implement` command)
**Performance Goals**: Phase transition overhead < 5 seconds; dependency graph computation < 1 second for 20 services
**Constraints**: Functions ≤ 30 lines, classes ≤ 200 lines; `Result[T, E]` for all recoverable errors; frozen dataclasses for all models; constructor injection only
**Scale/Scope**: Up to 20 services across 5+ phases; up to 50 tasks per service

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md complete with 7 user stories, 26 FRs; plan.md (this file) being created; tasks.md will follow |
| II. Architecture | ✅ PASS | All new modules in `src/specforge/core/` (domain logic, zero external deps). Reports via Jinja2 templates. Plugin boundary preserved (delegates to existing agent adapters) |
| III. Code Quality | ✅ PASS | All models frozen dataclasses; `Result[T, E]` return types; constructor injection; constants in config.py; functions ≤ 30 lines |
| IV. Testing | ✅ PASS | TDD: tests written before implementation. Unit tests for all domain logic. Integration tests for CLI with CliRunner + tmp_path |
| V. Commit Strategy | ✅ PASS | Conventional commits, one per task |
| VI. File Structure | ✅ PASS | Core logic in `core/`, CLI in `cli/`, templates in `templates/`, tests in `tests/unit/` and `tests/integration/` |
| VII. Governance | ✅ PASS | No conflicts. Constitution takes precedence |

## Project Structure

### Documentation (this feature)

```text
specs/011-implementation-orchestrator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── orchestrate-cmd.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   └── implement_cmd.py          # Extended: --all, --to-phase, --resume flags
├── core/
│   ├── orchestrator_models.py    # OrchestrationPlan, Phase, OrchestrationState, VerificationResult, IntegrationReport
│   ├── dependency_graph.py       # Topological sort, cycle detection, phase grouping
│   ├── phase_executor.py         # Runs all services in a phase via SubAgentExecutor
│   ├── contract_enforcer.py      # Post-phase contract verification between service pairs
│   ├── integration_test_runner.py # docker-compose up + health checks + request flow + event propagation
│   ├── integration_reporter.py   # Generates Markdown integration report via Jinja2
│   ├── orchestration_state.py    # Project-level state persistence (load/save/update)
│   └── config.py                 # New constants (ORCHESTRATION_STATE_FILENAME, PHASE_STATUSES, etc.)
├── templates/
│   └── base/
│       └── features/
│           └── integration-report.md.j2  # Report template
└── plugins/
    └── (no changes)

tests/
├── unit/
│   ├── test_orchestrator_models.py
│   ├── test_dependency_graph.py
│   ├── test_phase_executor.py
│   ├── test_contract_enforcer.py
│   ├── test_integration_test_runner.py
│   ├── test_integration_reporter.py
│   └── test_orchestration_state.py
└── integration/
    ├── test_implement_all_microservice.py
    ├── test_implement_all_monolith.py
    └── test_implement_all_resume.py
```

**Structure Decision**: Single project structure. All new modules placed in `src/specforge/core/` following Feature 009/010 patterns. No new top-level directories. CLI extension in existing `implement_cmd.py`.

## Design Decisions

### DD-001: Separate IntegrationOrchestrator (not extending PipelineOrchestrator)

**Decision**: Create a new `IntegrationOrchestrator` class rather than extending the existing `PipelineOrchestrator`.

**Rationale**: `PipelineOrchestrator` manages spec generation phases (research → clarify → edge-cases → tasks) for a single service. `IntegrationOrchestrator` manages implementation phases across multiple services. Different domain, different state model, different phase semantics. Composition over inheritance — the new orchestrator delegates to `SubAgentExecutor` (Feature 009) and `SharedInfraExecutor` (Feature 009) for actual service implementation.

**Naming note**: The feature is titled "Implementation Orchestrator" (it orchestrates implementation). The class is named `IntegrationOrchestrator` (it orchestrates integration across services via phased dependency resolution). Both terms are accurate at different levels of abstraction.

**Alternatives rejected**: Extending `PipelineOrchestrator` with implementation phases — rejected because it would violate single responsibility and mix spec-generation concerns with implementation concerns.

### DD-002: Dependency Graph as Pure Function Module

**Decision**: `dependency_graph.py` as a module of pure functions (not a class). Functions: `build_graph(manifest) → Result[Graph, str]`, `detect_cycles(graph) → tuple[tuple[str, ...], ...]`, `compute_phases(graph) → Result[tuple[Phase, ...], str]`.

**Rationale**: Graph operations are stateless transformations. Pure functions are easier to test and compose. Matches the pattern used by `execution_state.py` (module of pure functions operating on frozen dataclasses).

### DD-003: Intra-Phase Failure Policy — Continue-Then-Halt

**Decision**: When a service fails within a phase, remaining services in the same phase continue to completion. The orchestrator then halts before the next phase.

**Rationale**: Same-phase services have no mutual dependencies (by definition of phase grouping). Completing all independent services maximizes useful work. Halting before the next phase prevents building on incomplete foundations. This matches the spec clarification.

### DD-003a: Within-Phase Sequential Execution

**Decision**: Services within a phase are executed sequentially (one at a time), not in parallel. Parallel within-phase execution is deferred to a future feature.

**Rationale**: While same-phase services have no _logical_ dependencies, parallel execution introduces practical conflicts: port collisions during testing, interleaved git commits, shared filesystem contention, and non-deterministic console output. Sequential execution is simpler, safer, and sufficient for initial release. The `[P]` marker in the dependency graph denotes _parallelizable_ (no mutual dependency), not "will run in parallel."

### DD-004: Contract Enforcement via Published Contracts (Not Code Inspection)

**Decision**: `ContractEnforcer` loads published contract files from `.specforge/features/<slug>/contracts/` and compares them across service pairs. It does NOT inspect generated source code.

**Rationale**: Contract files are the source of truth for inter-service agreements (established by Feature 009's shared infra pre-phase). Code inspection would require language-specific parsers and couple the enforcer to implementation details. Contract files are declarative and stack-agnostic.

### DD-005: Orchestration State at Project Level

**Decision**: Persist orchestration state in `.specforge/orchestration-state.json` (project-level), separate from per-service execution state in `.specforge/features/<slug>/.execution-state.json`.

**Rationale**: The orchestrator tracks project-wide progress (which phases are complete, which services in each phase, verification results). This is a different granularity from per-service task progress. Separating them enables the orchestrator to resume without interfering with service-level state. Follows atomic-write pattern from `pipeline_state.py`.

### DD-006: Monolith Orchestration as Architecture Adapter Pattern

**Decision**: Use the existing `ArchitectureAdapter` protocol to switch behavior between microservice and monolith modes. The orchestrator checks `architecture` from manifest and delegates to mode-specific logic for: pre-phase (skip in monolith), verification type (contract vs boundary), and integration test type (docker-compose vs single-app).

**Rationale**: Existing `ArchitectureAdapter` already provides mode-specific behavior for spec generation. Extending this pattern to implementation orchestration maintains consistency. The adapter pattern keeps the core orchestration loop clean while allowing mode-specific behavior to be isolated and tested independently.

### DD-007: Integration Test Auto-Generation from Contracts

**Decision**: `IntegrationTestRunner` auto-generates test cases from published contract files rather than requiring manually written integration tests. Tests are generated as temporary test files, executed, and cleaned up.

**Rationale**: Contracts define the expected behavior between services. Auto-generating tests ensures 100% contract coverage with no manual drift. Generated tests are ephemeral (not committed) — they validate the current state of contracts, not a manually maintained test suite.

### DD-008: docker-compose for Integration Validation

**Decision**: Use actual `docker-compose up` (the same configuration generated by shared-infra pre-phase) for integration validation. Not Testcontainers.

**Rationale**: The shared infra pre-phase already generates docker-compose files. Using the same files for validation ensures what's tested matches what's deployed. Testcontainers would add a Java/language-specific dependency. docker-compose is already an assumed dependency for microservice mode.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        implement_cmd.py                             │
│              --all  --to-phase N  --resume                          │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    IntegrationOrchestrator                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. Load manifest → architecture + services + deps            │   │
│  │ 2. Build dependency graph → detect cycles → compute phases   │   │
│  │ 3. Pre-flight validation (artifacts exist, no cycles)        │   │
│  │ 4. Execute shared infra pre-phase (microservice only)        │   │
│  │ 5. For each phase:                                           │   │
│  │    a. PhaseExecutor.run(phase_services)                      │   │
│  │    b. ContractEnforcer.verify(all_implemented_services)       │   │
│  │    c. If fail → halt + report                                │   │
│  │ 6. IntegrationTestRunner.run(all_services)                   │   │
│  │ 7. IntegrationReporter.generate(results)                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──┬────────────┬──────────────┬────────────────┬─────────────────────┘
   │            │              │                │
   ▼            ▼              ▼                ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐
│ Phase  │ │ Contract │ │ Integration  │ │ Integration   │
│Executor│ │ Enforcer │ │ Test Runner  │ │ Reporter      │
└───┬────┘ └──────────┘ └──────────────┘ └───────────────┘
    │
    ▼ (delegates per service)
┌───────────────────────┐    ┌──────────────────────┐
│  SubAgentExecutor     │    │  SharedInfraExecutor  │
│  (Feature 009)        │    │  (Feature 009)        │
└───────────────────────┘    └──────────────────────┘
```

## Data Flow

```
manifest.json
    │
    ▼
dependency_graph.build_graph()
    │
    ▼
OrchestrationPlan (phases: [Phase(services=[...]), ...])
    │
    ▼
OrchestrationState (persisted between phases)
    │
    ├── Phase 0: SharedInfraExecutor.execute()
    │       └── Result → update state
    │
    ├── Phase N: PhaseExecutor.run(phase)
    │       ├── SubAgentExecutor.execute(svc_1) → ExecutionState
    │       ├── SubAgentExecutor.execute(svc_2) → ExecutionState
    │       └── ...
    │       │
    │       ▼
    │   ContractEnforcer.verify(implemented_services)
    │       └── VerificationResult (pass/fail per service pair)
    │
    ├── Integration: IntegrationTestRunner.run()
    │       └── IntegrationTestResult
    │
    └── IntegrationReporter.generate()
            └── integration-report.md
```

## Complexity Tracking

> No constitution violations. All modules fit within size limits. No additional complexity justifications needed.
