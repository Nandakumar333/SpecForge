# Implementation Plan: Task Generation Engine

**Branch**: `008-task-generation-engine` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-task-generation-engine/spec.md`

## Summary

Build a task generation engine that converts `plan.md` and `manifest.json` into ordered, parallelizable `tasks.md` files per service/module. The engine uses architecture-specific build sequences (14-step for microservice, 7-step for monolith) to produce dependency-ordered tasks with parallelization markers, effort estimates, file path hints, and governance rule references. Cross-service infrastructure tasks are generated once in a dedicated `cross-service-infra/tasks.md` file for microservice/modular-monolith architectures.

The implementation extends the existing `TasksPhase` pipeline phase by replacing its basic template delegation with a multi-component orchestrator: `TaskGenerator` coordinates `DependencyResolver` (DAG construction + topological sort), `ArchitectureTaskAdapter` (build sequence selection), `CrossServiceTaskGenerator` (shared infra deduplication), and `EffortEstimator` (T-shirt sizing). The engine reads Feature 003 governance files via the existing `PromptLoader` (read-only) to enrich task descriptions with coding standard references.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering), PyYAML 6.x (pattern files) — all existing  
**Storage**: File system — `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (write tasks.md)  
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)  
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)  
**Project Type**: CLI tool extension (new core modules + enhanced pipeline phase)  
**Performance Goals**: Single service ≤10s, full project (5+ services) ≤30s  
**Constraints**: Functions ≤30 lines, classes ≤200 lines, frozen dataclasses, Result[T] for errors, constructor injection, type hints everywhere  
**Scale/Scope**: Projects with 1–20 services/modules, up to 50 tasks per service

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md complete with 5 user stories, 23 FRs, 8 SCs. Clarifications resolved. |
| II. Architecture | ✅ PASS | New modules in `core/` (zero external deps). Output via Jinja2 template. No string concat. |
| III. Code Quality | ✅ PASS | All functions ≤30 lines. Frozen dataclasses. Result[T] returns. Constructor injection. |
| IV. Testing | ✅ PASS | TDD: unit tests per module, integration tests for CLI, snapshots for template output. |
| V. Commit Strategy | ✅ PASS | One conventional commit per task. PR references spec. |
| VI. File Structure | ✅ PASS | New modules in `src/specforge/core/`. Tests in `tests/unit/` and `tests/integration/`. |
| VII. Governance | ✅ PASS | No conflicts. Engine reads governance files (read-only, FR-021). |

## Project Structure

### Documentation (this feature)

```text
specs/008-task-generation-engine/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: usage guide
├── contracts/
│   └── generate-tasks-cmd.md   # CLI contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── core/
│   ├── task_models.py            # TaskItem, TaskFile, BuildStep, EffortSize (frozen dataclasses)
│   ├── task_generator.py         # TaskGenerator — main orchestrator
│   ├── dependency_resolver.py    # DAG builder, topological sort, cycle detection, parallel marking
│   ├── build_sequence.py         # BuildSequence definitions per architecture
│   ├── cross_service_tasks.py    # CrossServiceTaskGenerator — shared infra (microservice only)
│   ├── effort_estimator.py       # EffortEstimator — S/M/L/XL assignment
│   ├── governance_reader.py      # GovernanceReader — read-only prompt rule extraction
│   ├── config.py                 # + MICROSERVICE_BUILD_SEQUENCE, MONOLITH_BUILD_SEQUENCE, etc.
│   └── phases/
│       └── tasks_phase.py        # Enhanced TasksPhase (replaces current basic version)
├── templates/base/features/
│   └── tasks.md.j2               # Enhanced template with effort, deps, file paths, XDEP

tests/
├── unit/
│   ├── test_task_models.py
│   ├── test_task_generator.py
│   ├── test_dependency_resolver.py
│   ├── test_build_sequence.py
│   ├── test_cross_service_tasks.py
│   ├── test_effort_estimator.py
│   ├── test_governance_reader.py
│   └── test_phases/
│       └── test_tasks_phase.py
├── integration/
│   ├── test_generate_tasks_cmd.py
│   ├── test_task_generation_microservice.py
│   ├── test_task_generation_monolith.py
│   └── test_task_generation_modular_monolith.py
└── snapshots/
    └── test_tasks_template_rendering.py
```

