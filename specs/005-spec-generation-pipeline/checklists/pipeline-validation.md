# Pipeline Validation Checklist: Spec Generation Pipeline

**Purpose**: Validate requirements quality across pipeline mechanics, architecture adaptation, multi-feature services, and cross-feature integration
**Created**: 2026-03-16
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md)

## Pipeline Mechanics — Requirement Completeness

- [x] CHK001 Are all 6 pipeline phases explicitly defined with their execution order and dependencies? [Completeness, Spec §FR-002]
- [x] CHK002 Is the parallel execution requirement for phases 3a and 3b specified with failure-independence semantics (one can succeed while the other fails)? [Completeness, Spec §FR-005, US6 Scenario 2]
- [x] CHK003 Is the `.pipeline-state.json` schema fully defined with all fields, types, and valid status values? [Completeness, Data Model §PipelineState + §PhaseStatus]
- [x] CHK004 Is the locking strategy specified with creation mechanism, cleanup behavior, and stale detection threshold? [Completeness, Spec §FR-014 through §FR-018]
- [x] CHK005 Are phase re-run skip conditions clearly specified, including the `--force` override and interrupted-phase recovery? [Completeness, Spec §FR-010, §FR-012, §FR-013]
- [x] CHK006 Is service name resolution from manifest.json specified for both slug-based and feature-number-based inputs? [Completeness, Spec §FR-054, §FR-055, §FR-056]

## Pipeline Mechanics — Requirement Clarity

- [x] CHK007 Is "phase prerequisite completion" unambiguously defined — does it mean state says "complete", or does it check artifact file existence, or both? [Clarity, Spec §FR-007]
  - **Finding**: FR-007 says "prerequisite phases are not complete" and FR-013 handles in-progress recovery, but SC-008 adds "no phantom complete states for missing files", implying both checks. The plan (Phase 4 item 3) mentions "detect interrupted phases" but doesn't specify file-existence cross-check. **Recommendation**: Clarify in FR-007 or add FR to reconcile state vs. file existence.
- [ ] CHK008 Is the "30-minute stale lock threshold" specified with rationale for why 30 minutes, and is the override behavior defined (automatic override vs. user confirmation)? [Clarity, Spec §FR-018]
  - **Finding**: FR-018 says "allow override with a warning" but doesn't specify whether override is automatic or requires `--force`. The Assumptions section says "processes running longer are assumed crashed" which implies automatic. **Recommendation**: Clarify whether stale locks auto-override or require `--force`.
- [x] CHK009 Is the `--from` flag behavior specified for prerequisite validation — does `--from plan` check phases 1-3 are complete before starting? [Clarity, Plan §Phase 4 item 2, Contracts §CLI]
- [x] CHK010 Is the feature number pattern clearly defined — is it a zero-padded 3-digit string ("002"), a bare integer ("2"), or both? [Clarity, Spec §FR-055]
  - **Finding**: Spec says `002` consistently (zero-padded), and SC-009 confirms `specforge specify 002`. Plan says "numeric pattern". Consistent enough for implementation.

## Architecture Adaptation — Requirement Completeness

- [x] CHK011 Does the microservice adapter specification enumerate all 5 deployment concerns: containerization, health checks, service registration, circuit breakers, API gateway? [Completeness, Spec §FR-038, SC-005]
- [ ] CHK012 Are gRPC-specific requirements defined for the microservice adapter, or is it limited to REST patterns? [Gap, Spec §FR-038]
  - **Finding**: FR-038 lists "containerization, health checks, service registration, circuit breaker patterns, and API gateway route configuration" but does NOT mention gRPC. User's checklist criteria says "gRPC" but the spec only references "sync-rest" and "async-event" patterns (from Feature 004's communication planner). The plan's MicroserviceAdapter `get_context()` adds "communication_patterns" generically. **Recommendation**: Clarify whether gRPC is a supported communication pattern or if only sync-rest and async-event are in scope.
