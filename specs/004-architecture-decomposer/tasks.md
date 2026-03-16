# Tasks: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Input**: Design documents from `specs/004-architecture-decomposer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD enforced — test files BEFORE implementation files (Constitution Principle IV).

**Organization**: Tasks grouped by user story. Each story is independently testable.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US7)
- Effort: S=small (<30 min), M=medium (30–90 min), L=large (90+ min), XL=half day+

---

## Phase 1: Setup (Config & Constants)

**Purpose**: Add new types and constants to existing config.py — blocks all new modules

- [ ] T001 (S) UPDATE `src/specforge/core/config.py` — add `ArchitectureType` Literal, `VALID_ARCHITECTURES` list, `OVER_ENGINEERING_THRESHOLD = 5`, `MANIFEST_PATH`, `STATE_PATH`, `FEATURE_CATEGORIES`, `FEATURE_PRIORITIES`, `COMMUNICATION_PATTERNS` constants per quickstart.md Phase 1

> Commit: `feat(004): add architecture types and decompose constants to config`

---

## Phase 2: Foundational — Domain Patterns & Data Layer

**Purpose**: Domain knowledge data and core dataclasses — MUST complete before user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 (M) [P] Create tests for domain patterns in `tests/unit/test_domain_patterns.py` — validate all 6 domains + generic have 8–15 features, correct FeatureTemplate structure (name, description, category, priority, always_separate, data_keywords), keyword weights 1–3, and always_separate flags on auth/notification/integration/frontend
- [ ] T003 (XL) [P] Create `src/specforge/core/domain_patterns.py` — define `DOMAIN_PATTERNS` list with 6 domain dicts (finance, ecommerce, saas, social, healthcare, education) + `GENERIC_PATTERN` fallback per data-model.md §2–3 and spec FR-038/FR-049

> Commit: `feat(004): add domain pattern dictionaries for 6 domains + generic fallback`

- [ ] T004 (S) [P] Create tests for decomposition state in `tests/unit/test_decomposition_state.py` — test save/load round-trip for each step, resume detection from partial state file, state file deletion on complete (UT-012, UT-013)
- [ ] T005 (M) [P] Create `src/specforge/core/decomposition_state.py` — `DecompositionState` frozen dataclass, `save_state()` and `load_state()` functions with atomic writes per data-model.md §8, research.md Task 3/Task 5

> Commit: `feat(004): add DecompositionState persistence with atomic writes`

- [ ] T006 (S) [P] Create `src/specforge/templates/base/features/manifest.json.j2` — single line: `{{ manifest | tojson(indent=2) }}` per research.md Task 2
- [ ] T007 (S) [P] Create `src/specforge/templates/base/features/communication-map.md.j2` — Mermaid diagram template with service communication table per research.md Task 6. Note: this `.md.j2` file will be auto-discovered by TemplateRegistry as `TemplateType.feature` — either add it to `_EXCLUDED_FILES` in `template_registry.py` and render via `render_raw()`, or register a variable schema in `config.py`

> Commit: `feat(004): add manifest and communication-map Jinja2 templates`

**Checkpoint**: Domain data, state persistence, and templates ready. All user stories can now proceed.

---

## Phase 3: User Story 1+2 — Architecture Gate & Feature Decomposition (Priority: P1) MVP

**Goal**: User runs `specforge decompose "description"`, selects architecture, gets 8–15 prioritized features from domain analysis.

**Independent Test**: `specforge decompose --arch monolithic "Create a personal finance webapp"` produces a numbered feature list with domain-appropriate names.

### Tests for US1+US2

> **Write tests FIRST, ensure they FAIL before implementation**

- [ ] T008 (M) [P] [US2] Create `tests/unit/test_domain_analyzer.py` — test all 6 domains produce 8–15 features with correct names/categories (UT-001), test generic fallback for unrecognized input (UT-002), test keyword scoring: vague input triggers clarification at score < 2, clear input proceeds (UT-003), test gibberish detection, test >15 feature warning, test <5 features proceeds normally, test priority assignment P0–P3 (UT-014)

### Implementation for US1+US2

- [ ] T009 (L) [US2] Create `src/specforge/core/domain_analyzer.py` — `DomainAnalyzer` class with constructor injection of patterns, `analyze(description) -> Result[DomainMatch]` keyword scoring, `decompose(description, domain) -> Result[list[Feature]]` feature generation, `is_gibberish(description) -> bool`, `clarify(description) -> list[str]` returns 5 generic question templates from FR-058 for vague input (score < 2), `Feature` and `DomainMatch` frozen dataclasses per data-model.md §4/§10. `decompose()` must warn when >15 features generated (FR-008) and proceed normally for <5 features (FR-009)