**Structure Decision**: Single project layout (existing SpecForge structure). All new modules are in `src/specforge/core/` with one module per concern. No new CLI command — the engine plugs into the existing `TasksPhase` within the pipeline and can be triggered via `specforge specify <target>`.

---

## Design Decisions

### D1: Task Generation Data Model

Six frozen dataclasses model the task domain:

```
EffortSize (Literal["S", "M", "L", "XL"])

BuildStep (frozen dataclass)
├── order: int                    # Position in build sequence (1-14 or 1-7)
├── category: str                 # e.g., "scaffolding", "domain_models", "service_layer"
├── description_template: str     # Human-readable template with {service} placeholder
├── default_effort: EffortSize    # Architecture-specific default
├── file_path_pattern: str        # e.g., "src/{service}/domain/models/"
├── depends_on: tuple[int, ...]   # Order numbers this step depends on
└── parallelizable_with: tuple[int, ...]  # Steps that can run concurrently

TaskItem (frozen dataclass)
├── id: str                       # e.g., "T001"
├── description: str              # Human-readable task description
├── phase: int                    # Build sequence phase group
├── layer: str                    # Technical layer (e.g., "domain", "repository", "service")
├── dependencies: tuple[str, ...]  # Task IDs (local: "T001", external: "cross-service-infra/T001")
├── parallel: bool                # True if can run concurrently with siblings
├── effort: EffortSize            # S/M/L/XL
├── user_story: str               # e.g., "US1"
├── file_paths: tuple[str, ...]   # Concrete file path hints
├── service_scope: str            # Service/module slug
├── governance_rules: tuple[str, ...]  # e.g., ("ARCH-001", "BACK-001")
└── commit_message: str           # Conventional commit suggestion

TaskFile (frozen dataclass)
├── target_name: str              # Service/module slug or "cross-service-infra"
├── architecture: str             # "monolithic" | "microservice" | "modular-monolith"
├── tasks: tuple[TaskItem, ...]   # Ordered task list
├── phases: tuple[tuple[int, tuple[TaskItem, ...]], ...]  # Grouped by phase
└── total_count: int              # len(tasks)

GenerationSummary (frozen dataclass)
├── generated_files: tuple[str, ...]   # Relative paths of all tasks.md produced
├── task_counts: dict[str, int]        # Service slug → count
├── cross_dependencies: tuple[str, ...]  # XDEP references across files
└── warnings: tuple[str, ...]          # Skipped services, missing plans
```

**Immutability**: All dataclasses are frozen. Task lists are built via list comprehension, then converted to tuples at construction.

### D2: TaskGenerator — Main Orchestrator

```
TaskGenerator(
    manifest_path: Path,
    prompt_loader: PromptLoader,      # Existing — for governance rule extraction
    renderer: TemplateRenderer,       # Existing — for Jinja2 rendering
    registry: TemplateRegistry,       # Existing — for template discovery
)

generate_for_service(service_slug: str, plan_content: str) -> Result[TaskFile, str]
├── Step 1: Load ServiceContext from manifest
├── Step 2: Select BuildSequence via architecture type
├── Step 3: Extract features and group by technical layer (FR-022)
├── Step 4: Generate TaskItems per BuildStep, filtering inapplicable steps (FR-014)
├── Step 5: Resolve governance rules via GovernanceReader (FR-021)
├── Step 6: Assign effort estimates via EffortEstimator (FR-020)
├── Step 7: Build DependencyGraph and compute topological order (FR-006)
├── Step 8: Mark parallelizable tasks (FR-005)
├── Step 9: Cap at 50 tasks, grouping if needed (FR-018)
└── Step 10: Return TaskFile

generate_for_project(project_root: Path) -> Result[GenerationSummary, str]
├── Step 1: Load manifest, validate architecture (FR-001)
├── Step 2: Detect circular service dependencies (FR-007)
├── Step 3: Generate cross-service-infra tasks if microservice/modular-monolith (FR-008)
├── Step 4: For each service, validate plan.md exists (FR-015), generate tasks
├── Step 5: Inject XDEP references for cross-service dependencies (FR-010)
├── Step 6: Render each TaskFile via Jinja2 template
├── Step 7: Backup existing tasks.md files (FR-023)
├── Step 8: Write all output files
└── Step 9: Return GenerationSummary (FR-017)
```

