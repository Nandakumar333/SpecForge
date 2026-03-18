# Integration Quality Checklist: Project Status Dashboard

**Purpose**: Validate requirements completeness, clarity, and consistency across the 5 critical integration areas: state file collection, architecture-adaptive display, JSON schema stability, no-state service handling, and phase blocking logic.  
**Created**: 2026-03-18  
**Feature**: [spec.md](../spec.md)

## Requirement Completeness — State File Collection

- [x] CHK001 — Are ALL state file types that must be read explicitly enumerated in functional requirements, not just assumptions? Currently FR-002 and FR-005 reference data sources implicitly while the Assumptions section lists them. [Completeness, Gap — cross-ref Spec §Assumptions vs §FR-002/FR-005] *Addressed: data-model.md "Relationship to Existing Models" table explicitly maps each field to source. T009 annotated with FR-014 traceability.*
- [x] CHK002 — Is the expected behavior specified for when `.orchestration-state.json` does not exist (pre-orchestration projects where `implement --all` has never been run)? [Edge Case, Gap — Spec §Edge Cases] *Addressed: research.md R2 step 7 + T013 test_calculate_phase_progress_no_orchestration_state.*
- [x] CHK003 — Are the derivation rules for each lifecycle column (spec, plan, tasks, impl%, tests, docker) explicitly mapped to their source state file fields? [Clarity — Data-Model §LifecyclePhases Derivation Rules] *Addressed: data-model.md LifecyclePhases derivation notes + Relationship table.*
- [x] CHK004 — Is it specified how quality reports at `level: "task"` vs `level: "service"` are aggregated to produce the per-service quality summary? [Clarity, Gap — Spec §FR-005 references quality reports but does not distinguish levels] *Addressed: data-model.md "QualityReport Aggregation" section added by analyze.*
- [x] CHK005 — Are the pipeline phase names that map to lifecycle columns (`spec`, `plan`, `tasks`) explicitly listed, given that `PipelineState` has 7 phases (spec, research, datamodel, edgecase, plan, checklist, tasks)? Which phases map to the 3 displayed columns? [Completeness, Gap — Spec §FR-002 shows 3 columns but source has 7 phases] *Addressed: data-model.md Relationship table maps LifecyclePhases.spec/plan/tasks to PipelineState.phases[].status.*
- [x] CHK006 — Is the behavior specified when a service has a pipeline state but no execution state (meaning spec pipeline ran but implementation has not started)? Is this PLANNING or NOT_STARTED? [Clarity, Gap — Spec §FR-003 status derivation rules] *Addressed: research.md R2 waterfall step 5: pipeline in-progress → PLANNING.*

## Requirement Clarity — Architecture-Adaptive Display

- [x] CHK007 — Is the complete column set explicitly defined per architecture type? FR-009 specifies Docker omission for non-microservice but does not enumerate the full column list for each mode. [Clarity, Spec §FR-009] *Addressed: data-model LifecyclePhases fields define the complete column set; FR-009 + plan.md architecture section cover adaptive columns.*
- [x] CHK008 — Are contract test columns also explicitly scoped to microservice-only, or is this implied? FR-005 mentions "contract test results (microservice only)" in the quality summary but FR-002 does not mention contract columns in the service table. [Consistency, Spec §FR-002 vs §FR-005] *Addressed: FR-005 explicitly scopes contract tests to microservice. QualitySummaryRecord has contract_* fields as "None for non-microservice".*
- [x] CHK009 — Is "module boundary compliance" as a replacement column for Docker in modular-monolith mode defined with measurable pass/fail criteria? [Clarity, Spec §US1 AS3] *Addressed: data-model LifecyclePhases.boundary_compliance + QualityReport BOUNDARY category provides pass/fail.*
- [x] CHK010 — Are the column header labels specified (e.g., is it "Docker", "Docker Build", or "Container Status")? [Clarity, Gap — Spec §FR-002 uses informal names] *Addressed: implementation discretion per T034; spec intentionally uses informal names.*
- [x] CHK011 — Is it specified whether the architecture badge text matches the `manifest.json` values exactly (`"microservice"`, `"monolithic"`, `"modular-monolith"`) or uses display labels (`[MICROSERVICE]`, `[MONOLITH]`, `[MODULAR]`)? Spec §FR-001 and §US1 use different capitalizations. [Consistency, Spec §FR-001 vs §US1] *Addressed: FR-003 now clarifies display format vs data-model format. Badge uses display labels.*
- [x] CHK012 — Is the table column ordering specified, or left to implementation discretion? [Completeness, Gap — Spec §FR-002 lists columns but not their display order] *Addressed: implementation discretion; T034 defines rendering order.*

## Requirement Consistency — JSON Schema for CI/CD

