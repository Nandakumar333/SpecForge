# Implementation Plan: Edge Case Analysis Engine

**Branch**: `007-edge-case-engine` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/007-edge-case-engine/spec.md`

## Summary

Build an architecture-aware edge case analysis engine that reads `manifest.json` service topology (dependencies, events, shared entities) and produces enriched `edge-cases.md` per service with YAML frontmatter for machine parseability. Microservice mode generates inter-service failure scenarios (service down, network partition, eventual consistency, distributed transactions, version skew, data ownership) derived from actual `communication[]` and `events[]` entries. Monolith mode produces standard categories only (concurrency, data boundaries, state machine, UI/UX, security, data migration). Each edge case includes a deterministic severity, affected services, an architectural pattern recommendation, and a test suggestion.

**Approach**: Declarative YAML pattern files define scenario templates per category. A `MicroserviceEdgeCaseAnalyzer` reads the communication map and instantiates those templates with real service names. An `ArchitectureEdgeCaseFilter` removes irrelevant categories. The existing `EdgecasePhase` is enhanced to delegate to the analyzer. A standalone CLI command follows the research_cmd.py pattern.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (output), Jinja2 3.x (template rendering), PyYAML (pattern file loading) — all existing
**Storage**: File system — `.specforge/features/<slug>/edge-cases.md`, YAML pattern files bundled in package
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)
**Target Platform**: Cross-platform CLI
**Project Type**: CLI tool (SpecForge)
**Performance Goals**: < 2 seconds for 5-service manifest (SC-004)
**Constraints**: ≤ 30-line functions, frozen dataclasses, Result[T] pattern, constructor injection
**Scale/Scope**: 6-12 standard categories, up to 30 edge cases per service

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md + plan.md exist before code |
| II. Architecture | ✅ PASS | Core logic in `core/`, CLI in `cli/`, templates in `templates/`. Jinja2 for all output |
| III. Code Quality | ✅ PASS | Frozen dataclasses, Result[T], constructor injection, ≤30-line functions, type hints everywhere |
| IV. Testing | ✅ PASS | TDD: test tasks precede impl tasks |
| V. Commit Strategy | ✅ PASS | One commit per task, conventional commits |
| VI. File Structure | ✅ PASS | New files in correct layers: `core/edge_case_*.py`, `cli/edge_cases_cmd.py`, `knowledge/` |
| VII. Governance | ✅ PASS | Constitution supersedes; no conflicts |

## Project Structure

### Documentation (this feature)

```text
specs/007-edge-case-engine/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── edge-cases-cmd.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── core/
│   ├── edge_case_models.py        # D1: Frozen dataclasses (EdgeCase, EdgeCaseCategory, EdgeCaseReport, EdgeCasePattern, SeverityMatrix)
│   ├── edge_case_analyzer.py      # D2: MicroserviceEdgeCaseAnalyzer — reads manifest topology, generates dependency-specific edge cases
│   ├── edge_case_filter.py        # D3: ArchitectureEdgeCaseFilter — removes irrelevant categories per architecture
│   ├── edge_case_budget.py        # D4: EdgeCaseBudget — enforces count formula 6+2N+E+2(F-1), cap 30
│   ├── edge_case_patterns.py      # D5: PatternLoader — loads YAML pattern files, caches, returns EdgeCasePattern tuples
│   ├── config.py                  # D6: New constants — EDGE_CASE_CATEGORIES, SEVERITY_MATRIX, STANDARD_CATEGORIES, MICROSERVICE_CATEGORIES
│   └── phases/
│       └── edgecase_phase.py      # D7: Enhanced — delegates to analyzer, passes enriched edge cases to template
├── cli/
│   └── edge_cases_cmd.py          # D8: Standalone CLI command `specforge edge-cases <target>`
├── knowledge/
│   └── edge_case_patterns/        # D9: Declarative YAML pattern files
│       ├── service_unavailability.yaml
│       ├── network_partition.yaml
│       ├── eventual_consistency.yaml
│       ├── distributed_transactions.yaml
│       ├── version_skew.yaml
│       ├── data_ownership.yaml
│       ├── interface_contract_violation.yaml
│       ├── concurrency.yaml
│       ├── data_boundary.yaml
│       ├── state_machine.yaml
│       ├── ui_ux.yaml
│       ├── security.yaml
│       └── data_migration.yaml
└── templates/
    └── base/features/
        └── edge-cases.md.j2       # D10: Enhanced template with YAML frontmatter per edge case

tests/
├── unit/
│   ├── test_edge_case_models.py
│   ├── test_edge_case_analyzer.py
│   ├── test_edge_case_filter.py
│   ├── test_edge_case_budget.py
│   └── test_edge_case_patterns.py
├── integration/
│   └── test_edge_cases_cmd.py
└── snapshots/
    └── test_edge_cases_template.py
