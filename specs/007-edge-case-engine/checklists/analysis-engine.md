# Checklist: Analysis Engine Requirements Quality

**Purpose**: Validate that the edge case analysis engine requirements are complete, unambiguous, and architecture-aware — covering microservice categories, monolith filtering, communication map integration, YAML contract stability, and output budgeting.
**Created**: 2026-03-17
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md)
**Depth**: Standard | **Audience**: Reviewer (PR) | **Focus**: Architecture-aware analysis, category completeness, machine-parseability contract

---

## Microservice Category Completeness

- [ ] CHK001 - Are all 6 microservice-specific edge case categories explicitly enumerated in requirements? (service_unavailability, network_partition, eventual_consistency, distributed_transaction, version_skew, data_ownership) [Completeness, Spec §FR-002]
- [ ] CHK002 - Is each microservice category defined with a distinct scenario description that differentiates it from the other 5? [Clarity, Spec §FR-002]
- [ ] CHK003 - Are the trigger conditions for each microservice category specified? (e.g., 503 response for service_unavailability, message loss for eventual_consistency) [Completeness, Spec §FR-002]
- [ ] CHK004 - Is the mapping between communication pattern types (sync-rest, sync-grpc, async-events) and applicable microservice categories documented? [Clarity, Spec §FR-008]
- [ ] CHK005 - Are recommended handling strategies defined for each microservice category? (e.g., circuit breaker for service_unavailability, outbox for distributed_transaction) [Completeness, Spec §FR-019]
- [ ] CHK006 - Does the spec define which microservice categories apply to sync vs async dependencies? [Clarity, Spec §FR-008, §FR-009]
- [ ] CHK007 - Is the version_skew category scope defined — does it cover API contract changes, JWT claim changes, or both? [Clarity, Spec §FR-002]
- [ ] CHK008 - Is the data_ownership category trigger condition specified — only shared entities from BoundaryAnalyzer, or also explicit manifest references? [Clarity, Spec §FR-014]

## Monolith Standard Categories

- [ ] CHK009 - Are all 6 standard monolith categories explicitly enumerated? (concurrency, data_boundary, state_machine, ui_ux, security, data_migration) [Completeness, Spec §FR-003]
- [ ] CHK010 - Is each standard category defined with a scenario description relevant to monolith architectures? [Clarity, Spec §FR-003]
- [ ] CHK011 - Does the spec explicitly state that monolith mode generates ZERO distributed-system categories? [Clarity, Spec §FR-003, §SC-002]
- [ ] CHK012 - Are modular-monolith requirements specified as superset of monolith (standard categories + interface_contract_violation)? [Completeness, Spec §FR-004]
- [ ] CHK013 - Is the interface_contract_violation category scope defined for modular-monolith — module-level or service-interface-level? [Clarity, Spec §FR-004]
- [ ] CHK014 - Are standard category handling strategies appropriate for monoliths? (e.g., no "circuit breaker" for concurrency — should be locking/mutex patterns) [Consistency, Spec §FR-019]

## Architecture Filter Requirements

- [ ] CHK015 - Is the ArchitectureEdgeCaseFilter's filtering logic explicitly defined for all 3 architecture types? (monolithic, microservice, modular-monolith) [Completeness, Spec §FR-001, Plan §D3]
- [ ] CHK016 - Does the spec define which categories are REMOVED per architecture, not just which are included? (negative specification for safety) [Clarity, Spec §FR-003, §FR-015]
- [ ] CHK017 - Is the filtering behavior specified when architecture type is unknown or missing from manifest? [Edge Case, Gap]
- [ ] CHK018 - Is the interaction between ArchitectureEdgeCaseFilter and ArchitectureAdapter.get_edge_case_extras() specified — does filtering apply to adapter extras or only to pattern-generated cases? [Consistency, Spec §FR-017, Plan §D3]
- [ ] CHK019 - Does the spec define whether FR-015 (skip inter-service categories when zero dependencies) is applied BEFORE or AFTER the architecture filter? [Clarity, Spec §FR-015]
- [ ] CHK020 - Are severity matrix rules consistent with the filter — no microservice severity applied to monolith-only categories? [Consistency, Spec §FR-016]

## Communication Map Integration

