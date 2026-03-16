# Implementation Plan: Spec Generation Pipeline

**Branch**: `005-spec-generation-pipeline` | **Date**: 2026-03-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-spec-generation-pipeline/spec.md`

## Summary

Build a 6-phase pipeline that generates 7 specification artifacts per service/module, reading Feature 004's manifest.json to scope content to service boundaries. The pipeline uses an ArchitectureAdapter pattern (microservice/monolith/modular-monolith) to inject architecture-specific sections into Jinja2 templates, tracks phase completion in `.pipeline-state.json`, and supports concurrent execution across different services via atomic lock files.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering) — all existing
**Storage**: File system — `.specforge/features/<slug>/` directories with JSON state files
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting) — all existing
**Target Platform**: Cross-platform (Windows + Linux + macOS)
**Project Type**: CLI tool (extending existing `specforge` command)
**Performance Goals**: Full pipeline for a 5-feature service completes in under 60 seconds (SC-001)
**Constraints**: No new external dependencies in core (Clean Architecture). Cross-platform file locking (no `fcntl`).
**Scale/Scope**: Typical project has 3-8 services, each with 1-5 features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | PASS | spec.md, plan.md, tasks.md created before implementation |
| II. Architecture | PASS | All output via Jinja2 templates. Core has zero external deps. Plugin-compatible adapter pattern. |
| III. Code Quality | PASS | Type hints required. 30-line functions, 200-line classes. Result[T] for errors. Constructor injection. Constants in config.py. |
| IV. Testing | PASS | TDD enforced. Unit tests for all core modules. Integration tests for CLI. Snapshot tests for template output. |
| V. Commit Strategy | PASS | Conventional commits, one per task. |
| VI. File Structure | PASS | New modules in core/, phases/ subpackage, CLI commands in cli/, templates in templates/. |
| VII. Governance | PASS | Constitution takes precedence over all other docs. |

**Gate result**: ALL PASS. No violations to track.

## Project Structure

### Documentation (this feature)

```text
specs/005-spec-generation-pipeline/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entity definitions
├── contracts/
│   └── cli-contract.md  # CLI command signatures and output formats
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── main.py                    # MODIFIED — register new commands
│   ├── specify_cmd.py             # NEW — specforge specify <target>
│   └── pipeline_status_cmd.py     # NEW — specforge pipeline-status [target]
├── core/
│   ├── config.py                  # MODIFIED — add pipeline constants
│   ├── service_context.py         # NEW — ServiceContext + FeatureInfo + ServiceDependency + EventInfo
│   ├── pipeline_state.py          # NEW — PipelineState + PhaseStatus + save/load/lock
│   ├── pipeline_lock.py           # NEW — PipelineLock acquire/release with atomic O_EXCL
│   ├── spec_pipeline.py           # NEW — PipelineOrchestrator (main entry point)
│   ├── architecture_adapter.py    # NEW — ArchitectureAdapter protocol + 3 implementations
│   └── phases/
│       ├── __init__.py            # NEW — phase registry + PhaseDefinition
│       ├── base_phase.py          # NEW — BasePhase with run() template method
│       ├── specify_phase.py       # NEW — Phase 1: generate spec.md
│       ├── research_phase.py      # NEW — Phase 2: generate research.md
│       ├── datamodel_phase.py     # NEW — Phase 3a: generate data-model.md
│       ├── edgecase_phase.py      # NEW — Phase 3b: generate edge-cases.md
│       ├── plan_phase.py          # NEW — Phase 4: generate plan.md
│       ├── checklist_phase.py     # NEW — Phase 5: generate checklist.md
│       └── tasks_phase.py         # NEW — Phase 6: generate tasks.md
├── templates/base/features/
│   ├── spec.md.j2                 # MODIFIED — add service context blocks
│   ├── research.md.j2             # MODIFIED — add service context blocks
│   ├── datamodel.md.j2            # MODIFIED — add entity loops + arch conditionals
│   ├── plan.md.j2                 # MODIFIED — add adapter section loops + arch conditionals
│   ├── checklist.md.j2            # MODIFIED — add adapter checklist items
│   ├── edge-cases.md.j2           # MODIFIED — add adapter edge case loops
│   └── tasks.md.j2                # MODIFIED — add adapter task loops