```

**Structure Decision**: All new modules follow existing Clean Architecture boundaries. `knowledge/` is a new package for declarative data files (YAML patterns) — analogous to how `templates/` holds `.md.j2` files. Core logic has zero dependency on YAML loading details (PatternLoader returns frozen dataclasses).

## Design Decisions

### D1: Edge Case Data Model

```text
EdgeCase (frozen dataclass)
├── id: str                       # "EC-001"
├── category: EdgeCaseCategory    # Literal union of all categories
├── severity: Severity            # Literal["critical", "high", "medium", "low"]
├── scenario: str                 # Human-readable scenario description
├── affected_services: tuple[str, ...]  # ["ledger-service", "identity-service"]
├── handling_strategy: str        # "circuit breaker with fallback cache"
├── test_suggestion: str          # "Integration test: stub identity-service returning 503"
├── trigger: str                  # "identity-service returns 503 during token validation"

EdgeCaseReport (frozen dataclass)
├── service_slug: str
├── architecture: str
├── edge_cases: tuple[EdgeCase, ...]
├── total_count: int

EdgeCasePattern (frozen dataclass) — loaded from YAML
├── category: str
├── scenario_template: str        # "{{target_service}} unavailable during {{operation}}"
├── trigger_template: str
├── handling_strategies: tuple[str, ...]  # ["circuit_breaker", "retry_with_backoff"]
├── severity_microservice: str | None
├── severity_monolith: str | None
├── test_template: str
├── applicable_patterns: tuple[str, ...]  # ["sync-rest", "sync-grpc"] — which communication patterns this applies to
```

### D2: MicroserviceEdgeCaseAnalyzer

The KEY component. Constructor-injected with `ServiceContext` and `tuple[EdgeCasePattern, ...]`.

```text
analyze(service_ctx) -> EdgeCaseReport:
  1. Generate standard-category edge cases (1 per category from patterns)
  2. For each communication[] dependency:
     - Instantiate service_unavailability pattern with real target name
     - Instantiate network_partition if async pattern
     - Assign severity from SeverityMatrix(required, pattern)
  3. For each events[] where service is producer:
     - Instantiate eventual_consistency for each consumer
     - Instantiate distributed_transactions if multiple consumers
  4. For shared entities (via BoundaryAnalyzer):
     - Instantiate data_ownership pattern per shared entity
  5. Apply budget cap (EdgeCaseBudget)
  6. Number sequentially (EC-001, EC-002, ...)
  7. Return EdgeCaseReport
```

### D3: ArchitectureEdgeCaseFilter

```text
filter(patterns, architecture) -> tuple[EdgeCasePattern, ...]:
  - monolithic: keep only patterns whose category is in STANDARD_EDGE_CASE_CATEGORIES
  - microservice: keep all patterns
  - modular-monolith: keep monolith set + patterns whose category is "interface_contract_violation"
  - unknown architecture: fall back to monolithic behavior + emit warning via warnings.warn()
```

### D4: EdgeCaseBudget

```text
allocate(deps_count, events_count, features_count) -> int:
  budget = 6 + (2 * deps_count) + events_count + (2 * max(0, features_count - 1))
  return min(budget, 30)

prioritize(cases, budget) -> tuple[EdgeCase, ...]:
  Sort by severity (critical > high > medium > low), then category priority
  Return first `budget` cases