- [x] CHK013 Does the monolith adapter specification include both module boundary references and shared DB references? [Completeness, Spec §FR-039, Plan §Phase 2 item 3]
- [x] CHK014 Does the modular-monolith adapter specification include interface definitions (FR-052) AND boundary checks (FR-044)? [Completeness, Spec §FR-052, §FR-044]
- [x] CHK015 Are adapter behaviors defined for ALL 7 artifact types, or only for the subset that varies by architecture? [Completeness, Plan §Phase 2]
  - **Finding**: Plan defines 7 adapter methods (get_context, get_datamodel_context, get_research_extras, get_plan_sections, get_task_extras, get_edge_case_extras, get_checklist_extras). Spec generation (Phase 1) uses `get_context()`. Research (Phase 2) uses `get_research_extras()`. Data model (Phase 3a) uses `get_datamodel_context()` for entity scoping. All 7 artifacts are covered through dedicated adapter methods.

## Architecture Adaptation — Requirement Consistency

- [x] CHK016 Are the architecture-conditional template blocks consistent between spec FR requirements and plan adapter method outputs? [Consistency, Spec §FR-022/§FR-023 vs Plan §Phase 2]
- [x] CHK017 Is the modular-monolith behavior consistently defined as "monolith plus extras" across all artifacts, or are there contradictions? [Consistency, Spec §FR-040, §FR-044, §FR-052]
  - **Finding**: Spec treats modular-monolith as monolith + interface definitions + boundary checks. Plan's ModularMonolithAdapter extends MonolithAdapter. Data model doesn't define a separate entity for modular-monolith. Consistent.
- [ ] CHK018 Are event-related requirements (async-event pattern) specified for edge-cases.md generation — does "eventual consistency" in FR-034 cover event delivery failures? [Clarity, Spec §FR-034]
  - **Finding**: FR-034 lists "eventual consistency" and "timeouts" but doesn't explicitly call out event delivery failures (message bus unavailable, duplicate events, out-of-order delivery). The EventInfo entity exists in the data model. **Recommendation**: Consider adding explicit event delivery failure scenarios to FR-034 or the edge case edge cases list.

## Multi-Feature Services — Requirement Completeness

- [x] CHK019 Is the unified spec.md requirement for multi-feature services (e.g., ledger-service with 2 features) specified with acceptance criteria? [Completeness, Spec §FR-019, US1 Scenario 2, SC-006]
- [x] CHK020 Is the domain capability grouping requirement for larger services (3+ features) specified with a threshold and example? [Completeness, Spec §FR-021, US1 Scenario 6]
- [x] CHK021 Are user stories explicitly required to be organized by domain capability rather than feature number? [Completeness, Spec §FR-020]
- [ ] CHK022 Is the "domain capability" grouping algorithm defined — how does the system determine which features belong to which capability group? [Clarity, Spec §FR-020, Plan §Phase 3 item 4]
  - **Finding**: FR-020 says "organize by domain capability" and US1 gives examples ("Account Management", "Transaction Processing"), but neither the spec nor the plan defines HOW capabilities are derived from features. Plan says "groups features by category into domain capabilities" — does this mean the `category` field from FeatureInfo (foundation/core/supporting/integration/admin)? Those are architectural categories, not domain capabilities. **Recommendation**: Define the capability grouping algorithm — likely by `display_name` similarity or explicit capability mapping in the template context.
- [x] CHK023 Is the data-model.md unification requirement specified — does a multi-feature service produce ONE schema covering all features? [Completeness, Spec §FR-032]

## Multi-Feature Services — Edge Case Coverage

- [x] CHK024 Does the spec define behavior when a service has only 1 feature mapped (trivial case)? [Coverage, Spec §US1]
  - **Finding**: US1 Scenario 1 covers identity-service with Feature 001 only. Acceptance criteria are clear.