**Constructor injection**: `TaskGenerator` receives all dependencies via `__init__`. No global state.

### D3: DependencyResolver — DAG + Topological Sort

```
DependencyResolver()

build_graph(tasks: list[TaskItem]) -> Result[DependencyGraph, str]
├── Step 1: Create adjacency list from task.dependencies
├── Step 2: Validate all dependency IDs exist (FR-005 reference integrity)
├── Step 3: Detect cycles via DFS with color marking (FR-007)
├── Step 4: If cycle found, return Err with cycle path string
└── Step 5: Return DependencyGraph

topological_sort(graph: DependencyGraph) -> list[TaskItem]
├── Step 1: Kahn's algorithm with in-degree tracking
├── Step 2: Stable sort by (phase, order) for deterministic output
└── Step 3: Return ordered task list

mark_parallel(tasks: list[TaskItem], graph: DependencyGraph) -> list[TaskItem]
├── Step 1: Group tasks by dependency depth level
├── Step 2: Within each level, identify tasks with disjoint file paths
├── Step 3: Mark disjoint tasks with parallel=True
└── Step 4: Tasks sharing file paths at same level stay parallel=False
```

**Cycle detection**: DFS with white/gray/black coloring. Gray-to-gray edge indicates a cycle. The error message includes the full cycle path: `"Circular dependency: A → B → C → A"`.

### D4: BuildSequence — Architecture-Specific Ordering

```
MICROSERVICE_BUILD_SEQUENCE: tuple[BuildStep, ...] = (
    BuildStep(1,  "scaffolding",          "Set up {service} project scaffold",              "S", "src/{service}/",                        (),     ()),
    BuildStep(2,  "domain_models",        "Create domain models and value objects",          "M", "src/{service}/domain/models/",           (1,),   ()),
    BuildStep(3,  "database",             "Configure database context, migrations, seeds",   "L", "src/{service}/infrastructure/data/",     (2,),   ()),
    BuildStep(4,  "repository",           "Implement repository interfaces + implementations","M", "src/{service}/infrastructure/repos/",    (3,),   ()),
    BuildStep(5,  "service_layer",        "Implement service layer with validation",         "L", "src/{service}/application/services/",    (4,),   ()),
    BuildStep(6,  "communication_clients", "Create communication clients for dependent services","M", "src/{service}/infrastructure/clients/",  (5,),   ()),
    BuildStep(7,  "controllers",          "Implement API controllers + middleware",           "M", "src/{service}/api/controllers/",         (5,),   (6,)),
    BuildStep(8,  "event_handlers",       "Implement event publishers/consumers",             "M", "src/{service}/infrastructure/events/",   (5,),   (6, 7)),
    BuildStep(9,  "health_checks",        "Add health check endpoints",                      "S", "src/{service}/api/health/",              (7,),   (8,)),
    BuildStep(10, "contract_tests",       "Write contract tests against dependencies",       "L", "tests/{service}/contract/",              (6,),   ()),
    BuildStep(11, "unit_tests",           "Write unit tests for all layers",                 "L", "tests/{service}/unit/",                  (5,),   (10,)),
    BuildStep(12, "integration_tests",    "Write integration tests",                         "XL","tests/{service}/integration/",           (11,),  ()),
    BuildStep(13, "container_optimization","Optimize Dockerfile (multi-stage build)",         "S", "src/{service}/Dockerfile",               (7,),   (12,)),
    BuildStep(14, "gateway_config",       "Configure API gateway routes",                    "S", "infrastructure/gateway/",                (7,),   (13,)),
)

MONOLITH_BUILD_SEQUENCE: tuple[BuildStep, ...] = (
    BuildStep(1, "folder_structure",  "Set up {module} module folder structure",           "S", "src/modules/{module}/",                 (),    ()),
    BuildStep(2, "domain_models",     "Create domain models",                              "M", "src/modules/{module}/models/",          (1,),  ()),
    BuildStep(3, "database",          "Create database migrations (shared DbContext)",      "M", "src/modules/{module}/migrations/",      (2,),  ()),
    BuildStep(4, "repo_service",      "Implement repository + service layers",             "L", "src/modules/{module}/services/",        (3,),  ()),
    BuildStep(5, "controllers",       "Implement controllers",                             "M", "src/modules/{module}/controllers/",     (4,),  ()),
    BuildStep(6, "boundary_interface","Define module boundary interface",                   "M", "src/modules/{module}/contracts/",       (4,),  (5,)),
    BuildStep(7, "tests",            "Write unit + integration tests",                     "L", "tests/modules/{module}/",               (5,),  ()),
)
```