- [x] CHK013 — Is a schema versioning strategy specified for `status.json` to handle future field additions without breaking CI/CD consumers? [Gap — Spec §FR-018 defines field contract but not evolution strategy] *Addressed: JSON schema changed from const "1.0" to pattern "^1\\." for minor-version tolerance.*
- [x] CHK014 — Are backward compatibility guarantees documented for the JSON schema (e.g., additive-only changes, no field removals)? [Gap — critical for CI/CD stability per US5] *Addressed: schema has no additionalProperties:false, uses pattern-based version, warnings now required.*
- [x] CHK015 — Is the JSON `status` field enum (`COMPLETE`, `IN_PROGRESS`, etc.) consistent between the spec (uses spaces: "IN PROGRESS") and the JSON schema contract (uses underscores: `IN_PROGRESS`)? [Consistency, Spec §FR-003 vs contracts/status-json-schema.json] *Addressed: FR-003 now explicitly states display format uses spaces, data-model/JSON uses underscores.*
- [x] CHK016 — Are the `phases` array entries guaranteed to be ordered by `index`? Is this ordering requirement documented? [Clarity, Gap — Spec §US5 AS3 assumes phases can be queried by index] *Addressed: PhaseProgressRecord has phase_index field; implementation sorts by index.*
- [x] CHK017 — Is it specified whether `status.json` includes the `warnings` array (from corrupted state files) so CI/CD consumers can detect degraded status reads? [Completeness, Gap — FR-010 defines graceful handling but not JSON representation of warnings] *Addressed: warnings added to JSON schema required array.*
- [x] CHK018 — Are the `null` vs absent field semantics consistent? FR-018 says "set to `null` (not omitted)" — is this requirement also applied to quality summary fields (e.g., `coverage_avg: null` when no data)? [Consistency, Spec §FR-018 scopes to lifecycle fields only] *Addressed: JSON schema uses ["number", "null"] for optional quality fields, consistent with lifecycle pattern.*

## Scenario Coverage — Services with No State

- [x] CHK019 — Is the distinction between "service directory doesn't exist" vs "service directory exists but state files are empty/missing" specified? Both could result in NOT_STARTED but have different diagnostic implications. [Clarity, Gap — Spec §FR-015] *Addressed: data-model ServiceRawState defines None (file doesn't exist) vs Err (corrupt) vs Ok (valid).*
- [x] CHK020 — Is the transition from NOT_STARTED to PLANNING precisely defined? Is it triggered when the service's `.pipeline-state.json` first appears, or when its first phase enters `in-progress`? [Clarity, Gap — Spec §FR-003 lists status labels but not transition triggers] *Addressed: data-model State Transitions: "NOT_STARTED → PLANNING: First pipeline phase (spec) transitions to in-progress".*
- [x] CHK021 — Does the spec define what features column shows for a manifest-declared service with no feature mapping? (e.g., a shared infrastructure pseudo-service) [Edge Case, Gap — Spec §FR-013] *Addressed: ServiceStatusRecord.features is tuple[str, ...] — empty tuple shows "-" in display.*
- [x] CHK022 — Is it specified whether NOT_STARTED services contribute to phase progress calculations? (e.g., does a NOT_STARTED service in Phase 2 reduce Phase 2's completion percentage?) [Completeness, Gap — Spec §FR-004 does not address NOT_STARTED service weight in phase calculations] *Addressed: T013 added test_calculate_phase_progress_not_started_services_reduce_percent.*
- [x] CHK023 — Are requirements defined for the JSON representation of a service that has a pipeline state (partially through spec pipeline) but no execution state? Should `implementation_percent` be `0` or `null`? [Clarity, Gap — Spec §FR-018 only covers "no artifacts" case] *Addressed: data-model derivation rule updated — impl_percent=0 when execution state has 0 tasks or is absent.*

## Edge Case Coverage — Phase Blocking Dependencies

- [x] CHK024 — Is the blocking determination precisely defined? Is a service BLOCKED only when its dependency phase has a FAILED service, or also when the dependency phase is simply incomplete (IN PROGRESS)? [Clarity, Spec §FR-003 says "dependencies incomplete" — define "incomplete"] *Addressed: research.md R2 step 3 + data-model transition: "Service's dependency phase is not completed in orchestration state". Incomplete = not all services in dependency phase have status COMPLETE.*
- [x] CHK025 — Are phase blocking rules specified for monolith projects that have a flat dependency graph (no phases)? US2 AS4 says "phase section is omitted or shows single group" — which one? [Ambiguity, Spec §US2 AS4] *Addressed: T013 test_calculate_phase_progress_monolith returns empty phases (omitted).*
- [x] CHK026 — Is it specified whether a service can be BLOCKED and FAILED simultaneously (e.g., dependency incomplete AND own quality gate failed)? Or does FAILED take precedence? [Clarity, Gap — Spec §FR-003 lists statuses but not precedence rules] *Addressed: research.md R2 priority waterfall: step 2 (FAILED) takes precedence over step 3 (BLOCKED).*
- [x] CHK027 — Is it documented how the `blocked_by` field is determined when a phase depends on multiple prior phases and only some are incomplete? [Completeness, Gap — Data-Model §PhaseProgressRecord.blocked_by is singular int but blocking could be multi-phase] *Addressed: tracks first/primary blocking phase; acceptable simplification.*
- [x] CHK028 — Are requirements specified for what happens when orchestration state defines phases but manifest dependencies have changed since last orchestration run (stale phase data)? [Edge Case, Gap] *Addressed: collector reads orchestration as-is; FR-010 handles graceful degradation for stale data.*
- [x] CHK029 — Is the phase progress percentage formula documented in the spec or only in research.md? If it's a requirement (not just design), should it be in the spec? [Traceability — Research §R3 defines formula but Spec §FR-004 says only "calculated from aggregate status"] *Addressed: FR-004 is the requirement; research.md R3 is the design decision. Traceability is acceptable.*

## Notes

- Check items off as completed: `[x]`
- Items referencing `[Gap]` identify requirements that may need to be added to the spec
- Items referencing `[Consistency]` identify potential mismatches between spec sections
- Items referencing `[Clarity]` identify requirements that may need more precise language
- 28 of 29 items (97%) include traceability references
