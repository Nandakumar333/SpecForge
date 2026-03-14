# Implementation Readiness Checklist: Template Rendering Engine

**Purpose**: Validate that spec, plan, and design artifacts are complete, clear, and consistent enough to begin implementation without ambiguity
**Created**: 2026-03-14
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [research.md](../research.md)
**Audience**: Author / PR Reviewer
**Depth**: Thorough

---

## Acceptance Criteria Completeness

- [ ] CHK001 — Are acceptance scenarios defined for all 5 user stories (not 3 as user-request states — spec contains US1–US5)? [Completeness, Spec §US1–US5]
- [ ] CHK002 — Does US1 have acceptance scenarios covering all rendering modes: basic substitution, missing variables, conditionals (truthy + falsy), inheritance, partials, and generation header? [Completeness, Spec §US1]
- [ ] CHK003 — Does US2 define acceptance scenarios for both custom-override-found and fallback-to-built-in paths? [Completeness, Spec §US2]
- [ ] CHK004 — Does US3 define acceptance scenarios for stack-variant-found, fallback-to-generic, unsupported-stack, and user-override-of-variant? [Completeness, Spec §US3]
- [ ] CHK005 — Does US4 define acceptance scenarios for catalog listing, source attribution, precedence resolution, and type-filtered querying? [Completeness, Spec §US4]
- [ ] CHK006 — Does US5 define acceptance scenarios for clean output, unresolved placeholders, structural issues, and validation-pass confirmation? [Completeness, Spec §US5]
- [ ] CHK007 — Are acceptance scenarios written in Given/When/Then format with specific, unambiguous conditions? [Clarity, Spec §US1–US5]

## Template Inheritance Specification

- [ ] CHK008 — Is the extends/block pattern explicitly named as the inheritance mechanism in both spec (FR-002) and research (R-01)? [Clarity, Spec §FR-002, Research §R-01]
- [ ] CHK009 — Are the named block identifiers for the base prompt template specified (e.g., `role`, `instructions`, `context`, `constraints`)? [Completeness, Research §R-01]
- [ ] CHK010 — Is the behavior for blocks NOT overridden by child templates explicitly defined ("retain base template's default content")? [Clarity, Spec §FR-002]
- [ ] CHK011 — Is the `_` prefix convention for abstract/base templates (not directly renderable) documented in both spec and data model? [Consistency, Research §R-01, Data Model §TemplateInfo]
- [ ] CHK012 — Are requirements defined for what happens when a child template references a non-existent parent or block? [Edge Case, Spec §Edge Cases]
- [ ] CHK013 — Are requirements defined for circular inheritance detection? [Edge Case, Spec §Edge Cases]

## Prompt Template Catalog

- [ ] CHK014 — Are all 7 agent instruction prompt templates explicitly listed by name: backend, frontend, database, security, testing, cicd, api-design? [Completeness, Spec §FR-016]
- [ ] CHK015 — Is the tech-stack variant strategy clearly specified for prompt templates — which stacks get dedicated variants vs. fall back to generic? [Clarity, Spec §FR-017]
- [ ] CHK016 — Are the initial stack variants to be created enumerated (e.g., backend.dotnet, backend.nodejs, backend.python), or is the minimum variant set ambiguous? [Gap, Spec §FR-017]
- [ ] CHK017 — Is the base prompt template (`_base_prompt.md.j2`) structure documented with its block names and default content? [Completeness, Research §R-01]
- [ ] CHK018 — Are requirements consistent for which prompts get stack variants (all 7? only backend? a defined subset)? [Ambiguity, Spec §FR-017 vs Research §R-01]

## Feature Template Catalog