> Commit: `feat(004): implement DomainAnalyzer with keyword scoring and feature decomposition`

- [ ] T010 (M) [US1] UPDATE `src/specforge/cli/decompose_cmd.py` — replace placeholder with Click command skeleton: add `--arch` option (`type=click.Choice`), `--remap` option, `--no-warn` flag, mutual exclusion validation (FR-048), architecture gate using Rich Panel + Prompt for 3-choice selection per cli-contract.md, wire to `DomainAnalyzer` for feature decomposition, Rich Table for feature list display, state save after architecture selection and after decomposition per research.md Task 1. Wire clarification mode: if `DomainAnalyzer.analyze()` returns score < 2, ask 5 questions from `clarify()`, concatenate answers with description, re-analyze (FR-006/FR-058). Wire >15 features consolidation warning (FR-008). For monolithic: skip service mapping, defer manifest writing to T022 (ManifestWriter not yet available).

> Commit: `feat(004): implement architecture gate and decompose CLI flow for US1+US2`

- [ ] T011 (M) [US1] Create `tests/integration/test_decompose_flow.py` — IT-002: monolithic flow (`--arch monolithic` → no service mapping, all features as modules), IT-004: over-engineering warning (3-feature app + `--arch microservice`), IT-005: `--no-warn` suppresses warning, EC-001: gibberish input → error message, EC-005: empty description → error with examples. Also UPDATE existing `tests/integration/test_decompose_cmd.py` — add `--arch monolithic` to `test_with_description_exits_0` to prevent interactive prompt hang (existing tests break without this fix)

> Commit: `test(004): add integration tests for architecture gate and monolith flow`

**Checkpoint**: US1+US2 complete. `specforge decompose --arch monolithic "finance app"` works end-to-end with feature list output. Monolith manifest written.

---

## Phase 4: User Story 3 — Smart Feature-to-Service Mapping (Priority: P2)

**Goal**: For microservice/modular-monolith, features are intelligently grouped into services with rationale.

**Independent Test**: Decompose with microservice → produces 40–70% fewer services than features, each with WHY COMBINED/SEPARATE rationale.

### Tests for US3

- [ ] T012 (L) [P] [US3] Create `tests/unit/test_service_mapper.py` — UT-004: affinity scoring (same category +3, shared data_keywords +2, diff scaling −2, diff failure −2), UT-005: always_separate rules (auth/notification/integration/frontend always standalone), UT-006: greedy merge (affinity ≥3 combined, <3 singletons), UT-007: max 4 features per service cap, UT-008: every service gets WHY COMBINED or WHY SEPARATE rationale, test monolithic → single service with all features

### Implementation for US3

- [ ] T013 (L) [US3] Create `src/specforge/core/service_mapper.py` — `ServiceMapper` class, `Service` frozen dataclass per data-model.md §5, `map_features(features, arch) -> Result[list[Service]]` orchestrator, helper functions: `_compute_pairwise_scores`, `_apply_always_separate`, `_greedy_merge`, `_enforce_max_features`, `_generate_rationale` (each ≤30 lines) per research.md Task 4, FR-050 algorithm

> Commit: `feat(004): implement ServiceMapper with affinity scoring and rationale generation`

- [ ] T014 (M) [US3] UPDATE `src/specforge/cli/decompose_cmd.py` — wire ServiceMapper after DomainAnalyzer for microservice/modular-monolith paths, add Rich Table display of service mapping with rationale column, add over-engineering warning when features ≤5 + microservice (FR-016), save state after mapping step

> Commit: `feat(004): wire service mapping into decompose CLI flow`

**Checkpoint**: US3 complete. Microservice decompose produces grouped services with rationale. `--arch microservice "finance app"` works.

---

## Phase 5: User Story 4 — Interactive Mapping Review & Edit (Priority: P2)

**Goal**: User can review and interactively edit the proposed service mapping before finalization.

**Independent Test**: After mapping, edit commands (combine, split, rename, add, remove, override, done) correctly mutate the mapping.

### Implementation for US4

- [ ] T015 (M) [US4] UPDATE `src/specforge/cli/decompose_cmd.py` — add interactive review loop after service mapping: display mapping table, accept text commands (combine/split/rename/add/remove/override/done) via `console.input()` + `match/case` dispatch per cli-contract.md §Edit Commands, re-validate after each edit (FR-041 — no circular deps, no duplicate features), `remove` prompts user to reassign features, `override` changes communication patterns per cli-contract.md

