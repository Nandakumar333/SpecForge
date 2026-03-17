# Data Model: Edge Case Analysis Engine

**Feature**: 007-edge-case-engine
**Date**: 2026-03-17

## Entities

### EdgeCase

Represents a single generated edge case with all metadata for both human reading and machine parsing.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Sequential ID in EC-NNN format (e.g., "EC-001") |
| category | EdgeCaseCategory | Category literal (e.g., "service_unavailability", "concurrency") |
| severity | Severity | One of: "critical", "high", "medium", "low" |
| scenario | str | Human-readable scenario description |
| trigger | str | What causes this edge case to manifest |
| affected_services | tuple[str, ...] | Service slugs involved (e.g., ("ledger-service", "identity-service")) |
| handling_strategy | str | Recommended architectural pattern (e.g., "circuit breaker with fallback cache") |
| test_suggestion | str | How to verify correct handling (e.g., "Stub identity-service returning 503") |

**Immutability**: Frozen dataclass. Created once by the analyzer, never mutated.

### EdgeCasePattern

Loaded from YAML pattern files. Defines a scenario template that gets instantiated with real service names.

| Field | Type | Description |
|-------|------|-------------|
| category | str | Pattern category (e.g., "service_unavailability") |
| scenario_template | str | Jinja2-style template: "{{target_service}} unavailable during {{operation}}" |
| trigger_template | str | Template: "{{target_service}} returns 503 or connection refused" |
| handling_strategies | tuple[str, ...] | Architectural patterns: ("circuit_breaker", "retry_with_backoff") |
| severity_microservice | str or None | None means "derive from SeverityMatrix at runtime" |
| severity_monolith | str or None | None means "not applicable for this architecture" |
| test_template | str | Template: "Stub {{target_service}}, verify graceful degradation" |
| applicable_patterns | tuple[str, ...] | Communication patterns this applies to: ("sync-rest", "sync-grpc") |

**Immutability**: Frozen dataclass. Loaded once from YAML, cached.

### EdgeCaseReport

Aggregate container for all edge cases generated for a service.

| Field | Type | Description |
|-------|------|-------------|
| service_slug | str | Target service (e.g., "ledger-service") |
| architecture | str | Architecture type from manifest |
| edge_cases | tuple[EdgeCase, ...] | All generated edge cases, ordered by severity then category |
| total_count | int | Number of edge cases (for summary output) |

**Immutability**: Frozen dataclass. Produced by analyzer, consumed by template.

### SeverityMatrix

Deterministic severity lookup.

| Field | Type | Description |
|-------|------|-------------|
| microservice_rules | dict[tuple[bool, str], str] | (required, pattern) → severity |
| monolith_rules | dict[str, str] | category → severity |

**Not a dataclass** — implemented as module-level constants in config.py since it's static data.

## Relationships

```text
EdgeCasePattern (YAML files)
  ↓ loaded by PatternLoader
  ↓ filtered by ArchitectureEdgeCaseFilter
  ↓ instantiated by MicroserviceEdgeCaseAnalyzer
  ↓
EdgeCase (one per scenario × dependency)
  ↓ collected into
  ↓
EdgeCaseReport (one per service)
  ↓ rendered by
  ↓
edge-cases.md (via edge-cases.md.j2 template)
```

## State Transitions

EdgeCase entities are stateless — they are generated, rendered, and discarded. No persistence beyond the markdown output. Pipeline state tracks phase completion only (`pending` → `in-progress` → `complete`/`failed`).

## Validation Rules

- `id` must match pattern `EC-\d{3}`
- `severity` must be one of the four valid levels
- `category` must be in `STANDARD_EDGE_CASE_CATEGORIES ∪ MICROSERVICE_EDGE_CASE_CATEGORIES`
- `affected_services` must be non-empty
- `total_count` must equal `len(edge_cases)`
- `total_count` must not exceed `EDGE_CASE_MAX_PER_SERVICE` (30)