- [ ] CHK025 Is the maximum number of features per service bounded, and are requirements defined for services with 5+ features (spec.md readability)? [Coverage, Gap]
  - **Finding**: Feature 004 defines MAX_FEATURES_PER_SERVICE = 4 in config.py, but Feature 005's spec doesn't reference this limit or define behavior for edge cases near the boundary. FR-021 triggers sub-sections at 4+ features. SC-001 references "5-feature service" timing. **Recommendation**: Confirm whether MAX_FEATURES_PER_SERVICE from Feature 004 is enforced before the pipeline runs, or if the pipeline must handle arbitrary counts.
- [x] CHK026 Does the spec define what happens when features in the same service have conflicting priorities (e.g., P0 + P3)? [Coverage, Edge Case]
  - **Finding**: Not explicitly addressed, but FeatureInfo preserves individual priority fields and templates can sort/group by priority. Acceptable — spec.md generation merges narratively, not mechanically.

## Integration — Requirement Completeness

- [x] CHK027 Is the TemplateRegistry integration specified with the resolution method (render vs render_raw) and template type? [Completeness, Spec §FR-060, Plan §Phase 3 item 3, Research §R-06]
- [x] CHK028 Is the PromptContextBuilder integration specified with when it's invoked (Phase 4 only) and what task_domain is passed? [Completeness, Spec §FR-063, §FR-064, Plan §Phase 3 item 4]
- [x] CHK029 Is the manifest.json reading specified with the exact schema fields consumed (features, services, architecture, events)? [Completeness, Spec §FR-001, Data Model §ServiceContext, Research §R-05]
- [x] CHK030 Are breaking change risks to Features 001-004 identified and mitigated? [Completeness, Plan §Structure Decision]
  - **Finding**: Plan shows config.py MODIFIED (additive only — new constants), main.py MODIFIED (additive — new add_command calls), 7 templates MODIFIED (additive — new conditional blocks, backward compatible). No deletions or behavioral changes to existing code. Feature 004's template_registry.py _EXCLUDED_FILES is not modified (pipeline templates are NOT excluded — they go through registry resolution). Clean.

## Integration — Requirement Consistency

- [x] CHK031 Is the manifest.json schema consumed by ServiceContext consistent with the schema produced by Feature 004's ManifestWriter? [Consistency, Data Model §ServiceContext vs Feature 004 manifest_writer.py]
  - **Finding**: ServiceContext reads: service slug, name, features[], communication[]. ManifestWriter produces: services[{slug, name, features[], communication[]}], features[{id, name, display_name, description, priority, category, service}]. Fields align. FeatureInfo maps 1:1 to manifest feature entries. ServiceDependency extracts from communication links. Consistent.
- [x] CHK032 Are template context variables consistent between what the plan's adapter methods produce and what existing template variables expect? [Consistency, Plan §Phase 3 vs Research §R-04]
  - **Finding**: Existing templates use `project_name`, `feature_name`, `date`. Plan adds `architecture`, `service`, `features`, `dependencies`, `capabilities`, `adapter_sections`, etc. Templates use `{% if service %}` guards for backward compatibility. Consistent.
- [ ] CHK033 Is the template modification strategy (adding `{% if %}` blocks to existing templates) validated against the TemplateRenderer's context validation? [Consistency, Plan §Phase 6 vs Research §R-06]
  - **Finding**: TemplateRenderer.render() validates context against TemplateVarSchema before rendering. Adding new variables to templates means the schema must be updated to accept optional service-context variables. Neither the spec nor the plan mentions updating TemplateVarSchema. **Recommendation**: Add a task to update TemplateVarSchema (or use render_raw to bypass validation, or make new vars optional in schema).

## Acceptance Criteria Quality

- [x] CHK034 Are all 10 success criteria (SC-001 through SC-010) measurable without implementation knowledge? [Measurability, Spec §Success Criteria]
- [x] CHK035 Is SC-001 ("under 60 seconds") realistic given that the pipeline runs 6 sequential phases plus parallel phase 3? [Measurability, Spec §SC-001]
  - **Finding**: Plan estimates ~5.4s total from the CLI contract output example. Templates are small file renders. 60s is conservative and achievable.