> Commit: `feat(004): implement interactive service mapping review and edit loop`

- [ ] T016 (S) [US4] Add edge case tests to `tests/integration/test_decompose_flow.py` — EC-003: circular dependency after edit → detected and reported, EC-004: same feature in two services → validation error

> Commit: `test(004): add edge case tests for interactive mapping validation`

**Checkpoint**: US4 complete. User can edit mappings interactively. All edits validated before confirmation.

---

## Phase 6: User Story 5 — Service Communication Map (Priority: P3)

**Goal**: Generate communication patterns between services and a Mermaid dependency diagram.

**Independent Test**: After approving microservice mapping, output includes communication-map.md with directed connections and pattern labels.

### Tests for US5

- [ ] T017 (M) [P] [US5] Create `tests/unit/test_communication_planner.py` — UT-009: test all 5 heuristic rules (notification→async, auth→REST, same-context-split→gRPC, diff-context→REST, analytics→async), test Mermaid generation with solid arrows (required) and dashed arrows (optional), test DFS cycle detection per research.md Task 4

### Implementation for US5

- [ ] T018 (M) [US5] Create `src/specforge/core/communication_planner.py` — `CommunicationPlanner` class, `CommunicationLink` and `Event` frozen dataclasses per data-model.md §6–7, `plan(services) -> tuple[list[Service], list[Event]]` pattern assignment, `generate_mermaid(services, events) -> str` diagram, `detect_cycles(services) -> list[list[str]]` DFS-based cycle detection per research.md Task 4

> Commit: `feat(004): implement CommunicationPlanner with heuristic patterns and Mermaid output`

- [ ] T019 (S) [US5] UPDATE `src/specforge/cli/decompose_cmd.py` — wire CommunicationPlanner after mapping confirmation, render communication-map.md.j2 via `TemplateRenderer.render_raw()`, write to `.specforge/communication-map.md`

> Commit: `feat(004): wire communication planning into decompose flow`

**Checkpoint**: US5 complete. Communication map with Mermaid diagram generated for microservice/modular-monolith.

---

## Phase 7: User Story 7 — Manifest & Persistence (Priority: P2)

**Goal**: Write validated manifest.json atomically at each step, support resume on re-run.

**Independent Test**: Kill CLI mid-flow, re-run → offers resume from last step. Final manifest passes all 10 validation rules.

### Tests for US7

- [ ] T020 (M) [P] [US7] Create `tests/unit/test_manifest_writer.py` — UT-010: atomic write (temp + fsync + rename), UT-011: post-write validation catches invalid JSON, missing schema_version, duplicate feature ID, cross-reference errors, missing service assignment per manifest-schema.md §Validation Rules

### Implementation for US7

- [ ] T021 (M) [US7] Create `src/specforge/core/manifest_writer.py` — `ManifestWriter` class, `build_manifest(arch, domain, features, services, events, description) -> dict`, `write(path, manifest) -> Result[Path]` atomic write via mkstemp + fsync + Path.replace per research.md Task 3, `validate(path) -> Result[None]` 10-rule post-write validation per manifest-schema.md, render via `TemplateRenderer.render_raw("base/features/manifest.json.j2", {"manifest": dict})`

> Commit: `feat(004): implement ManifestWriter with atomic writes and post-write validation`

- [ ] T022 (M) [US7] UPDATE `src/specforge/cli/decompose_cmd.py` — wire ManifestWriter for final manifest output, add resume logic: check for `.specforge/decompose-state.json` on startup, offer resume/start-fresh prompt (FR-036), delete state file on successful completion, create feature directories under `.specforge/features/` per FR-025

> Commit: `feat(004): wire manifest writing and resume logic into decompose flow`

**Checkpoint**: US7 complete. Full flow persists state, resumes on crash, writes validated manifest.

---

## Phase 8: User Story 6 — Architecture Re-mapping (Priority: P3)

**Goal**: Re-map existing features to a different architecture without losing content.

**Independent Test**: Decompose as monolith, then `--remap microservice` → features preserved, services added, no files deleted.

### Implementation for US6

- [ ] T023 (M) [US6] UPDATE `src/specforge/cli/decompose_cmd.py` — implement `--remap` flow: load existing manifest, preserve features, re-run ServiceMapper with new architecture type, update manifest, preserve all existing spec/plan/tasks files (FR-031), handle all 6 transitions per cli-contract.md §Re-mapping table

> Commit: `feat(004): implement architecture re-mapping with feature preservation`

- [ ] T024 (M) [US6] Add remap integration test to `tests/integration/test_decompose_flow.py` — IT-003: decompose as monolith → remap to microservice → verify features preserved, services added, no files deleted