**Step filtering** (FR-014): Before generating tasks, steps are filtered based on service context:
- Step 6 (communication clients): omitted if `service_ctx.dependencies` is empty
- Step 8 (events): omitted if `service_ctx.events` is empty
- Step 10 (contract tests): omitted if no dependencies
- Step 6 (boundary interface, monolith): omitted if architecture is plain `monolithic` (not modular-monolith)
- Step 3 (database): omitted if no database entities detected in features

### D5: CrossServiceTaskGenerator — Shared Infrastructure

```
CrossServiceTaskGenerator(manifest_path: Path)

generate(services: list[ServiceContext]) -> Result[TaskFile, str]
├── Step 1: Collect all communication patterns across services
├── Step 2: Collect all events (producer/consumer pairs)
├── Step 3: Generate tasks for each cross-service concern:
│   ├── X-T001: Shared contracts library (protobuf defs, event schemas)
│   ├── X-T002: Docker compose file (all services + infrastructure)
│   ├── X-T003: Message broker setup (exchanges, queues)
│   ├── X-T004: API gateway master configuration
│   └── X-T005: Shared authentication middleware
├── Step 4: Filter — only include tasks for declared concerns
│   ├── No message broker task if no async events exist
│   └── No gateway task if no REST/gRPC endpoints
└── Step 5: Return TaskFile with target_name="cross-service-infra"
```

**Cross-service tasks use `X-T` prefix** to distinguish from per-service task IDs. Per-service tasks reference them as `[XDEP: cross-service-infra/X-T001]`.

**Architecture guard**: `generate()` returns `Ok(empty TaskFile)` for monolithic architecture. No caller-side check needed.

**Architecture-specific cross-service categories**:
| Category | Microservice | Modular-Monolith | Monolithic |
|---|---|---|---|
| shared_contracts (X-T001) | ✅ | ✅ | ❌ |
| docker_compose (X-T002) | ✅ | ❌ | ❌ |
| message_broker (X-T003) | ✅ (if async events) | ❌ | ❌ |
| api_gateway (X-T004) | ✅ (if REST/gRPC) | ❌ | ❌ |
| shared_auth (X-T005) | ✅ | ✅ | ❌ |

Modular-monolith includes only `shared_contracts` and `shared_auth` — modules share a process boundary so Docker compose, message broker, and gateway are unnecessary.

### D6: EffortEstimator — T-Shirt Sizing

```
EffortEstimator()

estimate(step: BuildStep, feature_count: int, dependency_count: int) -> EffortSize
├── Step 1: Start with step.default_effort
├── Step 2: If feature_count > 3, bump by one size (M→L, L→XL)
├── Step 3: If dependency_count > 2 and step is "communication_clients", bump by one size
├── Step 4: Cap at XL (never exceed)
└── Step 5: Return EffortSize
```

**Effort bump rules** (codified in `config.py`):
| Step Category | Base (1-2 features) | 3-4 features | 5+ features | Notes |
|---|---|---|---|---|
| scaffolding | S | S | M | Minimal scaling |
| domain_models | M | L | L | More entities to define |
| database | L | L | XL | More migrations, shared context complexity |
| repository | M | L | L | One repo per entity |
| service_layer | L | L | XL | Most business logic lives here |
| communication_clients | M | L | L | +1 bump if >2 deps regardless of features |
| controllers | M | L | L | More endpoints per feature |
| event_handlers | M | M | L | Scales with event count, not feature count |
| health_checks | S | S | S | Fixed effort regardless of features |
| contract_tests | L | L | XL | One suite per dependency |
| unit_tests | L | XL | XL | Scales linearly with feature count |
| integration_tests | XL | XL | XL | Always XL — infrastructure overhead dominates |
| container_optimization | S | S | M | Larger images need more optimization at scale |
| gateway_config | S | S | M | More routes per feature |

