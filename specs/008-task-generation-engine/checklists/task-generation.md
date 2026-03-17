# Checklist: Task Generation Requirements Quality

**Type**: Implementation requirements quality  
**Feature**: 008-task-generation-engine  
**Purpose**: Validate that the spec and plan requirements for task generation are complete, clear, consistent, and measurable — as unit tests for the English requirements  
**Created**: 2026-03-17  
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

---

## Microservice Build Sequence Completeness

- [ ] CHK001 - Are all 14 microservice build steps enumerated with explicit dependency chains in the plan? [Completeness, Plan §D4]
- [ ] CHK002 - Is the dependency relationship between each microservice step and its prerequisites explicitly defined (e.g., step 6 depends on step 5)? [Clarity, Plan §D4]
- [ ] CHK003 - Are the conditional inclusion/exclusion criteria for each microservice step specified (e.g., "omit step 6 if no dependencies")? [Completeness, Spec §FR-014, Plan §D4]
- [ ] CHK004 - Is the `parallelizable_with` relationship documented for every microservice step that can run concurrently (e.g., steps 6, 7, 8 after step 5)? [Completeness, Plan §D4]
- [ ] CHK005 - Are the file path patterns for all 14 microservice steps specified with `{service}` placeholders? [Completeness, Plan §D4]
- [ ] CHK006 - Is the mapping from manifest `communication` entries (sync-rest, sync-grpc, async-event) to specific microservice steps documented? [Gap, Spec §US1]

## Monolith Build Sequence Completeness

- [ ] CHK007 - Are all 7 monolith build steps enumerated with explicit dependency chains? [Completeness, Plan §D4]
- [ ] CHK008 - Is the shared database context requirement for step 3 (database migrations) explicitly specified with the context name pattern? [Clarity, Spec §FR-012]
- [ ] CHK009 - Is the conditional inclusion of step 6 (boundary interface) clearly scoped to `modular-monolith` only, with explicit exclusion for plain `monolithic`? [Clarity, Spec §FR-013, US3 §AC3]
- [ ] CHK010 - Are the file path patterns for monolith steps specified with `{module}` placeholders distinct from microservice `{service}` patterns? [Consistency, Plan §D4]
- [ ] CHK011 - Is the exclusion list for monolith mode exhaustive — are all 7 microservice-only concerns (container, gRPC, circuit breaker, service discovery, gateway, health check, contract tests) explicitly named? [Completeness, Spec §FR-011]
- [ ] CHK012 - Is the step 3 (database) omission criterion for monolith modules without database entities specified? [Completeness, Spec §US3 §AC4, Plan §D4]

## Cross-Service Task Deduplication

- [ ] CHK013 - Is the requirement that cross-service tasks appear in a separate `cross-service-infra/tasks.md` file (not inline in service files) unambiguously stated? [Clarity, Spec §FR-008, Clarification Q1]
- [ ] CHK014 - Is the `X-T` prefix namespace for cross-service task IDs documented to prevent collision with per-service `T` prefix? [Clarity, Plan §D5, Research §R-004]
- [ ] CHK015 - Is the `[XDEP: cross-service-infra/X-T00N]` notation defined with a parseable format specification? [Clarity, Spec §FR-010]
- [ ] CHK016 - Are all 5 cross-service task categories (shared contracts, docker compose, message broker, gateway, shared auth) explicitly enumerated with their `X-T` IDs? [Completeness, Plan §D5]
- [ ] CHK017 - Is the conditional filtering of cross-service tasks specified (e.g., no message broker task if no async events exist)? [Completeness, Plan §D5 §Step4]
- [ ] CHK018 - Is the architecture guard requiring `generate()` to return empty for monolithic architecture explicitly defined? [Clarity, Plan §D5]
- [ ] CHK019 - Does FR-009 ("MUST NOT duplicate") have measurable acceptance criteria for detecting duplication? [Measurability, Spec §FR-009]

## Dependency-Driven Task Generation (gRPC Clients)