> Commit: `test(004): add integration test for architecture re-mapping flow`

**Checkpoint**: US6 complete. Users can switch architecture without losing work.

---

## Phase 9: Polish & Cross-Cutting

**Purpose**: Full-flow integration tests, snapshot golden files, final validation

- [ ] T025 (M) Add full end-to-end integration tests to `tests/integration/test_decompose_flow.py` — IT-001: `specforge decompose --arch microservice "finance app"` → verify manifest.json, feature directories, communication-map.md all created and valid. Add modular-monolith integration test: `--arch modular-monolith "finance app"` → verify `architecture: "modular-monolith"` in manifest, same directory structure as microservice, communication links present
- [ ] T026 (M) [P] Create snapshot tests — ST-001: manifest golden file for "PersonalFinance" + microservice, ST-002: communication-map.md Mermaid golden file, ST-003: manifest golden file for monolithic. Add to `tests/snapshots/` using syrupy
- [ ] T027 (S) Run full test suite (`uv run pytest --cov=specforge --cov-report=term-missing`) and verify 100% coverage on all new `core/` modules
- [ ] T028 (S) Run linter (`uv run ruff check src/specforge/core/ tests/`) and fix any violations

> Commit: `test(004): add E2E integration tests and snapshot golden files`
> Commit: `chore(004): ensure full test coverage and lint compliance`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────────────┐
Phase 2 (Foundation) ─── T002+T003, T004+T005, T006+T007 ────┤ [all P]
                                                               ▼
Phase 3 (US1+2: Gate+Decompose) ── T008→T009→T010→T011 ──── MVP
                                                               │
Phase 4 (US3: Mapping) ──── T012→T013→T014 ───────────────────┤
Phase 5 (US4: Edit) ──── T015→T016 ───────────────────────────┤ depends on US3
Phase 6 (US5: Communication) ── T017→T018→T019 ───────────────┤ depends on US3
Phase 7 (US7: Manifest) ── T020→T021→T022 ────────────────────┤
                                                               │
Phase 8 (US6: Remap) ── T023→T024 ────────────────────────────┤ depends on US7
Phase 9 (Polish) ── T025, T026, T027, T028 ───────────────────┘ depends on all
```

### User Story Dependencies

- **US1+US2 (P1)**: Depends on Phase 2 only — MVP target
- **US3 (P2)**: Depends on US1+US2 (needs features to map)
- **US4 (P2)**: Depends on US3 (needs mapping to edit)
- **US5 (P3)**: Depends on US3 (needs services for communication)
- **US7 (P2)**: Can start after US1+US2 (manifest needs features), but benefits from US3+US5
- **US6 (P3)**: Depends on US7 (needs manifest to remap)

### Parallel Opportunities

**Phase 2** (all parallel — different files):
```
T002 (test_domain_patterns) ║ T004 (test_decomposition_state) ║ T006 (manifest.json.j2)
T003 (domain_patterns.py)   ║ T005 (decomposition_state.py)   ║ T007 (communication-map.j2)
```

**After Phase 3** (US3 tests + US5 tests + US7 tests in parallel):
```
T012 (test_service_mapper) ║ T017 (test_communication_planner) ║ T020 (test_manifest_writer)
```

---

## Implementation Strategy

### MVP First (US1+US2 Only)

1. Complete Phase 1: config.py constants (T001)
2. Complete Phase 2: domain patterns + state + templates (T002–T007)
3. Complete Phase 3: domain analyzer + CLI gate (T008–T011)
4. **STOP AND VALIDATE**: `specforge decompose --arch monolithic "finance app"` works
5. Monolithic flow complete — features listed, manifest written

### Incremental Delivery

1. **MVP**: Setup + Foundation + US1+US2 → Monolithic decompose works
2. **+Service Mapping**: US3 → Microservice grouping with rationale
3. **+Interactive Edit**: US4 → Users can modify mappings
4. **+Communication**: US5 → Mermaid diagram + communication patterns
5. **+Persistence**: US7 → Crash-safe state, validated manifest
6. **+Re-mapping**: US6 → Switch architecture without data loss
7. **Polish**: Snapshots, E2E tests, coverage, lint

---

## Notes

- [P] tasks = different files, no dependencies
- Each completed task = one git commit (Conventional Commits)
- TDD: test files created BEFORE implementation files
- All new classes use constructor injection — no global state
- All functions ≤30 lines, all classes ≤200 lines (constitution)
- `Result[T]` for all recoverable errors in `core/` — no `raise`
- Constants in `config.py` — no magic strings
