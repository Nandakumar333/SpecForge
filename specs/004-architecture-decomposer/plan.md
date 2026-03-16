# Implementation Plan: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Branch**: `004-architecture-decomposer` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-architecture-decomposer/spec.md`

## Summary

Implement the `specforge decompose` command: an interactive multi-step flow that (1) presents an architecture decision gate (monolithic / microservice / modular-monolith), (2) analyzes the user's app description against 6 built-in domain patterns to produce 8–15 prioritized features, (3) maps features to services using affinity scoring with combining/separation rules, (4) supports interactive review/editing of mappings, (5) generates a centralized `manifest.json` with communication patterns and Mermaid dependency diagram, and (6) persists state at each step for crash-safe resumption.

All logic is deterministic and rule-based — no LLM dependency. Domain patterns and mapping rules are hard-coded Python dicts. Output uses Jinja2 templates for both the communication map (`communication-map.md.j2`) and manifest (`manifest.json.j2` with `tojson` filter via `render_raw()`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI framework), Rich 13.x (terminal output + interactive prompts), Jinja2 3.x (template rendering — `communication-map.md.j2` + `manifest.json.j2` via `tojson` filter)
**Storage**: File system — `.specforge/manifest.json`, `.specforge/decompose-state.json`; atomic writes via `os.replace()`
**Testing**: pytest + pytest-cov + syrupy (snapshot tests) + ruff (linting)
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)
**Project Type**: CLI tool (extension of existing `specforge` CLI)
**Performance Goals**: Full decompose flow < 30 seconds (SC-001); deterministic — same input produces identical output (SC-004)
**Constraints**: Offline only, zero new external dependencies, no LLM/AI API calls, no network access
**Scale/Scope**: 6 built-in domain patterns, 8–15 features per decomposition, 7 new Python modules in `core/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | PASS | `spec.md` complete with 58 FRs, 14 UTs, 5 ITs, 3 STs, 5 ECs |
| II. Architecture | PASS | All new modules in `core/` (zero external deps). `communication-map.md.j2` and `manifest.json.j2` (using `tojson` filter) use Jinja2. No cross-layer imports. |
| III. Code Quality | PASS | Type hints on all signatures. `Result[T]` for recoverable errors. Constants in `config.py`. Constructor injection. Functions ≤30 lines (affinity scoring decomposed into helpers). |
| IV. Testing | PASS | TDD: test files before implementation. Unit tests for all 7 modules. Integration tests for CLI flows. Snapshot tests for manifest + communication map. |
| V. Commit Strategy | PASS | Conventional Commits. One commit per completed task. |
| VI. File Structure | PASS | New modules: `core/domain_analyzer.py`, `core/service_mapper.py`, `core/manifest_writer.py`, `core/decomposition_state.py`, `core/communication_planner.py`, `core/domain_patterns.py`. CLI: `cli/decompose_cmd.py` (update). Templates: `templates/base/features/`. Tests: `tests/unit/`, `tests/integration/`, `tests/snapshots/`. |
| VII. Governance | PASS | Constitution supersedes. No architecture-aware governance in v1 (FR-045). |

## Project Structure

### Documentation (this feature)

```text
specs/004-architecture-decomposer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli-contract.md  # decompose command CLI interface
│   └── manifest-schema.md # manifest.json schema contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   └── decompose_cmd.py          # UPDATE: full decompose flow implementation
├── core/
│   ├── config.py                 # UPDATE: ArchitectureType enum, new constants
│   ├── domain_patterns.py        # NEW: 6 domain pattern dicts + generic fallback
│   ├── domain_analyzer.py        # NEW: keyword scoring, domain matching, feature generation
│   ├── service_mapper.py         # NEW: affinity scoring, combining/separation, rationale
│   ├── communication_planner.py  # NEW: auto-assign patterns, Mermaid diagram generation
│   ├── manifest_writer.py        # NEW: manifest JSON generation, atomic write, validation
│   └── decomposition_state.py    # NEW: save/load/resume partial state
└── templates/base/features/
    ├── communication-map.md.j2   # NEW: Mermaid dependency diagram template
    └── manifest.json.j2          # NEW: Manifest output ({{ manifest | tojson }})

tests/
├── unit/
│   ├── test_domain_patterns.py   # NEW: domain data integrity tests
│   ├── test_domain_analyzer.py   # NEW: UT-001 through UT-003
│   ├── test_service_mapper.py    # NEW: UT-004 through UT-008
│   ├── test_communication_planner.py # NEW: UT-009
│   ├── test_manifest_writer.py   # NEW: UT-010, UT-011
│   └── test_decomposition_state.py   # NEW: UT-012, UT-013
├── integration/
│   └── test_decompose_flow.py    # NEW: IT-001 through IT-005
└── snapshots/
    ├── test_manifest_microservice/ # NEW: ST-001
    ├── test_manifest_monolith/    # NEW: ST-003
    └── test_communication_map/    # NEW: ST-002
```

**Structure Decision**: Single-project structure (existing SpecForge layout). All new production code goes in `src/specforge/core/` (domain logic) and `src/specforge/cli/` (command update). One new Jinja2 template in `templates/base/features/`. Tests follow existing `tests/unit/`, `tests/integration/`, `tests/snapshots/` convention.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `domain_patterns.py` exceeds 200 lines | Contains 6 domain pattern dictionaries + generic fallback. Each domain has ~12-15 feature entries with metadata fields. This is pure data declaration, not logic. | Splitting into 7 separate files (one per domain) would fragment related data and complicate imports. The constitution limit targets classes (200 LOC), not data modules. A single module with clearly separated sections is more navigable. |
| `display_name` added to manifest `features[]` schema | Spec FR-024 defines `name` (kebab-case slug) but no human-readable display name. The data model adds `display_name` for Rich table output and downstream feature spec generation readability. | Using `name` for both slug and display would require slug→display conversion everywhere. A dedicated `display_name` field is cleaner. This is a backward-compatible additive enhancement to the manifest schema. |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Spec-First | PASS | All design artifacts trace back to spec FRs. data-model.md entities map 1:1 to spec Key Entities. CLI contract covers all spec acceptance scenarios. |
| II. Architecture | PASS | 7 new modules all in `core/` with zero external deps. `communication-map.md.j2` and `manifest.json.j2` in `templates/base/features/`. All file generation via Jinja2. No cross-layer imports. `cli/decompose_cmd.py` imports from `core/` only. |
| III. Code Quality | PASS | All entities are frozen dataclasses with type hints. Affinity scoring decomposed into 6 helper functions (each ≤30 lines). `Result[T]` used for all fallible operations. Constants (`ArchitectureType`, thresholds, paths) added to `config.py`. |
| IV. Testing | PASS | Test plan covers: 7 unit test files (UT-001–UT-014), 1 integration test file (IT-001–IT-005), 3 snapshot test suites (ST-001–ST-003), 5 edge case tests (EC-001–EC-005). TDD order preserved in quickstart.md. |
| V. Commit Strategy | PASS | Implementation phases map to atomic commits. |
| VI. File Structure | PASS | No changes from pre-design check. All files in correct layers. |
| VII. Governance | PASS | No conflicts. Complexity Tracking documents 1 justified deviation (`domain_patterns.py` data module size). |