- [ ] CHK021 - Is the directionality requirement clear — edge cases generated on the SOURCE service (caller), not the target? [Clarity, Spec §FR-008, Clarification §Session]
- [ ] CHK022 - Is the event-based directionality specified — producer gets "message loss" cases, consumers get "stale data" cases? [Completeness, Spec §FR-009]
- [ ] CHK023 - Does the spec define what happens when a communication[] entry references a service not in the manifest? [Edge Case, Gap]
- [ ] CHK024 - Is circular dependency handling (A→B and B→A both in communication[]) addressed in requirements? [Coverage, Spec §Edge Cases]
- [ ] CHK025 - Are edge cases differentiated by the `required` flag on communication entries — does required vs optional produce different scenarios or just different severities? [Clarity, Spec §FR-008, §FR-016]
- [ ] CHK026 - Is the mapping from `events[]` to edge cases specified — does each event produce exactly 1 eventual_consistency case, or could it also trigger distributed_transaction? [Clarity, Spec §FR-009]
- [ ] CHK027 - Are edge cases specified for services that are BOTH producer AND consumer of events? [Coverage, Gap]

## YAML Frontmatter Contract

- [ ] CHK028 - Are all 6 required YAML frontmatter fields explicitly listed? (id, category, severity, affected_services, handling_strategy, test_suggestion) [Completeness, Spec §FR-006]
- [ ] CHK029 - Is the YAML block format specified — fenced code block (` ```yaml `) vs document-level frontmatter (`---`)? [Clarity, Research §R-002]
- [ ] CHK030 - Are field types defined for YAML values — is `affected_services` a YAML list or comma-separated string? [Clarity, Spec §FR-006]
- [ ] CHK031 - Is the `id` field format specified with enough precision for programmatic extraction? (regex pattern: `EC-\d{3}`) [Clarity, Spec §FR-007, Data Model]
- [ ] CHK032 - Are valid `severity` values constrained to exactly 4 options (critical/high/medium/low) in the YAML schema? [Completeness, Spec §FR-016]
- [ ] CHK033 - Are valid `category` values constrained to the defined union set (6 microservice + 6 standard + interface_contract_violation)? [Completeness, Spec §Key Entities]
- [ ] CHK034 - Is forward compatibility addressed — can Feature 009 sub-agent tolerate additional YAML fields added in future versions? [Coverage, Spec §SC-005]
- [ ] CHK035 - Is the YAML extraction method specified or documented? (regex pattern for fenced blocks) [Completeness, Research §R-002, §SC-005]

## Edge Case Count & Budget

- [ ] CHK036 - Is the budget formula explicitly defined with all variables? (6 + 2N + E + 2(F-1), cap 30) [Completeness, Spec §FR-018, §SC-001]
- [ ] CHK037 - Is the prioritization strategy defined when budget cap truncates edge cases? (which cases are dropped first?) [Clarity, Plan §D4]
- [ ] CHK038 - Is the minimum edge case count specified? (6 base cases even with zero deps/events) [Completeness, Spec §FR-018]
- [ ] CHK039 - Does the budget formula account for data_ownership cases from BoundaryAnalyzer — are they counted within the 2-per-dependency budget or separate? [Clarity, Spec §FR-014, §FR-018]
- [ ] CHK040 - Is the feature-interaction case count (2 per additional feature) scoped — what constitutes a "feature interaction" edge case? [Clarity, Spec §FR-018]
- [ ] CHK041 - Are the budget boundaries testable — can SC-001's formula be verified with a concrete example? (e.g., 2 deps + 1 event + 3 features = 6+4+1+4 = 15 cases) [Measurability, Spec §SC-001]
- [ ] CHK042 - Is the cap of 30 justified — does the spec explain why 30 and not 20 or 50? [Clarity, Spec §FR-018]

## Severity Matrix Completeness

- [ ] CHK043 - Is the severity matrix exhaustive — does it cover ALL valid (required, pattern) combinations including edge cases like (required, "unknown-pattern")? [Coverage, Spec §FR-016]
- [ ] CHK044 - Is the default severity defined for patterns not in the matrix? (e.g., a new communication pattern "sync-websocket") [Edge Case, Gap]
- [ ] CHK045 - Are monolith severity assignments consistent with the category priority order in the plan? (security=high aligns with priority 7?) [Consistency, Spec §FR-016, Plan §D6]
