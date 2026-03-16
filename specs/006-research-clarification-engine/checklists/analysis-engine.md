# Analysis Engine Checklist: Research & Clarification Engine

**Purpose**: Validate requirements quality for ambiguity detection, service-boundary analysis, research statuses, clarification persistence, architecture-change handling, and pipeline integration
**Created**: 2026-03-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness — Ambiguity Detection Patterns

- [x] CHK001 - Are the specific vague terms to detect enumerated (e.g., "appropriate", "as needed", "etc."), or is the list left open-ended? [Completeness, Spec §FR-001] — RESOLVED: T001 enumerates all terms with regex variants in VAGUE_TERM_PATTERNS
- [x] CHK002 - Are "missing quantities" defined as a detection category? FR-001 lists "vague terms, undefined domain concepts, unspecified technical choices, missing boundary definitions" but does not explicitly mention missing numeric thresholds or quantities [Gap, Spec §FR-001] — ACCEPTED: 4 categories are sufficient; numeric thresholds are out of scope for v1
- [x] CHK003 - Is "undefined term" detection specified with criteria for what constitutes "undefined"? (e.g., first-occurrence heuristic, no prior definition in spec, not in glossary) [Clarity, Spec §FR-001] — RESOLVED: T003 specifies "first-occurrence heuristic" for undefined_concept pattern
- [x] CHK004 - Are the confidence scoring criteria for AmbiguityMatch defined? The data model includes a `confidence: float` field but no requirement specifies how confidence is calculated [Gap, Spec §Key Entities] — RESOLVED: Implementation uses 1.0 for exact pattern matches, 0.7 for contextual/proximity matches
- [x] CHK005 - Is the minimum number of patterns per category specified, or could a category ship with zero patterns? [Completeness, Spec §FR-001] — RESOLVED: T003 default_patterns() factory ensures at least 1 pattern per type
- [x] CHK006 - Are false-positive mitigation requirements defined? (e.g., "appropriate" inside a quoted example should not trigger detection) [Edge Case, Gap] — RESOLVED: Implementation uses word-boundary regex (\b) and skips Markdown headings/code blocks

## Requirement Completeness — Service-Boundary Analysis

- [x] CHK007 - Is the keyword extraction algorithm for cross-service concept detection specified? FR-005 says "when a concept is referenced by multiple services" but does not define how concepts are identified from feature descriptions [Clarity, Spec §FR-005] — RESOLVED: T022 specifies split-on-spaces + BOUNDARY_STOP_WORDS + basic stemming
- [x] CHK008 - Are requirements defined for multi-feature services where features span 3+ services? The spec examples only cover 2-service boundary cases (ledger + planning) [Coverage, Spec §US1] — RESOLVED: T020 tests "3+ services sharing a concept includes all boundary pairs"
- [x] CHK009 - Is the behavior specified when a concept is referenced by ALL services in the manifest (e.g., "authentication")? Should ubiquitous concepts still generate boundary questions? [Edge Case, Spec §FR-005] — RESOLVED: Implementation filters concepts appearing in >60% of services as ubiquitous (no questions generated)
- [x] CHK010 - Are the ownership options presented by FR-005 enumerated? The plan mentions "shared library, event-driven sync, or move to one service" but the spec only says "present ownership options" [Clarity, Spec §FR-005] — RESOLVED: T001 ANSWER_TEMPLATES defines service_boundary options: owned-by-A, owned-by-B, shared library, duplicate with eventual consistency
- [x] CHK011 - Is the behavior defined when BoundaryAnalyzer finds zero cross-service concepts for a multi-feature service? [Edge Case, Spec §FR-004] — RESOLVED: analyze() returns empty tuple; T020 tests single-service case

## Requirement Clarity — Research Finding Statuses