- [ ] CHK019 — Are all 7 per-feature templates explicitly listed by name: spec, research, data-model, plan, checklist, edge-cases, tasks? [Completeness, Spec §FR-018]
- [ ] CHK020 — Are the placeholder variables for each feature template type defined in the variable schema? [Completeness, Data Model §TemplateVarSchema]
- [ ] CHK021 — Is "smart placeholders" in FR-019 defined with specific, measurable criteria (what makes a placeholder "smart" vs. a plain placeholder)? [Clarity, Spec §FR-019]
- [ ] CHK022 — Are conditional sections for feature templates specified — which sections are conditional and on what variables? [Gap, Spec §FR-003]
- [ ] CHK023 — Is the migration path from Feature 001 template names (e.g., `spec-template` → `spec`, `quickstart-template` → removed?) explicitly documented? [Completeness, Spec §Assumptions]

## Template Resolution Order

- [ ] CHK024 — Is the 3-level precedence order (user override → stack-specific variant → generic built-in) consistently stated across spec (FR-008), research (R-02), and contracts? [Consistency, Spec §FR-008, Research §R-02, Contract §TemplateRegistry]
- [ ] CHK025 — Is the full 4-step resolution chain for stack-specific lookups documented (user+stack → user+generic → built-in+stack → built-in+generic)? [Completeness, Research §R-02]
- [ ] CHK026 — **CONFLICT**: Does the spec clarification (subdirectories: `prompts/backend/dotnet.md.j2`) align with the plan/research (dot-notation: `backend.dotnet.md.j2`)? These are different disk organizations. [Conflict, Spec §Clarifications vs Plan §Project Structure vs Research §R-03]
- [ ] CHK027 — Are requirements defined for what happens when multiple user-override files match the same logical template? [Edge Case, Gap]

## Post-Render Validation Rules

- [ ] CHK028 — Are all 4 validation checks explicitly listed: (1) unresolved placeholders, (2) unclosed code blocks, (3) orphaned list markers, (4) broken heading hierarchy? [Completeness, Spec §FR-013, FR-014]
- [ ] CHK029 — Is the unresolved placeholder detection pattern specified (what regex/pattern identifies `{{ }}`, `{% %}`, `{# #}`)? [Clarity, Research §R-05]
- [ ] CHK030 — Is "orphaned list markers" defined with specific criteria (what constitutes an orphaned marker)? [Clarity, Spec §FR-014]
- [ ] CHK031 — Is the validation scope boundary explicitly drawn — which markdown checks are IN scope vs. delegated to external tools? [Clarity, Spec §FR-014, Spec §Assumptions]
- [ ] CHK032 — Are validation output requirements specified: line numbers, issue types, human-readable messages per the ValidationReport entity? [Completeness, Data Model §ValidationReport]
- [ ] CHK033 — Is the generation header validation defined — is its absence a hard error or soft warning? [Ambiguity, Research §R-06]

## Custom Filter Specification

- [ ] CHK034 — Are all custom Jinja2 filters explicitly listed by name: `snake_case`, `uppercase`, `pluralize`, `kebab_case`? [Completeness, Plan §Summary, Research §R-04]
- [ ] CHK035 — Is the behavior of each filter specified with input/output examples (e.g., `"MyProject"|snake_case → "my_project"`)? [Clarity, Research §R-04]
- [ ] CHK036 — Are edge case behaviors for filters defined (empty string, special characters, already-formatted input)? [Edge Case, Gap]
- [ ] CHK037 — Are the custom filters referenced in the spec's functional requirements, or do they only appear in plan/research? [Traceability, Gap — filters not in spec FRs]

## Error Handling for Missing Templates and Variables

- [ ] CHK038 — Is the error contract for missing templates specified with exact message format including template name, issue, and suggested resolution? [Clarity, Spec §FR-022, Contract §Error Contracts]
- [ ] CHK039 — Is the error contract for missing required variables specified with each missing variable named? [Clarity, Spec §FR-011]
- [ ] CHK040 — Is the error contract for type mismatches specified with expected vs. actual type? [Clarity, Spec §FR-012]
- [ ] CHK041 — Are all error paths using Result[T, E] rather than exceptions, consistent with the constitution's Code Quality principle? [Consistency, Constitution §III]
- [ ] CHK042 — Are error scenarios defined for: template syntax errors, circular inheritance, missing parent references, permission errors on user-override directory? [Coverage, Spec §Edge Cases, Spec §FR-022]
- [ ] CHK043 — Is the behavior specified when built-in templates are missing or corrupted (package installation issue)? [Edge Case, Gap]

