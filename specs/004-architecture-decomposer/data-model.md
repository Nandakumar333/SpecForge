# Data Model: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Feature**: 004-architecture-decomposer
**Date**: 2026-03-15

## Entities

### 1. ArchitectureType (Enum)

**Location**: `src/specforge/core/config.py`

| Value | Description |
|-------|-------------|
| `monolithic` | Single deployable unit, features as modules |
| `microservice` | Independent services per bounded context |
| `modular-monolith` | Single deployable, strict module boundaries |

**Validation**: Must be one of the three values. CLI `--arch` flag validates against this enum.

---

### 2. DomainPattern (TypedDict / dict)

**Location**: `src/specforge/core/domain_patterns.py`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Domain name (e.g., "finance", "ecommerce") |
| `keywords` | `list[tuple[str, int]]` | `(keyword, weight)` tuples, weight 1–3 |
| `features` | `list[FeatureTemplate]` | Domain-specific feature templates |

**Constraints**:
- Each domain has 8–15 feature templates (FR-004)
- Keywords have weights 1–3 (FR-049)
- 6 built-in domains + 1 generic fallback (FR-038)

---

### 3. FeatureTemplate (TypedDict / dict)

**Location**: `src/specforge/core/domain_patterns.py` (nested in DomainPattern)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Feature name (e.g., "authentication") |
| `description` | `str` | One-line description |
| `category` | `str` | One of: `foundation`, `core`, `supporting`, `integration`, `admin` |
| `priority` | `str` | One of: `P0`, `P1`, `P2`, `P3` |
| `always_separate` | `bool` | If True, always becomes its own service (FR-015) |
| `data_keywords` | `list[str]` | Entity/data keywords for affinity scoring |

**Constraints**:
- `always_separate=True` for: auth/identity, notification, external integration, frontend (FR-015)
- Priority derived from category: foundation→P0, core→P1, supporting→P2, integration/admin→P2-P3

---

### 4. Feature (frozen dataclass)

**Location**: `src/specforge/core/domain_analyzer.py`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Sequential ID: "001", "002", ... |
| `name` | `str` | Kebab-case name (e.g., "authentication") |
| `display_name` | `str` | Human-readable name (e.g., "Authentication & User Management") |
| `description` | `str` | One-line description |
| `priority` | `str` | `P0` \| `P1` \| `P2` \| `P3` |
| `category` | `str` | `foundation` \| `core` \| `supporting` \| `integration` \| `admin` |
| `always_separate` | `bool` | Whether this feature must be a standalone service |
| `data_keywords` | `tuple[str, ...]` | Immutable tuple of entity/data keywords |

**Validation**:
- `id` is zero-padded 3-digit string
- `name` matches `^[a-z][a-z0-9-]*$`
- `priority` is one of P0–P3
- `category` is one of the 5 valid values

---

### 5. Service (frozen dataclass)

**Location**: `src/specforge/core/service_mapper.py`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Display name (e.g., "Ledger Service") |
| `slug` | `str` | Kebab-case directory name (e.g., "ledger-service") |
| `feature_ids` | `tuple[str, ...]` | IDs of features in this service |
| `rationale` | `str` | WHY COMBINED or WHY SEPARATE explanation |
| `communication` | `tuple[CommunicationLink, ...]` | Links to other services |

**Validation**:
- `slug` matches `^[a-z][a-z0-9-]*$`
- `feature_ids` has 1–4 entries (FR-050 max cap)
- Every feature ID must exist in the feature list
- No feature ID appears in more than one service (FR-022)

**Note on Module entity**: The spec defines "Module" as a Key Entity for monolithic architecture. In the data model, a Module is represented as a Service with a single entry containing all feature IDs. There is no separate Module dataclass — the Service entity serves both purposes, distinguished by the manifest's `architecture` field.

---

### 6. CommunicationLink (frozen dataclass)

**Location**: `src/specforge/core/communication_planner.py`