```

### D5: PatternLoader

```text
load(package_dir) -> tuple[EdgeCasePattern, ...]:
  1. Scan knowledge/edge_case_patterns/*.yaml
  2. Parse each YAML file into EdgeCasePattern dataclass
  3. Cache result (immutable after load)
  4. Return frozen tuple
```

Uses `importlib.resources` to locate bundled YAML files within the package.

### D6: Config Constants

```python
# Edge Case Analysis Engine Constants (Feature 007)
EDGE_CASE_MAX_PER_SERVICE: int = 30

STANDARD_EDGE_CASE_CATEGORIES: tuple[str, ...] = (
    "concurrency", "data_boundary", "state_machine",
    "ui_ux", "security", "data_migration",
)

MICROSERVICE_EDGE_CASE_CATEGORIES: tuple[str, ...] = (
    "service_unavailability", "network_partition",
    "eventual_consistency", "distributed_transaction",
    "version_skew", "data_ownership",
)

MODULAR_MONOLITH_EXTRA_CATEGORIES: tuple[str, ...] = (
    "interface_contract_violation",
)

# Deterministic severity matrix: (required, pattern) -> severity
SEVERITY_MATRIX_MICROSERVICE: dict[tuple[bool, str], str] = {
    (True, "sync-rest"): "critical",
    (True, "sync-grpc"): "critical",
    (True, "async-event"): "high",
    (False, "sync-rest"): "high",
    (False, "sync-grpc"): "high",
    (False, "async-event"): "medium",
}

SEVERITY_MATRIX_MONOLITH: dict[str, str] = {
    "security": "high",
    "concurrency": "high",
    "data_boundary": "medium",
    "state_machine": "medium",
    "ui_ux": "low",
    "data_migration": "low",
}

EDGE_CASE_CATEGORY_PRIORITY: dict[str, int] = {
    "service_unavailability": 1,
    "distributed_transaction": 2,
    "network_partition": 3,
    "eventual_consistency": 4,
    "data_ownership": 5,
    "version_skew": 6,
    "interface_contract_violation": 7,
    "security": 8,
    "concurrency": 9,
    "data_boundary": 10,
    "state_machine": 11,
    "ui_ux": 12,
    "data_migration": 13,
}
```

### D7: Enhanced EdgecasePhase

The existing `_build_context()` currently passes only `adapter.get_edge_case_extras()`. Enhancement:

```text
_build_context(service_ctx, adapter, input_artifacts):
  1. Load YAML patterns via PatternLoader
  2. Filter by architecture via ArchitectureEdgeCaseFilter
  3. Run MicroserviceEdgeCaseAnalyzer (or standard analyzer for monolith)
  4. Build enriched context with EdgeCaseReport data
  5. Pass both adapter_edge_cases (for backward compat) AND enriched edge_cases list
```

### D8: CLI Command (edge_cases_cmd.py)

Follows `research_cmd.py` pattern exactly:
1. `resolve_target(target, project_root)` → slug
2. `load_service_context(slug, project_root)` → ServiceContext
3. `acquire_lock(lock_path, slug)` — pipeline lock
4. Load patterns → filter → analyze → generate EdgeCaseReport
5. Render via `TemplateRenderer.render("edge-cases", TemplateType.feature, context)`
6. Update pipeline state: `mark_complete(state, "edgecase", (str(path),))`
7. `release_lock(lock_path)`

### D9: YAML Pattern File Format

```yaml
# service_unavailability.yaml
category: service_unavailability
scenarios:
  - scenario_template: "{{target_service}} is unavailable when {{source_service}} attempts {{operation}}"
    trigger_template: "{{target_service}} returns 503 or connection refused"
    handling_strategies:
      - circuit_breaker
      - retry_with_backoff
      - fallback_cache
    severity_microservice: null  # Derived from SeverityMatrix at runtime
    severity_monolith: null      # Not applicable
    test_template: "Integration test: stub {{target_service}} returning 503, verify {{source_service}} degrades gracefully"
    applicable_patterns:
      - sync-rest
      - sync-grpc
  - scenario_template: "{{target_service}} responds with degraded data when {{source_service}} calls {{operation}}"
    trigger_template: "{{target_service}} returns partial response or timeout"
    handling_strategies:
      - bulkhead
      - timeout_with_fallback
    severity_microservice: null
    severity_monolith: null
    test_template: "Integration test: inject 5s delay on {{target_service}}, verify {{source_service}} uses fallback"
    applicable_patterns:
      - sync-rest
      - sync-grpc
```

Severity is `null` in YAML because it's determined at runtime by the `SeverityMatrix` using the `required` flag and `pattern` from `communication[]`.

**Pattern-to-Category Mapping** (which communication patterns trigger which categories):

| Category | Applicable Patterns | Notes |
|----------|-------------------|-------|
| service_unavailability | sync-rest, sync-grpc | Sync deps can fail with 503/timeout |
| network_partition | async-event | Async messaging can lose/delay messages |
| eventual_consistency | async-event | Consumer data lags behind producer |
| distributed_transaction | async-event | Multi-consumer coordination failures |
| version_skew | sync-rest, sync-grpc, async-event | API/schema changes affect all patterns |
| data_ownership | (none — derived from BoundaryAnalyzer) | Triggered by shared entities, not patterns |
| interface_contract_violation | (none — module boundary) | Modular-monolith only |
| concurrency–data_migration | (none — standard categories) | All architectures, pattern-independent |

### D10: Enhanced Template

The `edge-cases.md.j2` template is enhanced to:
- Render YAML frontmatter blocks per edge case (fenced ```` ```yaml ``` ```` blocks)
- Use the enriched `edge_cases` list (not just `adapter_edge_cases`)
- Fall back to existing behavior if `edge_cases` is empty (backward compat)

## Integration Points

| Component | Integrates With | Direction |
|-----------|----------------|-----------|
| `edge_case_analyzer.py` | `service_context.py` (ServiceContext, ServiceDependency, EventInfo) | reads |
| `edge_case_analyzer.py` | `boundary_analyzer.py` (shared entity detection) | reads |
| `edge_case_filter.py` | `architecture_adapter.py` (architecture type) | reads |
| `edge_case_patterns.py` | `knowledge/edge_case_patterns/*.yaml` | loads |
| `edgecase_phase.py` | `edge_case_analyzer.py`, `edge_case_filter.py`, `edge_case_patterns.py` | orchestrates |
| `edge_cases_cmd.py` | `pipeline_state.py`, `pipeline_lock.py`, `template_renderer.py` | reads/writes |
| `edge-cases.md.j2` | `edge_case_models.EdgeCaseReport` (via context dict) | renders |
| config.py | All edge case modules | constants |

## Complexity Tracking

No constitution violations expected. All modules stay within 200-line / 30-line-function limits.

| Risk | Mitigation |
|------|-----------|
| YAML pattern loading adds PyYAML dependency | PyYAML is already in the dependency tree (transitive). Use `importlib.resources` for bundled files |
| Template enhancement could break existing snapshots | Backward-compatible: only render enriched output when `edge_cases` context key is present |
| Budget cap truncation loses important edge cases | Prioritize by severity × category priority before truncation |
