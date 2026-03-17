# Implementation Readiness Checklist: Quality Validation System

**Purpose**: Validate that spec/plan requirements are complete, clear, and unambiguous for all checker implementations, auto-fix engine, diagnostic reporting, and backward compatibility — ensuring no gaps before task generation.
**Created**: 2026-03-17
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md)

## Requirement Completeness — Standard Checkers

- [ ] CHK001 - Are build check requirements defined for all supported project types (Python, .NET, Node.js), or is the scope limited to a single stack? [Completeness, Spec §FR-001]
- [ ] CHK002 - Are lint checker requirements specific about which linter tool to invoke per stack (ruff for Python, eslint for JS), or is tool selection left unspecified? [Clarity, Spec §FR-002]
- [ ] CHK003 - Is the test runner selection criteria documented for multi-stack projects (pytest vs dotnet test vs npm test)? [Completeness, Spec §FR-003]
- [ ] CHK004 - Are coverage threshold requirements sourced exclusively from `testing.prompts.md`, and is fallback behavior (no threshold defined) explicitly specified? [Completeness, Spec §FR-004, Edge Cases §7]
- [ ] CHK005 - Is the 30-line function limit and 200-line class limit sourced from governance prompts or hardcoded, and is this distinction documented? [Clarity, Spec §FR-005, §FR-006]
- [ ] CHK006 - Are secret detection patterns enumerated (AWS keys, API tokens, connection strings, private keys) or left as a vague "scan for secrets"? [Clarity, Spec §FR-007]
- [ ] CHK007 - Is the entropy threshold for secret detection specified as a measurable value? [Measurability, Spec §FR-007, Gap]
- [ ] CHK008 - Are TODO/FIXME/HACK scanning requirements clear about scope — only changed files or entire project? [Clarity, Spec §FR-008]
- [ ] CHK009 - Are prompt rule compliance requirements clear about the two-tier distinction (Tier 1 automated vs Tier 2 delegated)? [Clarity, Spec §FR-009]

## Requirement Completeness — Architecture-Specific Checkers

- [ ] CHK010 - Is the Docker checker's applicability rule explicitly limited to `architecture == "microservice"` in both spec and contract? [Consistency, Spec §FR-010, Contract §3]
- [ ] CHK011 - Is the container-relevant file pattern set (Dockerfile, docker-compose.yml, .dockerignore, dependency manifests) enumerated as a closed list or left open-ended? [Clarity, Spec §FR-010, Research §R7]
- [ ] CHK012 - Are contract checker requirements explicit that it only applies to `architecture == "microservice"`? [Consistency, Spec §FR-012, Contract §3]
- [ ] CHK013 - Is the consumer vs provider attribution heuristic for contract test failures defined with specific output patterns to match? [Clarity, Spec §FR-012, Clarifications §Q2]
- [ ] CHK014 - Is the boundary checker's applicability explicitly limited to `architecture == "modular-monolith"`? [Consistency, Spec §FR-017, Contract §3]
- [ ] CHK015 - Are "cross-module direct data access" and "module interface compliance" defined with detectable patterns, not just abstract concepts? [Clarity, Spec §FR-017, §FR-018]
- [ ] CHK016 - Is the full service-level verification (FR-010a) clearly distinguished from per-task Docker checks in terms of trigger conditions? [Consistency, Spec §FR-010 vs §FR-010a]
- [ ] CHK017 - Are requirements for proto file compilation (§FR-015) and event schema validation (§FR-016) conditional on file existence, and is this conditionality explicit? [Completeness, Spec §FR-015, §FR-016]

## Requirement Completeness — Auto-Fix Categories

- [ ] CHK018 - Does each of the 8 error categories (syntax, logic, type, lint, coverage, docker, contract, boundary) have a documented fix prompt strategy? [Completeness, Spec §FR-020, §FR-022]
- [ ] CHK019 - Is the mapping from checker → error category explicitly defined for all 11 checkers, or could any checker produce an ambiguous category? [Consistency, Data Model §ErrorCategory, Research §R3]
- [ ] CHK020 - Are targeted fix prompt requirements specific enough to distinguish from generic prompts? (e.g., "lint" → cite file/line/rule vs "fix lint errors") [Clarity, Spec §US2 Acceptance §1-5]
- [ ] CHK021 - Is the behavior for contract/provider-attributed errors (skip auto-fix, escalate immediately) documented as a hard rule, not just guidance? [Clarity, Spec §FR-012 Clarifications §Q2]
- [ ] CHK022 - Are progressive context requirements (attempt N includes history of attempts 1..N-1) specified with what exactly each attempt prompt must contain? [Completeness, Spec §FR-024]
- [ ] CHK023 - Is the "try ruff/eslint auto-fix first, then manual" strategy for LINT category explicitly specified or only implied? [Gap, User Input §auto-fix categories]

## Requirement Clarity — Diagnostic Report