- [ ] CHK020 - Is the rule that gRPC client tasks are generated for EVERY service listed in `service_ctx.dependencies` explicitly stated? [Completeness, Spec §US1 §AC1]
- [ ] CHK021 - Is the dependency relationship between gRPC client tasks and the service layer task (step 5 → step 6) clearly specified? [Clarity, Plan §D4]
- [ ] CHK022 - Is the behavior specified when a dependency target does not exist in the manifest (e.g., missing `payment-service`)? [Edge Case, Spec §Edge Cases]
- [ ] CHK023 - Are file path patterns for generated gRPC clients specified with the dependent service name (e.g., `src/{service}/infrastructure/clients/{target}-client`)? [Clarity, Plan §D4]
- [ ] CHK024 - Is the XDEP link from per-service gRPC client tasks to `cross-service-infra/X-T001` (shared contracts) documented as a required dependency? [Completeness, Spec §FR-010, Plan §D5]

## Event Handler Task Generation

- [ ] CHK025 - Is the mapping from manifest `events` entries (producer/consumer pairs) to event handler tasks (step 8) explicitly defined? [Completeness, Spec §US1 §AC4]
- [ ] CHK026 - Are event handler tasks required to specify producer vs consumer roles per the manifest's `EventInfo.producer` and `EventInfo.consumers` fields? [Clarity, Spec §US1 §AC4]
- [ ] CHK027 - Is the conditional omission of step 8 (event handlers) when `service_ctx.events` is empty explicitly documented? [Completeness, Plan §D4]
- [x] CHK028 - Is the XDEP link from event handler tasks to `cross-service-infra/X-T003` (message broker setup) documented as a required dependency? [Resolved] ✅ Added to T024 test assertions and plan §D5 architecture scope table
- [x] CHK029 - Are requirements specified for services that are BOTH producer and consumer of the same event? [Resolved] ✅ T024b edge case test added for bidirectional events; bidirectional_events_manifest.json fixture added

## Effort Estimation Architecture Differentiation

- [ ] CHK030 - Are default effort sizes (S/M/L/XL) assigned to EVERY build step for both microservice and monolith sequences? [Completeness, Plan §D4]
- [ ] CHK031 - Do effort defaults differ between architectures where appropriate (e.g., monolith database=M vs microservice database=L due to per-service context overhead)? [Consistency, Plan §D4, §D6]
- [ ] CHK032 - Are the effort bump rules for high feature counts (>3 features bumps M→L) specified with measurable thresholds? [Measurability, Plan §D6]
- [ ] CHK033 - Is the effort bump rule for high dependency counts (>2 deps on gRPC clients step) quantified? [Measurability, Plan §D6]
- [ ] CHK034 - Is the effort cap at XL (never exceeds) explicitly stated as a hard constraint? [Clarity, Plan §D6]
- [x] CHK035 - Are effort bump rules specified for all 14 microservice build steps? [Resolved] ✅ Complete 14-row bump table added to Plan §D6

## Governance Rule References (Feature 003 Integration)