| Field | Type | Description |
|-------|------|-------------|
| `target` | `str` | Target service slug |
| `pattern` | `str` | `sync-rest` \| `sync-grpc` \| `async-event` |
| `required` | `bool` | True = solid arrow, False = dashed arrow in Mermaid (FR-051) |
| `description` | `str` | Purpose of this connection |

**Validation**:
- `target` must reference an existing service slug
- `pattern` must be one of 3 valid values

---

### 7. Event (frozen dataclass)

**Location**: `src/specforge/core/communication_planner.py`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Event name, pattern: `{producer}.{entity}.{action}` (FR-052) |
| `producer` | `str` | Producer service slug |
| `consumers` | `tuple[str, ...]` | Consumer service slugs |
| `payload_summary` | `str` | Brief description of event data |

**Validation**:
- `name` matches `^[a-z-]+\.[a-z-]+\.[a-z-]+$`
- `producer` must reference an existing service slug
- All `consumers` must reference existing service slugs

---

### 8. DecompositionState (frozen dataclass)

**Location**: `src/specforge/core/decomposition_state.py`

| Field | Type | Description |
|-------|------|-------------|
| `step` | `str` | Current step: `architecture` \| `decomposition` \| `mapping` \| `review` \| `complete` |
| `architecture` | `str \| None` | Selected architecture type or None |
| `project_description` | `str` | Original user input |
| `domain` | `str \| None` | Matched domain name or None |
| `features` | `tuple[Feature, ...]` | Decomposed features (empty if not yet decomposed) |
| `services` | `tuple[Service, ...]` | Mapped services (empty if not yet mapped) |
| `timestamp` | `str` | ISO-8601 UTC of last update |

**State Transitions**:
```
architecture: architecture set, features/services empty
decomposition: features populated, services empty
mapping: services populated (microservice/modular-monolith only)
review: user confirmed mapping
complete: manifest written — state file deleted
```

---

### 9. Manifest (dict — not a dataclass)

**Location**: `src/specforge/core/manifest_writer.py` (constructed as dict, serialized via `json.dumps`)

**Schema**: See `specs/004-architecture-decomposer/contracts/manifest-schema.md`

The manifest is a plain dict because:
1. It's the serialization target (written as JSON), not a domain entity used in logic
2. It's constructed once from Feature + Service + Event entities and written to disk
3. Post-write validation operates on the deserialized dict (FR-053)

---

### 10. DomainMatch (frozen dataclass)

**Location**: `src/specforge/core/domain_analyzer.py`

| Field | Type | Description |
|-------|------|-------------|
| `domain_name` | `str` | Matched domain (e.g., "finance") or "generic" |
| `score` | `int` | Total keyword weight score |
| `matched_keywords` | `tuple[str, ...]` | Keywords that matched from description |

**Validation**:
- If `score < 2`: triggers clarification mode (FR-006)
- If `score >= 2`: proceed with matched domain

---

## Relationships

```
DomainPattern  1──*  FeatureTemplate     (domain contains feature templates)
DomainMatch    1──1  DomainPattern       (match references a domain)
Feature        *──1  Service             (each feature belongs to exactly one service)
Service        *──*  CommunicationLink   (services communicate with other services)
Service        *──*  Event               (services produce/consume events)
DecompositionState ──* Feature           (state tracks features)
DecompositionState ──* Service           (state tracks services)
Manifest       ──*  Feature              (manifest contains all features)
Manifest       ──*  Service              (manifest contains all services)
Manifest       ──*  Event                (manifest contains all events)
```

## State Machine: Decompose Flow

```
┌─────────┐    ┌──────────────┐    ┌─────────┐    ┌────────┐    ┌──────────┐
│  START   │───►│ architecture │───►│decompose│───►│mapping │───►│ review   │
└─────────┘    └──────────────┘    └─────────┘    └────────┘    └──────────┘
                                       │                              │
                                       │ (monolith: skip mapping)     │
                                       └──────────────────────────────┤
                                                                      │
                                                                      ▼
                                                                ┌──────────┐
                                                                │ complete │
                                                                └──────────┘
                                                                      │
                                                                      ▼
                                                              (delete state,
                                                               write manifest)
```