- [x] CHK036 Is SC-007 ("100% of generated artifacts pass checklist validation") achievable given that checklist.md (Phase 5) validates Phase 1-4 artifacts that IT generated? [Measurability, Spec §SC-007]
  - **Finding**: This is a self-consistency check — the pipeline validates its own output. It's achievable by construction (if the pipeline generates correctly, checklist passes). The real test is whether the checklist catches malformed artifacts from template errors.

## Dependencies & Assumptions

- [x] CHK037 Is the assumption "manifest.json exists before pipeline runs" enforced with a clear error path? [Dependencies, Spec §FR-058, Assumptions]
- [x] CHK038 Is the cross-platform file locking assumption documented with the chosen mechanism (O_CREAT|O_EXCL instead of fcntl)? [Dependencies, Research §R-01, Plan §Phase 1 item 7]
- [ ] CHK039 Is the ThreadPoolExecutor parallelism assumption validated against the template rendering engine's thread safety? [Assumption, Research §R-03]
  - **Finding**: Research §R-03 says "Both phases are I/O-bound (template rendering + file writes)" but doesn't address whether Jinja2's Environment object is thread-safe. Jinja2 Environment IS thread-safe for rendering (documented), but TemplateRenderer wraps it with registry lookups. **Recommendation**: Verify TemplateRenderer.render() is safe for concurrent calls or use separate renderer instances per thread.

## Cross-Check Coverage — Architecture Test Coverage

- [x] CHK040 Are integration tests specified for ALL 3 architecture types (microservice, monolith, modular-monolith)? [Coverage, Tasks §Phase 10]
  - **Finding**: T046 covers microservice E2E, T047 covers monolith E2E, T047b covers modular-monolith E2E. All 3 architectures have dedicated integration tests.
- [x] CHK041 Is there an integration test for a single-feature service (minimal path)? [Coverage, Tasks §Phase 10]
  - **Finding**: T047c covers single-feature service E2E — verifies no sub-sections, minimal data model.
- [x] CHK042 Do snapshot golden files exist for all 3 architectures? [Coverage, Tasks §Phase 10]
  - **Finding**: T049 includes spec/plan/datamodel snapshots for microservice, monolith, AND modular-monolith.
- [x] CHK043 Does the ArchitectureAdapter Protocol cover DatamodelPhase and ResearchPhase with dedicated methods? [Completeness, Data Model §ArchitectureAdapter]
  - **Finding**: get_datamodel_context() provides entity scoping rules; get_research_extras() provides architecture-specific research questions. No phase uses raw `architecture` string for conditional logic.
- [x] CHK044 Do templates have explicit three-way conditionals for modular-monolith (not just fallthrough to monolith)? [Completeness, Plan §Phase 6]
  - **Finding**: Templates use `{% if architecture == 'modular-monolith' %}` for strict boundaries, interface contracts, and no cross-module DB. Modular-monolith is NOT treated as implicit monolith fallthrough.
- [x] CHK045 Is graceful degradation specified when Feature 003 governance files are absent? [Completeness, Spec §FR-065]
  - **Finding**: FR-065 specifies plan.md generation proceeds without prompt context injection, no error raised.

## Notes

- CHK008: Stale lock override mechanism needs clarification (auto vs. --force)
- CHK012: gRPC not in spec FRs — either add it or remove from expectations
- CHK018: Event delivery failure scenarios should be explicitly listed in FR-034
- CHK022: Domain capability grouping algorithm is underspecified — needs definition
- CHK025: MAX_FEATURES_PER_SERVICE boundary behavior needs cross-feature clarification
- CHK033: TemplateVarSchema update is missing from plan — add to Phase 6 or Phase 1
- CHK039: Thread safety of TemplateRenderer needs verification before parallel execution