- [x] CHK012 - Are the criteria for assigning RESOLVED vs UNVERIFIED status explicitly defined? FR-021 says "UNVERIFIED when version information cannot be confirmed without external network access" — is this the only differentiator? [Clarity, Spec §FR-021] — RESOLVED: T016 specifies RESOLVED for embedded-knowledge confirmations (no version info needed), UNVERIFIED for version-dependent info
- [x] CHK013 - Is the CONFLICTING status trigger condition specified beyond "multiple sources disagree"? Are thresholds defined (e.g., 2+ conflicting findings trigger CONFLICTING)? [Clarity, Spec §FR-017] — RESOLVED: Implementation triggers CONFLICTING when 2+ viable alternatives exist for a single decision point
- [x] CHK014 - Are requirements for BLOCKED status escalation defined? (e.g., how does a BLOCKED finding get resolved — manual edit, re-run, separate command?) [Gap, Spec §FR-017] — ACCEPTED: BLOCKED findings require manual resolution; merge_findings re-evaluates on re-run
- [x] CHK015 - Is the "source" field vocabulary constrained? The data model lists "embedded-knowledge", "spec-reference", "manifest-metadata" but the spec does not mandate these values [Consistency, Spec §Key Entities vs §FR-017] — RESOLVED: data-model.md constrains to 3 values; implementation enforces this
- [x] CHK016 - Are requirements defined for the transition from UNVERIFIED to RESOLVED? Can a finding's status be manually upgraded? [Gap, Spec §FR-020] — RESOLVED: merge_findings re-evaluates UNVERIFIED on re-run; no manual upgrade mechanism needed

## Requirement Consistency — Clarification Append Behavior

- [x] CHK017 - Is the exact Markdown format for the Clarifications section specified? FR-006 says "Clarifications section appended to spec.md" and FR-007 says "append-only" but neither defines the bullet format (e.g., `- Q: ... → A: ...` appears only in the Clarifications section itself, not in requirements) [Clarity, Spec §FR-006] — RESOLVED: T011 specifies `- Q: [{category}] {question} → A: {answer}` format
- [x] CHK018 - Is the insertion point for the Clarifications section defined when it doesn't exist yet? (before Assumptions? after Success Criteria?) [Gap, Spec §FR-006] — RESOLVED: T011 specifies "inserts before ## Assumptions if not found"
- [x] CHK019 - Are requirements defined for what happens when the existing Clarifications section has been manually reformatted by a user between runs? [Edge Case, Spec §Edge Cases line 120] — RESOLVED: T030 handles "malformed Clarifications section (falls back to creating new section)"
- [x] CHK020 - Is the session date format specified (ISO 8601 YYYY-MM-DD)? The data model says "ISO date" but FR-006/FR-007 don't reference session grouping [Consistency, Spec §FR-006 vs §Key Entities] — RESOLVED: T011 specifies "### Session YYYY-MM-DD" subsection format
- [x] CHK021 - Are duplicate detection requirements defined for the append-only constraint? If the same question is answered in two sessions, is duplicate recording prevented or allowed? [Clarity, Spec §FR-007] — RESOLVED: T008 now tests SC-004 duplicate suppression on re-run

## Scenario Coverage — Architecture-Change Re-Clarification

- [x] CHK022 - Is "architecture-related" precisely defined for invalidation scope? FR-014a says "service-boundary, communication, data-ownership categories" but the category enum only has "service_boundary" and "communication" — is "data-ownership" a missing category? [Consistency, Spec §FR-014a vs §FR-002] — RESOLVED: data-ownership maps to service_boundary category; T023 targets (service_boundary, communication) tuples
- [x] CHK023 - Are requirements defined for the re-validation marker format? FR-014a says "mark as requiring re-validation" but doesn't specify how (tag, status field, inline marker?) [Clarity, Spec §FR-014a] — RESOLVED: T023 specifies `[NEEDS RE-VALIDATION]` inline tag appended to affected entries
- [x] CHK024 - Is the remap detection mechanism specified beyond "reading manifest.json metadata"? The assumption says `previous_architecture` field but no requirement mandates this field exists or how it's populated [Gap, Spec §FR-012 vs Assumptions] — RESOLVED: T022 specifies detect_remap() checks `previous_architecture` field differing from `architecture`; Feature 004 dependency documented
- [x] CHK025 - Are requirements defined for bidirectional remap (microservice → monolith)? FR-013 lists questions for "service boundaries, communication patterns, data ownership, shared state, eventual consistency" — are all relevant when going FROM microservice back to monolith? [Coverage, Spec §FR-013] — ACCEPTED: get_remap_questions generates generic arch-change questions; both directions produce relevant questions
- [x] CHK026 - Is the behavior specified when remap has occurred but the target service has no prior clarifications to invalidate? [Edge Case, Spec §FR-014a] — RESOLVED: T021 tests "no existing Clarifications section returns Ok with no changes"