## Snapshot Test Strategy

- [ ] CHK044 — Is the snapshot testing approach documented for rendered template output (golden file comparison)? [Completeness, Plan §Technical Context, Constitution §IV]
- [ ] CHK045 — Are snapshot tests required for all template types: constitution, prompts (generic + at least one stack variant), feature templates, and partials? [Coverage, Gap]
- [ ] CHK046 — Is the snapshot update workflow documented (how to regenerate snapshots after intentional template changes)? [Completeness, Quickstart §Running Tests]
- [ ] CHK047 — Are snapshot tests required for user-override scenarios (rendering with an override vs. without)? [Coverage, Gap]
- [ ] CHK048 — Is the backward compatibility constraint for existing Feature 001 snapshot tests documented with explicit pass/update expectations? [Clarity, Plan §Constraints]

## Cross-Artifact Consistency

- [ ] CHK049 — Do the 4 core module names align across spec entities, plan project structure, contracts, and data model: TemplateRegistry, TemplateRenderer, TemplateValidator, StackAdapter? [Consistency, All artifacts]
- [ ] CHK050 — Does the TemplateVarSchema in the data model match the variable validation requirements in FR-011/FR-012? [Consistency, Spec §FR-011/FR-012, Data Model §TemplateVarSchema]
- [ ] CHK051 — Does the contract's public API (`.render()`, `.get()`, `.validate()`, `.get_context()`) cover all functional requirements in the spec? [Traceability, Contract vs Spec §FR-001–FR-022]
- [ ] CHK052 — Is the `partial` type in the TemplateType enum reflected in the spec's FR requirements, or is it only in the data model? [Consistency, Data Model §TemplateType vs Spec §FR-005]

## Dependencies & Assumptions

- [ ] CHK053 — Is the Feature 001 migration dependency explicitly documented with the specific breaking changes expected? [Completeness, Spec §Assumptions]
- [ ] CHK054 — Is the Jinja2 ChoiceLoader dependency documented as a design decision with fallback if behavior changes? [Assumption, Research §R-02]
- [ ] CHK055 — Are the 5 supported stacks (dotnet, nodejs, python, go, java) consistently listed across spec, config, and research? [Consistency]

---

## Summary

| Dimension | Items | Key Findings |
|-----------|-------|-------------|
| Acceptance Criteria | CHK001–CHK007 | Spec has 5 user stories (user referenced 3); all have Given/When/Then scenarios |
| Inheritance | CHK008–CHK013 | Well-specified; block names documented in research but not spec |
| Prompt Catalog | CHK014–CHK018 | 7 prompts listed; minimum stack variant set is ambiguous |
| Feature Catalog | CHK019–CHK023 | 7 features listed; "smart placeholders" needs quantification |
| Resolution Order | CHK024–CHK027 | **CONFLICT**: Spec says subdirectories, plan/research says dot-notation |
| Validation | CHK028–CHK033 | 4 checks listed; header validation severity unclear |
| Custom Filters | CHK034–CHK037 | 4 filters documented in plan/research but **not in spec FRs** |
| Error Handling | CHK038–CHK043 | Good coverage; missing built-in corruption scenario |
| Snapshot Tests | CHK044–CHK048 | Strategy exists; override and variant coverage gaps |
| Cross-Artifact | CHK049–CHK052 | Module names consistent; partial type traceability gap |
| Dependencies | CHK053–CHK055 | Migration documented; stack list consistency to verify |