### D7: GovernanceReader — Read-Only Prompt Rule Extraction

```
GovernanceReader(prompt_loader: PromptLoader)

get_relevant_rules(layer: str, architecture: str) -> tuple[str, ...]
├── Step 1: Load PromptSet via prompt_loader.load_for_feature("*")
├── Step 2: Filter rules by scope matching layer (e.g., "function" → service layer)
├── Step 3: Filter by architecture applicability
├── Step 4: Return tuple of rule_id strings (e.g., ("ARCH-001", "BACK-001"))
└── Fallback: Return empty tuple if prompt files not found (graceful degradation)
```

**Read-only contract**: GovernanceReader only calls `PromptLoader.load_for_feature()`. It never writes to `.specforge/prompts/`. If governance files don't exist (e.g., `specforge init` was run without `--stack`), the reader returns empty tuples and task descriptions omit the `Prompt-rules:` line.

**Complete scope-to-layer mapping**:

| Governance Scope | Matched Build Steps | Rule Prefix Examples |
|---|---|---|
| `scope: "class"` | domain_models (2), database entities | ARCH-001 (SRP), BACK-001 |
| `scope: "function"` | service_layer (5), repository (4), controllers (7), communication_clients (6) | ARCH-003 (DI), BACK-002 |
| `scope: "module"` | scaffolding (1), gateway_config (14), container_optimization (13) | ARCH-002 (dependency direction) |
| `scope: "file"` | database config (3), health_checks (9), event_handlers (8) | DB-001, SEC-001 |
| `scope: "test"` | unit_tests (11), integration_tests (12), contract_tests (10) | TEST-001, TEST-002 |
| *(unmapped)* | Steps with no matching governance scope | Returns empty tuple — no `Prompt-rules:` line |

The mapping is approximate — `scope: "function"` matches any step that primarily produces function-level code (services, repositories, controllers). Steps with no matching scope gracefully return empty governance tuples.

### D8: Enhanced TasksPhase

The existing `TasksPhase` is replaced with an enhanced version that uses `TaskGenerator` instead of simple template delegation:

```
TasksPhase(BasePhase)
├── name = "tasks"
├── artifact_filename = "tasks.md"

_build_context(service_ctx, adapter, input_artifacts) -> dict
├── Step 1: Extract plan.md content from input_artifacts
├── Step 2: Create TaskGenerator with injected dependencies
├── Step 3: Call generate_for_service(service_slug, plan_content)
├── Step 4: If Err, propagate error
├── Step 5: Convert TaskFile to template context dict
└── Step 6: Return context for Jinja2 rendering

run(service_ctx, adapter, renderer, registry, input_artifacts) -> Result
├── Step 1: Backup existing tasks.md → tasks.md.bak (FR-023)
├── Step 2: Call parent run() with enhanced context
└── Step 3: Return Result
```

**Backward compatibility**: The enhanced `TasksPhase` still implements `BasePhase` protocol. The pipeline orchestrator calls it identically. Only the internal context-building logic changes.

**Supersedes `get_task_extras()`**: The 14-step `MICROSERVICE_BUILD_SEQUENCE` subsumes the old `ArchitectureAdapter.get_task_extras()` return values. The old 3-task extras are replaced: "Container build" → step 13 (container_optimization), "Service registration" → step 9 (health_checks) + step 14 (gateway_config), "Contract tests" → step 10 (contract_tests). The existing `get_task_extras()` method is no longer called by the enhanced `TasksPhase`.

### D9: Enhanced tasks.md.j2 Template

The template is restructured to support the richer task format:

```
Output format per task:
T001 [P] [US1] [Layer:domain] Create Account entity
  Service: ledger-service
  Files: src/LedgerService.Domain/Entities/Account.cs
  Depends: T000 (project scaffolding)
  Effort: S
  Prompt-rules: ARCH-001, BACK-001
  Commit: feat(ledger): add Account entity
```

Template sections:
1. Header with metadata (service, architecture, date)
2. Cross-service dependencies section (if any `[XDEP:]` references)
3. Phase-grouped tasks with dependency and effort annotations
4. Summary footer (total tasks, effort breakdown, parallelization stats)