tests/
├── unit/
│   ├── test_service_context.py    # NEW — ServiceContext loading + feature number resolution
│   ├── test_pipeline_state.py     # NEW — state save/load/transitions + interrupted recovery
│   ├── test_pipeline_lock.py      # NEW — lock acquire/release/stale detection
│   ├── test_spec_pipeline.py      # NEW — orchestrator phase ordering + skip logic
│   ├── test_architecture_adapter.py  # NEW — 3 adapters produce correct context
│   ├── test_phases/
│   │   ├── test_base_phase.py     # NEW — base phase template method
│   │   ├── test_specify_phase.py  # NEW — spec generation with multi-feature services
│   │   ├── test_datamodel_phase.py # NEW — data model scoping by architecture
│   │   ├── test_edgecase_phase.py # NEW — edge case generation with arch extras
│   │   ├── test_plan_phase.py     # NEW — plan generation with arch sections
│   │   └── test_tasks_phase.py    # NEW — task generation with arch extras
│   └── ...
├── integration/
│   ├── test_pipeline_microservice.py      # NEW — full pipeline E2E for microservice arch
│   ├── test_pipeline_monolith.py          # NEW — full pipeline E2E for monolith arch
│   ├── test_pipeline_modular_monolith.py  # NEW — full pipeline E2E for modular-monolith arch
│   ├── test_pipeline_single_feature.py    # NEW — single-feature service E2E
│   └── test_pipeline_resume.py            # NEW — interrupt + resume scenarios
└── snapshots/
    ├── spec_microservice.md               # NEW — golden file for microservice spec
    ├── spec_monolith.md                   # NEW — golden file for monolith spec
    ├── spec_modular_monolith.md           # NEW — golden file for modular-monolith spec
    ├── plan_microservice.md               # NEW — golden file for microservice plan
    ├── plan_monolith.md                   # NEW — golden file for monolith plan
    ├── plan_modular_monolith.md           # NEW — golden file for modular-monolith plan
    └── datamodel_modular_monolith.md      # NEW — golden file for modular-monolith data model
