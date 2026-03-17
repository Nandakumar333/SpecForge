# Checklist: Analysis Engine Requirements Quality

**Purpose**: Validate that the edge case analysis engine requirements are complete, unambiguous, and architecture-aware — covering microservice categories, monolith filtering, communication map integration, YAML contract stability, and output budgeting.
**Created**: 2026-03-17
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md)
**Depth**: Standard | **Audience**: Reviewer (PR) | **Focus**: Architecture-aware analysis, category completeness, machine-parseability contract

---

## Microservice Category Completeness

- [X] CHK001 - Are all 6 microservice-specific edge case categories explicitly enumerated in requirements? (service_unavailability, network_partition, eventual_consistency, distributed_transaction, version_skew, data_ownership) [Completeness, Spec §FR-002] — ✅ All 6 listed in FR-002
- [X] CHK002 - Is each microservice category defined with a distinct scenario description that differentiates it from the other 5? [Clarity, Spec §FR-002] — ✅ US1 acceptance scenarios + YAML pattern files define distinct triggers per category
- [X] CHK003 - Are the trigger conditions for each microservice category specified? (e.g., 503 response for service_unavailability, message loss for eventual_consistency) [Completeness, Spec §FR-002] — ✅ US1.1 (503), US1.2 (propagation delay), US1.3 (timeout/message-loss), Plan §D9 YAML patterns
- [X] CHK004 - Is the mapping between communication pattern types (sync-rest, sync-grpc, async-events) and applicable microservice categories documented? [Clarity, Spec §FR-008] — ✅ FR-008 specifies source-service directionality; FR-016 maps pattern types to severity; Plan §D9 YAML has applicable_patterns
- [X] CHK005 - Are recommended handling strategies defined for each microservice category? (e.g., circuit breaker for service_unavailability, outbox for distributed_transaction) [Completeness, Spec §FR-019] — ✅ FR-019 lists patterns; Plan §D9 YAML handling_strategies per category
- [X] CHK006 - Does the spec define which microservice categories apply to sync vs async dependencies? [Clarity, Spec §FR-008, §FR-009] — ✅ FR-008 covers sync deps, FR-009 covers async/event deps with explicit role separation
- [X] CHK007 - Is the version_skew category scope defined — does it cover API contract changes, JWT claim changes, or both? [Clarity, Spec §FR-002] — ✅ FIXED: FR-002 now explicitly states "API contract changes (REST endpoint schema) and authentication token changes (new JWT claims)"
- [X] CHK008 - Is the data_ownership category trigger condition specified — only shared entities from BoundaryAnalyzer, or also explicit manifest references? [Clarity, Spec §FR-014] — ✅ FR-014 specifies "using BoundaryAnalyzer patterns" only

## Monolith Standard Categories

- [X] CHK009 - Are all 6 standard monolith categories explicitly enumerated? (concurrency, data_boundary, state_machine, ui_ux, security, data_migration) [Completeness, Spec §FR-003] — ✅ All 6 listed in FR-003
- [X] CHK010 - Is each standard category defined with a scenario description relevant to monolith architectures? [Clarity, Spec §FR-003] — ✅ Plan §D9 YAML pattern files define scenarios per standard category
- [X] CHK011 - Does the spec explicitly state that monolith mode generates ZERO distributed-system categories? [Clarity, Spec §FR-003, §SC-002] — ✅ FR-003 "standard categories ONLY"; SC-002 "zero distributed-system categories"
- [X] CHK012 - Are modular-monolith requirements specified as superset of monolith (standard categories + interface_contract_violation)? [Completeness, Spec §FR-004] — ✅ FR-004 "standard monolith categories PLUS interface contract violation"
- [X] CHK013 - Is the interface_contract_violation category scope defined for modular-monolith — module-level or service-interface-level? [Clarity, Spec §FR-004] — ✅ FIXED: FR-004 now specifies "published module interfaces (public API surface of a module)"
- [X] CHK014 - Are standard category handling strategies appropriate for monoliths? (e.g., no "circuit breaker" for concurrency — should be locking/mutex patterns) [Consistency, Spec §FR-019] — ✅ FR-019 lists "architectural patterns" generically; Plan §D9 YAML patterns define monolith-appropriate strategies per category file

## Architecture Filter Requirements