## Requirement Completeness — Pipeline Integration

- [x] CHK027 - Is the pipeline state update behavior for `specforge research` fully specified? The plan says it marks research phase "complete" but no FR explicitly requires this [Gap, Spec §FR-024] — RESOLVED: T018 explicitly updates .pipeline-state.json; FR-024 covers pipeline state tracking
- [x] CHK028 - Is the relationship between `specforge research` (standalone command) and ResearchPhase (pipeline phase) clearly defined? Can both produce research.md — and if so, which takes precedence? [Ambiguity, Spec §FR-024] — RESOLVED: Plan D1 states they're separate; both produce compatible research.md; last-write wins
- [x] CHK029 - Are requirements defined for `.pipeline-lock` interaction? The spec mentions it in Assumptions and Edge Cases but no FR mandates lock checking before spec.md modification [Gap, Spec §Assumptions vs §FR-027] — RESOLVED: T012 now acquires pipeline lock via acquire_lock(); T030 enforces lock check for both commands
- [x] CHK030 - Is the manifest.json `previous_architecture` field documented as a contract with Feature 004? The spec assumes this field exists but Feature 004's manifest schema may not include it [Dependency, Spec §Assumptions] — ACCEPTED: Feature 004 dependency assumption documented; detect_remap returns False gracefully if field absent
- [x] CHK031 - Are error messages specified for integration failure modes? (e.g., manifest.json missing, spec.md missing, pipeline locked) [Gap, Spec §FR-026] — RESOLVED: T008/T015 test exit code 1 with error messages for missing manifest, missing spec, pipeline locked
- [x] CHK032 - Is the template discovery requirement for `clarifications-report.md.j2` specified? FR-025 says "use Jinja2 templates via TemplateRegistry" but doesn't specify the template name or that it must be added to FEATURE_TEMPLATE_NAMES [Completeness, Spec §FR-025] — RESOLVED: T004 creates the template; TemplateRegistry discovers built-in templates automatically

## Acceptance Criteria Quality

- [x] CHK033 - Is SC-002 ("detects at least 80% of ambiguities") measurable without a production deployment? The measurement method references "post-implementation change requests" which may not exist at validation time [Measurability, Spec §SC-002] — ACCEPTED: SC-002 is a long-term quality metric; validated via known-ambiguity test fixtures
- [x] CHK034 - Is SC-005 ("at least 3 additional service-boundary questions") testable without a specific reference manifest? The number "3" appears arbitrary without defining the baseline service complexity [Measurability, Spec §SC-005] — RESOLVED: T020 now asserts ≥5 remap questions covering all 5 FR-013 topics; uses PersonalFinance manifest as reference
- [x] CHK035 - Are acceptance scenarios defined for the research merge behavior (FR-020)? US2 scenario 5 covers re-run but doesn't specify what "merging" looks like in the output [Coverage, Spec §US2] — RESOLVED: T014 tests merge_findings preserving RESOLVED, re-evaluating BLOCKED, adding new findings

## Notes

- Check items off as completed: `[x]`
- Items marked [Gap] indicate missing requirements that should be added to the spec
- Items marked [Consistency] indicate potential conflicts between spec sections
- Items marked [Clarity] indicate requirements that need more precise language
- Items marked [Edge Case] indicate boundary conditions not covered in requirements
