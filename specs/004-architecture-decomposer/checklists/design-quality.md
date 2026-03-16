# Design Quality Checklist: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Purpose**: Validate that plan-phase design artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) completely, clearly, and consistently address spec.md requirements
**Created**: 2026-03-15
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Depth**: Standard
**Audience**: Reviewer (PR gate, post-planning)
**Focus Areas**: Specification completeness traceability, architecture gate design, feature decomposition design, service mapping design, communication planning design, manifest contract, integration with Features 001–003, testing coverage, code quality alignment

---

## Specification Completeness — Design Traceability

- [x] CHK001 - Are all 7 user stories traceable to specific design artifacts (data-model entities, CLI contract flows, or quickstart phases)? [Completeness, Spec §US1–US7]
- [x] CHK002 - Are all 10 edge cases from the spec addressed in the CLI contract error messages or data-model validation rules? [Coverage, Spec §Edge Cases]
- [x] CHK003 - Are non-functional requirements (determinism, <30s speed, persistence) reflected in specific design decisions in research.md or plan.md? [Completeness, Spec §SC-001/SC-004/SC-006]
- [x] CHK004 - Are all 8 out-of-scope exclusions preserved in design decisions (no LLM, no deployment config, no domain combination, no configurable rules)? [Consistency, Spec §Out of Scope]
- [x] CHK005 - Are all 3 architecture types defined with distinct data-model behaviors in manifest-schema.md? [Completeness, Spec §FR-033/FR-043]
- [x] CHK006 - Does the data-model.md cover every Key Entity defined in the spec (Manifest, Feature, Service, Module, CommunicationLink, DecompositionState)? [Completeness, Spec §Key Entities]
- [x] CHK007 - Is the relationship between FeatureTemplate (pattern data) and Feature (runtime entity) clearly documented in the data model? [Clarity, data-model.md §Entities 3–4]

---

## Architecture Decision Gate — Design Adequacy

- [x] CHK008 - Does the CLI contract define the exact interactive prompt format for all 3 architecture choices including one-line descriptions? [Completeness, Spec §FR-001/FR-003, cli-contract.md §Interactive Flow]
- [x] CHK009 - Is the `--arch` flag's bypass behavior specified in both the CLI contract (options table) and the research.md (Rich vs Click decision)? [Consistency, Spec §FR-035]
- [x] CHK010 - Is the over-engineering warning threshold (≤5 features) documented in both plan.md (config.py constants) and CLI contract (warning example)? [Consistency, Spec §FR-016/FR-046]
- [x] CHK011 - Does the CLI contract specify `--remap` behavior for all 6 architecture transitions (mono↔micro, mono↔modular, micro↔modular)? [Coverage, Spec §FR-030/FR-031/FR-032] — PASS: Remap transition table added to cli-contract.md §Re-mapping with all 6 transitions documented.
- [x] CHK012 - Is partial state recovery (Ctrl+C) documented with step-level granularity in both data-model.md (DecompositionState transitions) and research.md (Task 5)? [Completeness, Spec §FR-037]
- [x] CHK013 - Is the first-run vs subsequent-run distinction documented in the CLI contract with concrete example flows? [Clarity, Spec §FR-036, cli-contract.md §Subsequent Run]
- [x] CHK014 - Are the exact error messages for invalid `--arch` values and `--arch + --remap` conflicts specified verbatim in the CLI contract? [Clarity, Spec §FR-047/FR-048, cli-contract.md §Error Messages]
- [x] CHK015 - Does the state machine diagram in data-model.md cover the monolith shortcut path (skip mapping/review)? [Completeness, data-model.md §State Machine]

---

## Feature Decomposition — Design Adequacy

- [x] CHK016 - Does the data-model.md DomainPattern entity specify all 6 domain names and the generic fallback with the exact FR-049 dictionary structure? [Completeness, Spec §FR-038/FR-049]
- [x] CHK017 - Is the generic fallback feature set (Auth, CRUD, Admin, Reporting, Notifications) documented in the data model or plan? [Completeness, Spec §FR-007]
- [x] CHK018 - Is the v1 non-combinable decision documented in research.md with rationale and deferral note? [Clarity, Spec §FR-039/C-11]
- [x] CHK019 - Is the keyword scoring algorithm (weighted keywords, sum scores, threshold ≥ 2) specified with enough detail to implement deterministically? [Clarity, Spec §FR-006/FR-039, research.md §Task 4]
- [x] CHK020 - Is the priority assignment logic (category→priority mapping: foundation→P0, core→P1, etc.) specified in both data-model.md and quickstart.md? [Completeness, Spec §FR-005]
- [x] CHK021 - Are the `data_keywords` field and its role in affinity scoring connected across data-model.md (FeatureTemplate entity) and research.md (Task 4)? [Consistency]
- [x] CHK022 - Is the gibberish/empty input detection documented with specific criteria and example error messages in the CLI contract? [Completeness, Spec §FR-010, cli-contract.md §Error Messages]
- [x] CHK023 - Is the >15 features consolidation warning behavior documented in the design artifacts? [Coverage, Spec §FR-008]