- [x] CHK036 - Is the scope-to-layer mapping for governance rules fully defined for all 14 build steps? [Clarity, Plan §D7, Research §R-005] ✅ Complete mapping table added to Plan §D7 and Research §R-005
- [ ] CHK037 - Is the read-only contract with Feature 003 prompt files unambiguously specified (no writes, no modifications)? [Clarity, Spec §FR-021]
- [ ] CHK038 - Is the graceful degradation behavior specified when governance files don't exist (empty tuple fallback, omit `Prompt-rules:` line)? [Completeness, Plan §D7]
- [x] CHK039 - Are the rule IDs in task output (e.g., `ARCH-001`, `BACK-001`) required to match actual `PromptRule.rule_id` values from loaded governance files using Feature 003 namespace prefixes (ARCH-, BACK-, SEC-, DB-, TEST-, FRONT-, CICD-)? [Consistency, Spec §FR-021] ✅ All examples updated to use Feature 003 namespace
- [ ] CHK040 - Is the architecture applicability filter for governance rules defined (e.g., microservice rules don't apply in monolith mode)? [Completeness, Plan §D7 §Step3]
- [x] CHK041 - Is it specified which governance domains (backend, security, testing, etc.) map to which task layers? [Resolved] ✅ Complete mapping table in Plan §D7 covers all 5 scope types + unmapped fallback

## Parallelization Marker Correctness

- [ ] CHK042 - Is the parallelization criterion (file-path disjointness at the same dependency depth level) precisely defined? [Clarity, Plan §D3, Research §R-002]
- [ ] CHK043 - Are the `parallelizable_with` relationships in the build sequence validated against file path patterns to ensure no false parallels? [Consistency, Plan §D4]
- [ ] CHK044 - Is the algorithm for computing dependency depth levels documented (topological depth: 0 = no deps)? [Clarity, Plan §D3 §DependencyGraph]
- [ ] CHK045 - Are explicit examples of correct parallel marking provided (e.g., controllers ∥ event_handlers after service_layer)? [Clarity, Plan §D4]
- [ ] CHK046 - Are explicit examples of non-parallel siblings provided (e.g., unit_tests NOT parallel with integration_tests despite same depth)? [Clarity, Spec §US4 §AC3]
- [ ] CHK047 - Is the behavior specified when ALL tasks at a depth level have disjoint paths (all marked `[P]`) vs when NONE do (none marked)? [Coverage, Gap]
- [x] CHK048 - Does the spec define how parallel markers interact with cross-file XDEP dependencies (can a task be `[P]` if it has an XDEP)? [Resolved] ✅ XDEP dependencies are cross-file — parallel markers apply within a single task file only. A task with an XDEP can still be `[P]` relative to siblings in the same file if their local file paths are disjoint. The XDEP is an ordering constraint across files, not within a file.

## Cross-Cutting Requirements Quality

- [ ] CHK049 - Is the 50-task cap (FR-018) specified with a clear grouping strategy for when the cap is triggered? [Measurability, Spec §FR-018, Research §R-003]
- [ ] CHK050 - Is the task format (`T001 [P] [US1] [Layer:domain] Description`) defined with a parseable grammar or regex? [Clarity, Plan §D9]
- [ ] CHK051 - Are conventional commit message patterns per task category defined (e.g., `feat(service): ...` for implementation, `test(service): ...` for tests)? [Completeness, Plan §D1 TaskItem.commit_message]
- [ ] CHK052 - Is the backup strategy (tasks.md → tasks.md.bak) specified for the case where tasks.md.bak already exists (overwrite previous backup)? [Edge Case, Research §R-006]
- [x] CHK053 - Are the "required sections" that plan.md must contain before task generation defined? [Resolved] ✅ FR-015 updated: Summary, Technical Context, Design Decisions (minimum)
- [ ] CHK054 - Is the `generate_for_project` behavior specified for mixed architectures (e.g., if manifest declares both services and modules)? [Gap]
- [ ] CHK055 - Are the performance requirements (≤10s single service, ≤30s full project) defined with specific hardware/scale assumptions? [Measurability, Spec §SC-001, §SC-007]

---

## Notes

- All 8 user-specified must-have focus areas are covered (CHK001-006: microservice ordering, CHK007-012: monolith ordering, CHK013-019: cross-service dedup, CHK020-024: gRPC clients, CHK025-029: event handlers, CHK030-035: effort estimates, CHK036-041: governance rules, CHK042-048: parallel markers)
- 2 remaining `[Gap]` items (CHK047 behavior when all tasks disjoint, CHK054 mixed architecture). 5 prior gaps resolved (CHK028, CHK029, CHK035, CHK041, CHK048). 2 ambiguities resolved (CHK039, CHK053).
- 3 `[Ambiguity]` / `[Edge Case]` items flagged for clarification (CHK022, CHK052, CHK053)
- Traceability: 53 of 55 items (96%) reference specific spec/plan sections