- [X] CHK015 - Is the ArchitectureEdgeCaseFilter's filtering logic explicitly defined for all 3 architecture types? (monolithic, microservice, modular-monolith) [Completeness, Spec §FR-001, Plan §D3] — ✅ Plan §D3 defines filter logic per architecture; FR-003/FR-004/FR-015 define category inclusion
- [X] CHK016 - Does the spec define which categories are REMOVED per architecture, not just which are included? (negative specification for safety) [Clarity, Spec §FR-003, §FR-015] — ✅ FR-003 "standard categories ONLY" (implicit exclusion of microservice cats); US2.2 explicitly lists excluded categories
- [X] CHK017 - Is the filtering behavior specified when architecture type is unknown or missing from manifest? [Edge Case, Gap] — ✅ FIXED: FR-001 now specifies "fall back to monolithic behavior and emit a warning"
- [X] CHK018 - Is the interaction between ArchitectureEdgeCaseFilter and ArchitectureAdapter.get_edge_case_extras() specified — does filtering apply to adapter extras or only to pattern-generated cases? [Consistency, Spec §FR-017, Plan §D3] — ✅ FR-017 "use adapter extras AND layer service-specific on top"; Plan §D7 shows both passed to template
- [X] CHK019 - Does the spec define whether FR-015 (skip inter-service categories when zero dependencies) is applied BEFORE or AFTER the architecture filter? [Clarity, Spec §FR-015] — ✅ Plan §D2 step sequence: filter by architecture first, then skip inter-service if zero deps (step 2 checks communication[])
- [X] CHK020 - Are severity matrix rules consistent with the filter — no microservice severity applied to monolith-only categories? [Consistency, Spec §FR-016] — ✅ FR-016 defines separate matrices per architecture; monolith matrix uses category-based rules, microservice uses required×pattern

## Communication Map Integration

- [X] CHK021 - Is the directionality requirement clear — edge cases generated on the SOURCE service (caller), not the target? [Clarity, Spec §FR-008, Clarification §Session] — ✅ FR-008 "for the calling service (the service that declares the dependency)"
- [X] CHK022 - Is the event-based directionality specified — producer gets "message loss" cases, consumers get "stale data" cases? [Completeness, Spec §FR-009] — ✅ FR-009 explicitly defines producer vs consumer roles
- [X] CHK023 - Does the spec define what happens when a communication[] entry references a service not in the manifest? [Edge Case, Gap] — ✅ FIXED: New FR-020 "emit edge case with target slug as-is, append warning note"
- [X] CHK024 - Is circular dependency handling (A→B and B→A both in communication[]) addressed in requirements? [Coverage, Spec §Edge Cases] — ✅ Edge case section: "Engine detects the cycle and generates a circular dependency edge case"
- [X] CHK025 - Are edge cases differentiated by the `required` flag on communication entries — does required vs optional produce different scenarios or just different severities? [Clarity, Spec §FR-008, §FR-016] — ✅ FR-016 severity matrix differentiates; scenarios are same shape, severity changes
- [X] CHK026 - Is the mapping from `events[]` to edge cases specified — does each event produce exactly 1 eventual_consistency case, or could it also trigger distributed_transaction? [Clarity, Spec §FR-009] — ✅ FIXED: FR-009 now specifies "1 eventual_consistency per consumer PLUS 1 distributed_transaction if 2+ consumers"
- [X] CHK027 - Are edge cases specified for services that are BOTH producer AND consumer of events? [Coverage, Gap] — ✅ FIXED: FR-009 now specifies "Services that are both producer AND consumer get edge cases for both roles"

## YAML Frontmatter Contract