- [ ] CHK024 - Are all required sections of the diagnostic report enumerated (original error, per-attempt diffs, remaining failures, suggested steps)? [Completeness, Spec §FR-027]
- [ ] CHK025 - Is the "timeline" requirement (§FR-028) defined with a specific structure (chronological list, per-attempt detail level)? [Clarity, Spec §FR-028]
- [ ] CHK026 - Are "suggested manual remediation steps" required to be category-specific, and are example suggestions documented per category? [Clarity, Spec §FR-027, §US4 Acceptance §3]
- [ ] CHK027 - Is the diagnostic report output format specified (Markdown via Jinja2 template) and is the template path defined? [Completeness, Research §R9, Plan §Structure]
- [ ] CHK028 - Are per-attempt diffs defined as actual file diffs, a summary of changes, or both? [Ambiguity, Spec §FR-027]
- [ ] CHK029 - Is it specified whether the diagnostic report includes check results for ALL checks per attempt or only the failing ones? [Gap]

## Requirement Completeness — Quality Report JSON

- [ ] CHK030 - Is the `.quality-report.json` schema defined with specific field names, types, and nesting structure? [Completeness, Data Model §QualityReport]
- [ ] CHK031 - Are the JSON report's consumers documented (Feature 012 dashboard, CI tooling), and are their schema requirements captured? [Gap, User Input §dashboard needs]
- [ ] CHK032 - Is the report lifecycle specified (overwritten each run, not version-controlled)? [Completeness, Research §R11]
- [ ] CHK033 - Is the report write location explicitly defined (`.specforge/features/<slug>/` or service root)? [Clarity, Plan §Technical Context]

## Requirement Consistency — Backward Compatibility

- [ ] CHK034 - Is the `QualityChecker.__init__(project_root, service_slug)` signature preservation documented as a hard constraint? [Consistency, Contract §1]
- [ ] CHK035 - Is the `QualityChecker.check(changed_files) → Result[QualityCheckResult, str]` return type preservation documented? [Consistency, Contract §1]
- [ ] CHK036 - Is the `QualityCheckResult` → `QualityGateResult` mapping defined for all fields (passed, build_output, lint_output, test_output, failed_checks, is_regression)? [Completeness, Data Model §Backward Compat]
- [ ] CHK037 - Is the `AutoFixLoop.fix()` signature preservation documented as a hard constraint? [Consistency, Contract §2]
- [ ] CHK038 - Is the `detect_regression()` static method contract preserved in the shim? [Consistency, Contract §1]
- [ ] CHK039 - Are there requirements specifying that existing Feature 009 tests must continue to pass without modification? [Gap]

## Scenario Coverage — Edge Cases & Exceptions

- [ ] CHK040 - Are requirements defined for when no changed files are provided to the quality gate? [Coverage, Edge Cases §6]
- [ ] CHK041 - Are requirements defined for when a checker tool is not installed (e.g., Docker not available)? [Coverage, Spec §FR-031, Edge Cases §2]
- [ ] CHK042 - Are requirements defined for when AST analysis encounters non-Python files? [Coverage, Edge Cases §8, Clarifications §Q1]
- [ ] CHK043 - Is the behavior for multi-category errors (root cause vs symptom) specified with a deterministic resolution rule? [Clarity, Edge Cases §4]
- [ ] CHK044 - Are requirements defined for repeated regressions across all 3 fix attempts? [Coverage, Edge Cases §5]
- [ ] CHK045 - Is the selective re-check strategy (FR-026: re-run only failed checks + regression check) specified with enough detail to implement? [Clarity, Spec §FR-026, Research §R10]

## Dependencies & Assumptions

- [ ] CHK046 - Is the dependency on Feature 003's `PromptLoader` and `PromptThreshold` API documented with specific method signatures? [Completeness, Spec §FR-009, Research §R8]
- [ ] CHK047 - Is the threshold key → checker mapping (e.g., `max_function_lines` → LineLimitChecker) enumerated as a closed set? [Completeness, Research §R8]
- [ ] CHK048 - Is the assumption that `manifest.json` always has an `architecture` field (or defaults to "monolithic") validated against Feature 009's actual manifest schema? [Assumption, Spec §Assumptions]
- [ ] CHK049 - Is the dependency on `ServiceContext` (from Feature 009) documented with the specific fields the quality gate reads? [Completeness, Contract §3]

## Notes

- Check items off as completed: `[x]`
- Items CHK001–CHK009: Standard checker requirement quality
- Items CHK010–CHK017: Architecture-specific checker requirement quality
- Items CHK018–CHK023: Auto-fix category coverage requirement quality
- Items CHK024–CHK029: Diagnostic report requirement quality
- Items CHK030–CHK033: Quality report JSON requirement quality
- Items CHK034–CHK039: Backward compatibility requirement quality
- Items CHK040–CHK045: Edge case scenario coverage
- Items CHK046–CHK049: Dependency/assumption validation
