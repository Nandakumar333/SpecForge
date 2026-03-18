# Orchestration Correctness Checklist: Implementation Orchestrator

**Purpose**: Validate that requirements for phased orchestration, contract enforcement, conflict detection, failure handling, and integration reporting are complete, clear, and consistent across spec.md, plan.md, and data-model.md.
**Created**: 2026-03-17
**Feature**: [spec.md](../spec.md)

## Phase Execution Order & Dependency Graph

- [ ] CHK001 - Is the algorithm for computing phases from the dependency graph specified with enough precision to be deterministic? (Kahn's algorithm is in research.md R-001 but not in spec.md functional requirements) [Clarity, Gap]
- [ ] CHK002 - Are requirements defined for how the dependency graph handles transitive dependencies? (e.g., if C depends on B which depends on A, is it specified that C is placed in a phase after B's phase, not just after A's?) [Completeness, Spec §FR-002]
- [ ] CHK003 - Is the behavior specified when a service has dependencies in multiple earlier phases? (e.g., planning-service depends on both Phase 1 identity and Phase 2 ledger — must be Phase 3) [Completeness, Spec §FR-002]
- [ ] CHK004 - Are requirements defined for validating the computed phase plan against the manifest before execution starts? (i.e., a "dry run" or pre-flight that shows the computed plan) [Gap]
- [ ] CHK005 - Is it specified whether the phase order is displayed to the user before execution begins, allowing them to review/abort? [Coverage, Gap]
- [ ] CHK006 - Are requirements for services with zero dependencies consistently defined? (FR-002 says "no mutual dependencies" but doesn't define the base case — all-independent projects = one phase?) [Clarity, Spec §FR-002]

## Shared Infrastructure Pre-Phase

- [ ] CHK007 - Is the complete list of shared infrastructure components explicitly enumerated? (FR-004 lists "contracts library, docker-compose base, API gateway skeleton, message broker configuration" — is this exhaustive or extensible?) [Completeness, Spec §FR-004]
- [ ] CHK008 - Are requirements defined for what happens when shared infra partially succeeds? (e.g., contracts library builds but gateway skeleton fails — retry just the failed component or restart entire pre-phase?) [Coverage, Gap]
- [ ] CHK009 - Is the ordering of shared infrastructure components specified? (Must contracts library build before docker-compose base, or are they independent?) [Clarity, Spec §FR-004]
- [ ] CHK010 - Are requirements defined for shared infra in modular-monolith mode? (FR-004 says "microservice mode", FR-005 says "monolithic mode" — modular-monolith is unspecified for this pre-phase) [Gap, Spec §FR-004/FR-005]
- [ ] CHK011 - Is it specified that shared infra completion is a hard gate? (i.e., no service can begin until ALL shared infra tasks succeed, not just some) [Clarity, Spec §FR-004]

## Contract Enforcement After Every Phase

- [ ] CHK012 - Is it explicitly stated that contract verification runs after the FINAL implementation phase as well, not just between phases? (FR-008 says "after each phase" — does the last phase trigger verification before integration validation?) [Clarity, Spec §FR-008]
- [ ] CHK013 - Are requirements defined for the scope of "all implemented services" growing cumulatively? (After Phase 3, verification checks Phase 1 + Phase 2 + Phase 3 pairs — is this N² growth acknowledged?) [Coverage, Spec §FR-008]
- [ ] CHK014 - Is the contract comparison algorithm specified? (Structural comparison? Field-by-field? Type-compatible? Exact match?) [Clarity, Gap]
- [ ] CHK015 - Are requirements defined for versioned contracts? (What if a service publishes contract v2 while consumers still expect v1?) [Coverage, Gap]
- [ ] CHK016 - Is it specified what "shared entity boundary analysis" checks for, beyond entity ownership conflicts? (FR-008 references Feature 006 but doesn't define the exact checks) [Clarity, Spec §FR-008]
- [ ] CHK017 - Are requirements defined for contract verification when `--to-phase N` is used? (Does verification still run after the ceiling phase?) [Coverage, Spec §FR-022]

## Docker-Compose Progressive Service Addition

- [ ] CHK018 - Is it specified that inter-phase docker-compose health checks test only services from completed phases (progressive addition), or all declared services? [Clarity, Spec §FR-008]
- [ ] CHK019 - Are requirements defined for how docker-compose is configured to start a subset of services? (Profiles? Selective `docker compose up svc1 svc2`?) [Gap]
- [ ] CHK020 - Is the docker-compose startup timeout specified per phase? (Phase 1 with 2 services vs. final integration with 8+ services may need different timeouts) [Completeness, Gap]
- [ ] CHK021 - Are requirements defined for docker-compose teardown between phases? (Do services stay running across phases, or are they brought down and re-started with the new phase's services added?) [Gap]
- [ ] CHK022 - Is it specified what happens when docker-compose health check fails for a previously-passing service after a new phase's services are added? [Edge Case, Gap]

## Conflict Detection: Routes, Schemas, Naming

- [ ] CHK023 - Are API route conflict detection requirements defined? (Two services claiming the same gateway route path) [Gap]
- [ ] CHK024 - Are event schema naming conflict requirements defined? (Two services publishing events with the same name but different schemas) [Gap]
- [ ] CHK025 - Are service naming collision requirements specified? (e.g., two services with slugs that produce identical Docker container names or port assignments) [Gap]
- [ ] CHK026 - Are database schema naming conflict requirements defined for monolith mode? (Two modules claiming the same table name or schema namespace) [Completeness, Spec §FR-026]
- [ ] CHK027 - Is the term "conflict detection" distinguished from "contract verification"? (Spec uses both concepts but doesn't clearly differentiate when each applies) [Clarity, Gap]
- [ ] CHK028 - Are requirements defined for message broker queue/topic naming conflicts between services? [Gap]

## Monolith Mode Simplified Orchestration

- [ ] CHK029 - Is the complete list of microservice-specific features SKIPPED in monolith mode exhaustively defined? (FR-005 says "shared infra skipped", FR-012 says "monolith integration test" — but are all skip conditions listed in one place?) [Completeness, Spec §FR-005/FR-010/FR-012]
- [ ] CHK030 - Are module boundary compliance check criteria quantified? (FR-010 says "no cross-module direct data access" — is "direct data access" defined precisely?) [Clarity, Spec §FR-010]
- [ ] CHK031 - Is the monolith integration test approach specified beyond "single application with all modules enabled"? (What constitutes "enabled"? What test suite runs?) [Clarity, Spec §FR-012]
- [ ] CHK032 - Are requirements consistent between US4 scenarios and FR-005/FR-010/FR-012? (US4 §3 says "end-to-end test suite" but FR-012 says "monolith integration test" — same thing?) [Consistency, Spec §US4/FR-012]
- [ ] CHK033 - Are requirements defined for modular-monolith as a distinct mode from monolithic? (FR-010 defines boundary checks for "modular monolith" but no user story explicitly covers modular-monolith orchestration flow end-to-end) [Coverage, Gap]

## Failure Handling Per Phase

- [ ] CHK034 - Is the continue-then-halt policy clearly stated as a requirement, not just a clarification? (Currently in Clarifications section and FR-020, but US1 scenario 4 is the primary reference) [Clarity, Spec §FR-020]
- [ ] CHK035 - Is "no rollback" explicitly documented as a deliberate design choice, with rationale? (Edge case mentions "fix forward" but no FR states this) [Completeness, Gap]
- [ ] CHK036 - Are requirements defined for the interaction between service failure and contract verification? (If 2 of 3 Phase 2 services succeed but one fails, does contract verification run for the 2 that succeeded?) [Coverage, Gap]
- [ ] CHK037 - Is the behavior specified when a phase has a mix of completed and failed services AND contract verification also fails? (Two independent failure modes — which is reported first? Both?) [Coverage, Gap]
- [ ] CHK038 - Are requirements defined for `--resume` behavior after a phase with partial failures? (Does it re-try the failed service only, or re-run the entire phase?) [Clarity, Spec §FR-014/FR-020]
- [ ] CHK039 - Is it specified what state the orchestration is left in after a halt? (Status = "halted"? "failed"? Does it differ between service failure and verification failure?) [Clarity, Gap]
- [ ] CHK040 - Are requirements defined for user intervention options after a halt? (Only `--resume`? Or also `--skip-failed`, `--force-next-phase`?) [Coverage, Gap]

## Integration Report Contents

- [ ] CHK041 - Is the integration report format specified? (Markdown? JSON? Both?) [Clarity, Spec §FR-017]
- [ ] CHK042 - Is the report output path specified? (Where is `integration-report.md` written? Project root? `.specforge/`?) [Completeness, Gap]
- [ ] CHK043 - Are all three required sections (service status, contract results, test results) explicitly listed in FR-017? (FR-017 says "services implemented per phase, verification results at each boundary, integration validation results" — close but not exact match to user's expectation) [Consistency, Spec §FR-017]
- [ ] CHK044 - Are requirements defined for what the report includes when orchestration fails mid-run? (Does it report only completed phases, or also show what was planned but not executed?) [Coverage, Spec §FR-017]
- [ ] CHK045 - Is the report's "overall status/verdict" field defined with specific possible values? (Data model says `pass | fail | partial` — is this reflected in spec FR-017?) [Consistency, Spec §FR-017 / data-model.md §IntegrationReport]
- [ ] CHK046 - Are requirements defined for elapsed time tracking in the report? (US7 §2 mentions "total elapsed time" but FR-017 does not) [Consistency, Spec §US7/FR-017]
- [ ] CHK047 - Is it specified whether the report includes per-service task completion counts? (Data model has `tasks_completed` and `tasks_total` in ServiceStatus — is this surfaced in the report?) [Completeness, Gap]

## Notes

- **Focus areas**: 8 user-specified orchestration correctness domains
- **Depth**: Standard — covers requirement completeness, clarity, consistency, and gap detection
- **Audience**: Reviewer (design review / PR review)
- **Must-have items incorporated**: All 8 user-specified focus areas mapped to dedicated sections
- **Key gaps identified**: Progressive docker-compose (CHK018-022), conflict detection specifics (CHK023-028), and failure handling interaction modes (CHK036-040) have the most [Gap] markers, suggesting these areas need the most spec refinement