- [X] CHK028 - Are all 6 required YAML frontmatter fields explicitly listed? (id, category, severity, affected_services, handling_strategy, test_suggestion) [Completeness, Spec §FR-006] — ✅ All 6 listed in FR-006
- [X] CHK029 - Is the YAML block format specified — fenced code block (` ```yaml `) vs document-level frontmatter (`---`)? [Clarity, Research §R-002] — ✅ FIXED: New FR-021 "MUST use fenced code block format"
- [X] CHK030 - Are field types defined for YAML values — is `affected_services` a YAML list or comma-separated string? [Clarity, Spec §FR-006] — ✅ FIXED: FR-021 "affected_services field MUST be a YAML list (sequence)"
- [X] CHK031 - Is the `id` field format specified with enough precision for programmatic extraction? (regex pattern: `EC-\d{3}`) [Clarity, Spec §FR-007, Data Model] — ✅ FR-007 "EC-NNN" pattern; Data Model validation rules: `EC-\d{3}`
- [X] CHK032 - Are valid `severity` values constrained to exactly 4 options (critical/high/medium/low) in the YAML schema? [Completeness, Spec §FR-016] — ✅ FR-016 "MUST be one of: critical, high, medium, low"
- [X] CHK033 - Are valid `category` values constrained to the defined union set (6 microservice + 6 standard + interface_contract_violation)? [Completeness, Spec §Key Entities] — ✅ EdgeCaseCategory lists all 13 valid values
- [X] CHK034 - Is forward compatibility addressed — can Feature 009 sub-agent tolerate additional YAML fields added in future versions? [Coverage, Spec §SC-005] — ✅ FIXED: FR-021 "Additional fields MAY be added; consumers MUST tolerate unknown keys"
- [X] CHK035 - Is the YAML extraction method specified or documented? (regex pattern for fenced blocks) [Completeness, Research §R-002, §SC-005] — ✅ Research §R-002 documents regex: `re.findall(r'```yaml\n(.*?)\n```', text, re.DOTALL)`

## Edge Case Count & Budget

- [X] CHK036 - Is the budget formula explicitly defined with all variables? (6 + 2N + E + 2(F-1), cap 30) [Completeness, Spec §FR-018, §SC-001] — ✅ FR-018 defines full formula; SC-001 cross-references
- [X] CHK037 - Is the prioritization strategy defined when budget cap truncates edge cases? (which cases are dropped first?) [Clarity, Plan §D4] — ✅ FIXED: FR-018 now specifies "prioritized by severity (critical>high>medium>low), then by category priority order"
- [X] CHK038 - Is the minimum edge case count specified? (6 base cases even with zero deps/events) [Completeness, Spec §FR-018] — ✅ FR-018 "6 base cases (1 per standard category)" — always generated
- [X] CHK039 - Does the budget formula account for data_ownership cases from BoundaryAnalyzer — are they counted within the 2-per-dependency budget or separate? [Clarity, Spec §FR-014, §FR-018] — ✅ FIXED: FR-018 now specifies "Data ownership cases count within the 2-per-dependency allocation (not additive)"
- [X] CHK040 - Is the feature-interaction case count (2 per additional feature) scoped — what constitutes a "feature interaction" edge case? [Clarity, Spec §FR-018] — ✅ FIXED: FR-018 now defines "scenarios where two features within the same service have conflicting resource needs"
- [X] CHK041 - Are the budget boundaries testable — can SC-001's formula be verified with a concrete example? (e.g., 2 deps + 1 event + 3 features = 6+4+1+4 = 15 cases) [Measurability, Spec §SC-001] — ✅ SC-001 formula is deterministic and verifiable with any input tuple
- [X] CHK042 - Is the cap of 30 justified — does the spec explain why 30 and not 20 or 50? [Clarity, Spec §FR-018] — ✅ Clarifications §Session: "Budget formula: 6 base + 2/dep + 1/event + 2/extra-feature. Hard cap at 30" — keeps document actionable per developer review scope

## Severity Matrix Completeness

- [X] CHK043 - Is the severity matrix exhaustive — does it cover ALL valid (required, pattern) combinations including edge cases like (required, "unknown-pattern")? [Coverage, Spec §FR-016] — ✅ FIXED: FR-016 now includes default rule for unknown patterns
- [X] CHK044 - Is the default severity defined for patterns not in the matrix? (e.g., a new communication pattern "sync-websocket") [Edge Case, Gap] — ✅ FIXED: FR-016 now specifies "defaults to high for required, medium for optional"
- [X] CHK045 - Are monolith severity assignments consistent with the category priority order in the plan? (security=high aligns with priority 7?) [Consistency, Spec §FR-016, Plan §D6] — ✅ Severity and priority are orthogonal: severity=impact level, priority=truncation order. security=high severity + priority 7 means "high impact but lower truncation priority than distributed cases" — consistent