### D10: Config Constants

New constants added to `config.py`:

```python
# Task Generation (Feature 008)
TASK_ID_PREFIX: str = "T"
CROSS_SERVICE_TASK_PREFIX: str = "X-T"
CROSS_SERVICE_TARGET: str = "cross-service-infra"
MAX_TASKS_PER_SERVICE: int = 50

EFFORT_SIZES: tuple[str, ...] = ("S", "M", "L", "XL")
EFFORT_BUMP_THRESHOLD_FEATURES: int = 3
EFFORT_BUMP_THRESHOLD_DEPS: int = 2

CROSS_SERVICE_CATEGORIES: tuple[str, ...] = (
    "shared_contracts",
    "docker_compose",
    "message_broker",
    "api_gateway",
    "shared_auth",
)

MICROSERVICE_STEP_COUNT: int = 14
MONOLITH_STEP_COUNT: int = 7

# Step categories that are conditionally included
CONDITIONAL_STEPS: dict[str, str] = {
    "communication_clients": "dependencies",  # Requires non-empty dependencies
    "event_handlers": "events",             # Requires non-empty events
    "contract_tests": "dependencies",       # Requires non-empty dependencies
    "boundary_interface": "modular-monolith", # Requires modular-monolith arch
    "database": "entities",                 # Requires database entities
}
```

---

## Integration Points

| Component | Integrates With | Direction |
|-----------|----------------|-----------|
| `task_generator.py` | `service_context.py` (ServiceContext, ServiceDependency, EventInfo) | reads |
| `task_generator.py` | `build_sequence.py` (MICROSERVICE/MONOLITH_BUILD_SEQUENCE) | reads |
| `task_generator.py` | `dependency_resolver.py` (DependencyResolver) | orchestrates |
| `task_generator.py` | `effort_estimator.py` (EffortEstimator) | orchestrates |
| `task_generator.py` | `governance_reader.py` (GovernanceReader) | orchestrates |
| `task_generator.py` | `cross_service_tasks.py` (CrossServiceTaskGenerator) | orchestrates |
| `dependency_resolver.py` | `task_models.py` (TaskItem, DependencyGraph) | reads/writes |
| `cross_service_tasks.py` | `service_context.py` (ServiceContext) | reads |
| `cross_service_tasks.py` | `config.py` (CROSS_SERVICE_CATEGORIES) | reads |
| `governance_reader.py` | `prompt_loader.py` (PromptLoader, PromptSet) | reads |
| `governance_reader.py` | `prompt_models.py` (PromptRule) | reads |
| `effort_estimator.py` | `task_models.py` (BuildStep, EffortSize) | reads |
| `effort_estimator.py` | `config.py` (EFFORT_BUMP_THRESHOLD_*) | reads |
| `phases/tasks_phase.py` | `task_generator.py` (TaskGenerator) | orchestrates |
| `phases/tasks_phase.py` | `phases/base_phase.py` (BasePhase) | extends |
| `tasks.md.j2` | `task_models.TaskFile` (via context dict) | renders |
| `config.py` | All task generation modules | constants |

### With Feature 003 (Prompt Governance)

**Read-only integration**. `GovernanceReader` calls `PromptLoader.load_for_feature()` to get `PromptSet`. It reads `PromptRule.rule_id`, `PromptRule.scope`, and `PromptRule.severity` to match rules to task layers. It never writes to `.specforge/prompts/`. If governance files are absent, all rule fields default to empty tuples.

### With Feature 004 (Architecture Decomposer)

**Manifest consumption**. `TaskGenerator` reads `.specforge/manifest.json` (written by Feature 004) to obtain: architecture type, services/modules array, service dependencies, communication patterns, and event definitions. The manifest is not modified.

### With Feature 005 (Spec Pipeline)

**Pipeline integration**. The enhanced `TasksPhase` runs as the 7th phase in `PipelineOrchestrator`. It receives `input_artifacts` containing the rendered output of prior phases (plan.md, research.md, data-model.md). State is tracked via `pipeline_state.py` (pending → in-progress → complete).

---

## Complexity Tracking

> No constitution violations. All modules fit within 200-line class limits and 30-line function limits.