```

**Structure Decision**: Extends the existing single-project structure. New `phases/` subpackage under `core/` groups phase runners to keep the core directory manageable (7 phase files + base + init = 9 files). Lock logic is a separate module from state logic because their concerns differ (atomicity via O_EXCL vs. JSON persistence). Architecture adapter is a single file with Protocol + 3 small implementations (each ~40 lines, well within 200-line class limit).

## Implementation Phases

### Phase 1: Foundation — Config, Data Models, State Management

**Files**: config.py (modified), service_context.py, pipeline_state.py, pipeline_lock.py

1. Add pipeline constants to `config.py`: PIPELINE_STATE_FILENAME, PIPELINE_LOCK_FILENAME, LOCK_STALE_THRESHOLD_MINUTES, PIPELINE_PHASE_STATUSES, PIPELINE_PHASES, SHARED_ENTITIES_PATH, CONTRACTS_DIR, STUB_CONTRACT_SUFFIX
2. Implement `ServiceContext` frozen dataclass with `load_from_manifest()` class method that reads manifest.json, resolves target service, filters features, extracts dependencies
3. Implement `FeatureInfo`, `ServiceDependency`, `EventInfo` frozen dataclasses
4. Implement feature number resolution: `resolve_target()` function that accepts slug or numeric ID and returns service slug
5. Implement `PipelineState` and `PhaseStatus` frozen dataclasses with `save_state()`, `load_state()`, `create_initial_state()` functions (following decomposition_state.py pattern)
6. Implement state transition helpers: `mark_in_progress()`, `mark_complete()`, `mark_failed()`, `is_phase_complete()`, `get_next_phase()`, `detect_interrupted()`
7. Implement `PipelineLock` with `acquire_lock()` (atomic O_CREAT|O_EXCL), `release_lock()`, `is_stale()` functions

**Key design decisions**:
- `resolve_target()` returns `Result[ServiceContext]` — Err if not found
- State transitions return new frozen PipelineState (immutable)
- Lock file uses `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)` for atomicity
- All I/O functions return `Result[T]`

### Phase 2: Architecture Adapters

**Files**: architecture_adapter.py

1. Define `ArchitectureAdapter` Protocol with 7 methods: `get_context()`, `get_datamodel_context()`, `get_research_extras()`, `get_plan_sections()`, `get_task_extras()`, `get_edge_case_extras()`, `get_checklist_extras()`
2. Implement `MicroserviceAdapter`:
   - `get_context()`: adds `dependencies`, `communication_patterns`, `events` to template vars
   - `get_datamodel_context()`: returns `{"entity_scope": "isolated", "cross_service_ref": "api_contract", "shared_entities": False}`
   - `get_research_extras()`: returns service mesh evaluation, API versioning strategy, distributed tracing questions
   - `get_plan_sections()`: returns sections for containerization, health checks, service registration, circuit breakers, API gateway
   - `get_task_extras()`: returns container build, service registration, contract test tasks
   - `get_edge_case_extras()`: returns service-down, network partition, eventual consistency, timeout scenarios
   - `get_checklist_extras()`: returns API contract validation, deployment readiness items
3. Implement `MonolithAdapter`:
   - `get_context()`: adds `module_context`, `shared_infrastructure` to template vars
   - `get_datamodel_context()`: returns `{"entity_scope": "module", "cross_service_ref": "shared_table", "shared_entities": True}`
   - `get_research_extras()`: returns shared resource contention, module dependency analysis questions
   - `get_plan_sections()`: returns shared DB, shared auth middleware sections
   - `get_task_extras()`: simplified (no Docker, no service discovery)
   - `get_edge_case_extras()`: module boundary violations, shared resource contention
   - `get_checklist_extras()`: module isolation verification
4. Implement `ModularMonolithAdapter` (extends MonolithAdapter):
   - Inherits monolith behavior
   - `get_datamodel_context()`: returns `{"entity_scope": "strict_module", "cross_service_ref": "interface_contract", "shared_entities": True, "no_cross_module_db": True}`
   - `get_research_extras()`: inherits monolith + adds module boundary enforcement strategy, interface versioning questions
   - `get_plan_sections()`: adds module boundary enforcement rules
   - `get_edge_case_extras()`: adds interface contract violations
   - `get_checklist_extras()`: adds no cross-module direct DB access check
5. Factory function: `create_adapter(architecture: str) -> ArchitectureAdapter`

### Phase 3: Phase Runners

**Files**: phases/__init__.py, phases/base_phase.py, phases/specify_phase.py through tasks_phase.py

1. `PhaseDefinition` frozen dataclass in `__init__.py` with name, number, template_name, artifact_filename, prerequisites, parallel_with
2. Phase registry: `PHASE_DEFINITIONS` tuple of all 7 PhaseDefinition instances
3. `BasePhase` class with template method pattern:
   - `run(service_ctx, adapter, state, renderer, registry) -> Result[Path]`
   - Steps: validate prerequisites → build context → render template → write artifact
   - `_build_context()` abstract method — each subclass provides phase-specific context
   - `_post_render()` hook — optional post-processing (e.g., datamodel phase creates shared_entities.md)
4. Phase implementations (each ~30-60 lines):
   - `SpecifyPhase`: groups features by category into "domain capabilities", adds service deps if microservice
   - `ResearchPhase`: uses spec.md content as input context, adds adapter research extras via `get_research_extras()`
   - `DatamodelPhase`: builds entity list scoped to service via `get_datamodel_context()`, creates shared_entities.md for monolith, creates API contract references for microservice
   - `EdgecasePhase`: builds base edge cases + adapter extras
   - `PlanPhase`: uses spec + research + datamodel as input, injects prompt context (FR-063/064), adds adapter plan sections
   - `ChecklistPhase`: validates previous artifacts, adds adapter checklist items
   - `TasksPhase`: builds ordered task list + adapter task extras

### Phase 4: Pipeline Orchestrator

**Files**: spec_pipeline.py

1. `PipelineOrchestrator` class with constructor injection:
   - Dependencies: `TemplateRegistry`, `TemplateRenderer`, `PromptContextBuilder`
   - Method: `run(target: str, project_root: Path, force: bool, from_phase: str | None) -> Result`
2. Orchestration flow:
   - Load manifest.json → resolve target → build ServiceContext
   - Create adapter via factory
   - Acquire lock (or fail with lock error)
   - Load or create PipelineState
   - If `force`: reset all phases to pending
   - If `from_phase`: validate prerequisites, start from that phase
   - Detect interrupted phases → reset to pending
   - Execute phases in order, skip completed ones
   - Phase 3: use ThreadPoolExecutor for parallel datamodel + edgecase
   - After each phase: update state, save to disk
   - Release lock in finally block
3. Error handling: if any phase fails, save state (marking failed phase), release lock, return Err with phase name and error
4. Stub contract generation: during plan phase, if dependent service has no contracts/ dir, generate stub contract

### Phase 5: CLI Integration

**Files**: specify_cmd.py, pipeline_status_cmd.py, main.py (modified)

1. `specify_cmd.py` — Click command:
   - `@click.command("specify")`
   - `@click.argument("target")`
   - `@click.option("--force", is_flag=True)`
   - `@click.option("--from", "from_phase", type=click.Choice(PIPELINE_PHASES))`
   - Rich console output: progress per phase with timing
   - Delegates to PipelineOrchestrator
2. `pipeline_status_cmd.py` — Click command:
   - `@click.command("pipeline-status")`
   - `@click.argument("target", required=False)`
   - Rich table output showing phase status per service
3. Register both commands in `main.py` via `cli.add_command()`

### Phase 6: Template Enhancement

**Files**: all 7 feature templates in templates/base/features/

1. Enhance `spec.md.j2`:
   - Add `{% if service %}` block for service-scoped spec generation
   - Add `{% for capability in capabilities %}` loop for domain-grouped user stories
   - Add `{% if architecture == 'microservice' %}` for Service Dependencies section
   - Add `{% if architecture == 'modular-monolith' %}` for Module Interface Contract section
   - Preserve backward compatibility (templates still work without service context)
2. Enhance `research.md.j2`:
   - Add `{% for question in adapter_research_extras %}` loop for architecture-specific research questions
   - Microservice: service mesh, API versioning, distributed tracing questions
   - Modular-monolith: module boundary enforcement strategy, interface versioning questions
3. Enhance `datamodel.md.j2`:
   - Add `{% for entity in entities %}` loop for service-scoped entities
   - Add `{% if architecture == 'microservice' %}` for API contract references (no cross-service tables)
   - Add `{% if architecture == 'modular-monolith' %}` for strict module boundary constraints and `no_cross_module_db` warning
   - Add `{% if architecture in ['monolithic', 'modular-monolith'] %}` for shared_entities.md references
4. Enhance `plan.md.j2`:
   - Add `{% for section in adapter_sections %}` loop
   - Add `{% if architecture == 'microservice' %}` for deployment concerns
   - Add `{% if architecture == 'modular-monolith' %}` for module boundary enforcement rules
5. Enhance `edge-cases.md.j2`:
   - Add `{% for ec in adapter_edge_cases %}` loop for architecture extras
   - Add `{% if architecture == 'modular-monolith' %}` for interface contract violation scenarios (distinct from monolith boundary violations)
6. Enhance `checklist.md.j2`:
   - Add `{% for item in adapter_checklist %}` loop
   - Add `{% if architecture == 'modular-monolith' %}` for cross-module DB access verification
7. Enhance `tasks.md.j2`:
   - Add `{% for task in adapter_tasks %}` loop
   - Architecture-specific tasks injected via adapter

All templates use three-way architecture conditionals where behavior differs:
- `{% if architecture == 'microservice' %}` — deployment, contracts, distributed concerns
- `{% if architecture == 'modular-monolith' %}` — strict boundaries, interface contracts, no cross-module DB
- `{% if architecture == 'monolithic' %}` or `{% else %}` — shared infrastructure, module isolation

### Phase 7: Integration Testing + Snapshots

**Files**: test_pipeline_microservice.py, test_pipeline_monolith.py, test_pipeline_resume.py, snapshot golden files

1. Integration test: full microservice pipeline with mock manifest (2 services, 3+2 features)
2. Integration test: full monolith pipeline with mock manifest (3 modules)
3. Integration test: full modular-monolith pipeline with mock manifest (3 modules, 2+1+2 features) — verifies interfaces.md, strict boundary constraints, no cross-module DB checks, interface contract violation edge cases
4. Integration test: single-feature service pipeline (1 service, 1 feature) — verifies no sub-sections in spec.md, minimal data model
5. Integration test: pipeline resume after interrupt (delete artifact mid-pipeline)
6. Integration test: concurrent lock detection
7. Integration test: feature number resolution
8. Snapshot golden files for all 3 architectures: microservice, monolith, and modular-monolith spec/plan/datamodel output

## Integration Points

### Feature 004 → Feature 005 (manifest.json)

Feature 005 reads Feature 004's manifest.json output. The manifest schema (from Feature 004's manifest-schema contract) provides:
- `architecture` field → determines which ArchitectureAdapter to use
- `services[].slug` → target resolution
- `services[].features[]` → feature scoping
- `services[].communication[]` → dependency extraction
- `features[].id` → feature number resolution
- `features[].service` → reverse lookup (feature → service)

### Feature 002 → Feature 005 (TemplateRenderer)

Pipeline phases render artifacts via `TemplateRenderer.render()`, passing ServiceContext-derived variables as template context. Template resolution uses the existing 4-step chain (user override → built-in). New template context variables: `service`, `architecture`, `features`, `dependencies`, `capabilities`, `entities`, `adapter_sections`, `adapter_tasks`, `adapter_edge_cases`, `adapter_checklist`.

### Feature 003 → Feature 005 (PromptContextBuilder)

Plan phase (Phase 4) uses `PromptContextBuilder.build()` to inject governance prompt content into the plan template context. The `task_domain` parameter is set based on the service's primary feature category.

## Testing Strategy

| Layer | Count | What's Tested |
|-------|-------|---------------|
| Unit | ~50 tests | ServiceContext loading, state transitions, lock acquire/release, adapter output (all 3 architectures incl. `get_datamodel_context()` and `get_research_extras()`), each phase's context building |
| Integration | ~20 tests | Full pipeline E2E for all 3 architectures + single-feature service, CLI commands with CliRunner, resume from interrupt, concurrent locks, feature number resolution |
| Snapshot | ~12 tests | Template output for microservice/monolith/modular-monolith spec, plan, datamodel, edge-cases |

**TDD order**: Tests before implementation for every module (Constitution Principle IV).

**Test fixtures**:
- `_mock_manifest()` — returns a dict matching Feature 004's manifest schema with 2 services (identity + ledger), microservice architecture
- `_mock_manifest_monolith()` — same but monolithic, features as modules
- `_mock_manifest_modular_monolith()` — modular-monolith with 3 modules (auth, payments, reporting) with 2+1+2 features, strict module boundaries
- `_mock_manifest_single_feature()` — microservice with 1 service containing 1 feature (tests minimal path)
- `_mock_service_context()` — pre-built ServiceContext for ledger-service