---

## Service Mapping (Microservice) — Design Adequacy

- [x] CHK024 - Is the full 6-step affinity scoring algorithm from FR-050 documented in research.md with specific score values (+3/+2/+1/−2/−2) and merge threshold (≥3)? [Completeness, Spec §FR-050, research.md §Task 4]
- [x] CHK025 - Are the `always_separate` rules (auth, notification, integration, frontend) traceable from spec FR-015 through data-model FeatureTemplate.always_separate to quickstart Phase 3? [Consistency, Spec §FR-015]
- [x] CHK026 - Is the rationale generation pattern ("Combined: shared '{category}' bounded context...") specified with concrete template strings? [Clarity, Spec §FR-040/C-06, research.md §Task 4]
- [x] CHK027 - Is the WHY SEPARATE rationale template equally specified alongside the WHY COMBINED template? [Consistency, Spec §FR-012] — PASS: 4 WHY SEPARATE templates added to research.md Task 4 (always-separate, different scaling, different failure mode, singleton).
- [x] CHK028 - Are all 6 edit operations (combine, split, rename, add, remove, done) specified with syntax examples in the CLI contract? [Completeness, Spec §FR-017–FR-021, cli-contract.md §Edit Commands]
- [x] CHK029 - Is immediate re-validation after user edits documented as a design requirement in the CLI contract or data-model.md? [Completeness, Spec §FR-041]
- [x] CHK030 - Is the circular dependency detection algorithm specified in the design artifacts (e.g., topological sort, Kahn's algorithm)? [Clarity, Spec §FR-023] — PASS: DFS-based cycle detection algorithm specified in research.md Task 4 with O(V+E) complexity and full cycle path reporting.
- [x] CHK031 - Is the max 4 features per service cap documented in both data-model.md (Service validation) and research.md (algorithm step 5)? [Consistency, Spec §FR-050]
- [x] CHK032 - Does the data model define what happens to orphaned features when a service is removed via the `remove` edit command? [Coverage, Spec §FR-021, cli-contract.md] — PASS: cli-contract.md §Edit Commands specifies "user prompted to reassign each feature" — interactive per-feature reassignment to existing services.

---

## Communication Planning — Design Adequacy

- [x] CHK033 - Are all 5 heuristic rules from FR-027 documented in the design artifacts (notification→async, auth→REST, internal→gRPC, different-context→REST, analytics→async)? [Completeness, Spec §FR-027]
- [x] CHK034 - Is the CommunicationLink entity's `required` field connected to Mermaid rendering (solid vs dashed arrows) in both data-model.md and manifest-schema.md? [Consistency, Spec §FR-051]
- [x] CHK035 - Is the Event entity's naming pattern (`{producer}.{entity}.{action}`) specified with validation regex in data-model.md? [Clarity, Spec §FR-052, data-model.md §Entity 7]
- [x] CHK036 - Does the design specify where the communication-map.md file is written (`.specforge/communication-map.md`) and under what conditions (microservice/modular-monolith only)? [Completeness, cli-contract.md §Output Files]
- [x] CHK037 - Is user override of auto-assigned communication patterns during interactive review documented in the design? [Coverage, Spec §FR-027] — PASS: `override` edit command added to cli-contract.md §Edit Commands (`override <service> <target> <pattern>`) for changing communication patterns between services.

---

## Manifest — Design Adequacy

- [x] CHK038 - Does the manifest-schema.md contract match the spec's FR-024 schema exactly (all fields, types, nesting)? [Consistency, Spec §FR-024, manifest-schema.md §Full Schema] — PASS: `display_name` deviation documented in plan.md Complexity Tracking with rationale (Rich table output + downstream readability). Backward-compatible additive field.
- [x] CHK039 - Are all 10 post-write validation rules from FR-053 documented with specific error messages in manifest-schema.md? [Completeness, Spec §FR-053, manifest-schema.md §Validation Rules]
- [x] CHK040 - Is the atomic write mechanism (temp file + `os.replace()`) documented in both research.md (Task 3) and quickstart.md (Key Patterns)? [Consistency, Spec §FR-028] — PASS: Both research.md and quickstart.md include `os.fsync(fd)` before close.
- [x] CHK041 - Is the "full rewrite, not incremental patch" manifest update approach documented consistently across research.md and manifest-schema.md? [Consistency, Spec §FR-029]
- [x] CHK042 - Does manifest-schema.md define architecture-specific manifest behavior for all 3 types (monolith: 1 service, microservice: multiple, modular-monolith: same as micro)? [Completeness, manifest-schema.md §Architecture-Specific]
- [x] CHK043 - Is the `schema_version` field's forward-compatibility purpose documented with migration deferral note? [Clarity, Spec §FR-042, manifest-schema.md §Schema Version]
- [x] CHK044 - Does the manifest schema in the contract include the `display_name` field that appears in data-model.md's Feature entity but is absent from the spec's FR-024 schema? [Consistency, Spec §FR-024 vs data-model.md §Entity 4] — PASS: Deviation documented in plan.md Complexity Tracking. `display_name` is an additive backward-compatible enhancement for Rich table output and downstream readability.

---

## Integration with Features 001–003 — Design Adequacy

- [x] CHK045 - Are the specific changes to `decompose_cmd.py` documented (new Click options, flow orchestration, Rich output, state logic, module imports)? [Completeness, Spec §New Modules, quickstart.md §Phase 6]
- [x] CHK046 - Is the `manifest.json.j2` template registered via `render_raw()` with explicit documentation that no TemplateRegistry changes are needed? [Clarity, research.md §Task 2/Task 6]
- [x] CHK047 - Is the Feature 003 governance scope explicitly limited (no architecture-conditional prompts in v1) in plan.md? [Completeness, Spec §FR-045, plan.md §Constitution Check]
- [x] CHK048 - Is backward compatibility with existing CLI commands (init, check, validate-prompts) addressed in the plan's constitution check? [Completeness, Spec §FR-054]
- [x] CHK049 - Are the new constants added to `config.py` enumerated in the quickstart.md (ArchitectureType, OVER_ENGINEERING_THRESHOLD, MANIFEST_PATH, STATE_PATH)? [Completeness, quickstart.md §Phase 1]
- [x] CHK050 - Is the `communication-map.md.j2` template discoverable by the existing TemplateRegistry without modifications (`.md.j2` extension, in `features/` directory)? [Consistency, research.md §Task 6]

---

## Testing — Design Coverage

- [x] CHK051 - Does the quickstart.md map every unit test ID (UT-001–UT-014) to a specific test file and module? [Completeness, Spec §Testing Requirements, quickstart.md] — PASS: Each UT ID now mapped to specific method under test in quickstart.md.
- [x] CHK052 - Are integration tests (IT-001–IT-005) specified with concrete input scenarios and expected output assertions in the spec? [Clarity, Spec §IT-001–IT-005]
- [x] CHK053 - Are snapshot test golden file paths defined in plan.md's project structure with matching spec IDs (ST-001–ST-003)? [Completeness, plan.md §Source Code]
- [x] CHK054 - Are all 5 edge case tests (EC-001–EC-005) traceable to specific edge cases in the spec's Edge Cases section? [Consistency, Spec §Edge Cases/EC-001–EC-005]
- [x] CHK055 - Is test file creation order documented as "before implementation" in alignment with constitution Principle IV (TDD)? [Consistency, quickstart.md §Implementation Order] — PASS: quickstart.md updated to explicitly state "TDD enforced: create test files BEFORE implementation files (Constitution Principle IV)."
- [x] CHK056 - Does the test plan include coverage for the monolith shortcut path (decompose without mapping/review)? [Coverage, Spec §IT-002]

---

## Code Quality (Constitution Alignment) — Design Adequacy

- [x] CHK057 - Is the affinity scoring algorithm's decomposition into ≤30-line helper functions explicitly documented in research.md (6 named functions)? [Completeness, Constitution §III, research.md §Task 4]
- [x] CHK058 - Is the `domain_patterns.py` 200-line data module exception justified in plan.md's Complexity Tracking with rationale and rejected alternative? [Completeness, plan.md §Complexity Tracking]
- [x] CHK059 - Are all new entities specified as frozen dataclasses with type hints in data-model.md (matching existing `prompt_models.py` patterns)? [Consistency, Constitution §III, data-model.md]
- [x] CHK060 - Are all fallible operations documented as returning `Result[T]` in quickstart.md function signatures? [Consistency, Constitution §III, quickstart.md §Key Patterns]
- [x] CHK061 - Are all magic strings (paths, thresholds, enum values) documented for placement in `config.py` in quickstart.md Phase 1? [Completeness, Constitution §III]
- [x] CHK062 - Is constructor injection documented for all new classes (DomainAnalyzer, ServiceMapper, CommunicationPlanner, ManifestWriter)? [Consistency, Constitution §III, quickstart.md]
- [x] CHK063 - Is the dependency flow preserved (cli → core → stdlib only) with no reverse imports documented? [Consistency, Constitution §VI, plan.md §Constitution Check]

---

## Cross-Artifact Consistency

- [x] CHK064 - Does the plan.md Technical Context's "Primary Dependencies" line mention Jinja2 for manifest generation (matching the `manifest.json.j2` decision in research.md)? [Consistency, plan.md §Technical Context vs research.md §Task 2] — PASS: Technical Context updated to reference both `communication-map.md.j2` and `manifest.json.j2`.
- [x] CHK065 - Does the manifest-schema.md contract's `features[]` schema include `display_name` and `category` fields present in data-model.md but absent from spec §FR-024? [Consistency, Spec §FR-024 vs data-model.md vs manifest-schema.md] — PASS: `category` is in spec FR-024. `display_name` deviation documented in plan.md Complexity Tracking.
- [x] CHK066 - Is the `events` array in manifest-schema.md consistent with the Event entity in data-model.md (same fields, types, constraints)? [Consistency]
- [x] CHK067 - Does the quickstart.md atomic write pattern match the research.md Task 3 implementation (including `os.fsync()` before close)? [Consistency, quickstart.md §Key Patterns vs research.md §Task 3] — PASS: Both include `os.fsync(fd)` before close.
- [x] CHK068 - Are the state file deletion conditions consistent between data-model.md ("complete: state file deleted") and research.md ("On successful completion, delete the state file")? [Consistency]

---

## Summary

| Category | Items | Pass | Fail | Pass Rate |
|----------|-------|------|------|-----------|
| Specification Completeness — Design Traceability | 7 | 7 | 0 | 100% |
| Architecture Decision Gate | 8 | 8 | 0 | 100% |
| Feature Decomposition | 8 | 8 | 0 | 100% |
| Service Mapping (Microservice) | 9 | 9 | 0 | 100% |
| Communication Planning | 5 | 5 | 0 | 100% |
| Manifest | 7 | 7 | 0 | 100% |
| Integration with Features 001–003 | 6 | 6 | 0 | 100% |
| Testing | 6 | 6 | 0 | 100% |
| Code Quality (Constitution) | 7 | 7 | 0 | 100% |
| Cross-Artifact Consistency | 5 | 5 | 0 | 100% |
| **TOTAL** | **68** | **68** | **0** | **100%** |

### Gaps Found (0)

All 68 checklist items now pass.

### Gaps Resolved (13) — Fixed across analysis and remediation passes

| ID | Category | Resolution |
|----|----------|------------|
| CHK011 | Architecture Gate | Remap transition table added to cli-contract.md |
| CHK027 | Service Mapping | 4 WHY SEPARATE templates added to research.md |
| CHK030 | Service Mapping | DFS cycle detection algorithm added to research.md |
| CHK032 | Service Mapping | "User prompted to reassign" specified in cli-contract.md |
| CHK037 | Communication | `override` edit command added to cli-contract.md |
| CHK038 | Manifest | `display_name` deviation documented in plan.md Complexity Tracking |
| CHK040 | Manifest | quickstart.md already includes `os.fsync(fd)` — re-verified |
| CHK044 | Manifest | `display_name` deviation documented in plan.md Complexity Tracking |
| CHK051 | Testing | UT IDs mapped to specific methods in quickstart.md |
| CHK055 | Testing | TDD ordering added to quickstart.md §Implementation Order |
| CHK064 | Cross-Artifact | plan.md Technical Context updated for manifest.json.j2 |
| CHK065 | Cross-Artifact | `display_name` deviation documented in Complexity Tracking |
| CHK067 | Cross-Artifact | quickstart.md confirmed consistent with research.md |
