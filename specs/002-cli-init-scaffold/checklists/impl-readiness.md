# Pre-Implementation Readiness Checklist: SpecForge CLI Init & Scaffold

**Purpose**: Validate spec.md, plan.md, and supporting artifacts are complete, clear, and consistent enough to begin implementation without rework risk
**Created**: 2026-03-14
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [contracts/cli-commands.md](../contracts/cli-commands.md)

---

## Acceptance Criteria Quality

- [ ] CHK001 - Are all user stories in spec.md counted accurately? The user input references "4 user stories" but spec.md contains 5 (User Stories 1–5 at P1–P4) — is this discrepancy intentional or is one story considered out of scope? [Consistency, Spec §User Scenarios]
- [ ] CHK002 - Do all 5 user stories contain ≥2 Given/When/Then acceptance scenarios covering both happy path and at least one failure/alternate path? User Story 5 (decompose) has only 2 scenarios — is the failure path (App Analyzer unavailable) intentionally deferred to Feature 004? [Coverage, Spec §User Story 5]
- [ ] CHK003 - Is the `--dry-run` acceptance scenario in User Story 1 (scenario 6) consistent with FR-016? Scenario 6 says "no git repository is initialized" — does this align with FR-016's wording "without writing any files or initializing git"? [Consistency, Spec §FR-016 vs User Story 1 scenario 6]
- [ ] CHK004 - Are acceptance scenarios for the `--here --force` path present in User Story 2 (scenario 3) measurable without ambiguity? "Missing files are created and existing files are preserved" — is "missing" defined relative to the canonical `.specforge/` file list? [Clarity, Spec §User Story 2 scenario 3]

---

## Directory Structure Completeness

- [ ] CHK005 - Are the 7 agent prompt file names enumerated by exact filename in FR-002, or only described by count ("all 7 agent prompt files")? A count without names leaves ambiguity about canonical filenames during implementation. [Clarity, Spec §FR-002]
- [ ] CHK006 - Are the 7 per-feature template file names enumerated by exact filename in FR-002, or only by count? [Clarity, Spec §FR-002]
- [ ] CHK007 - Is the `scripts/` subdirectory listed in FR-002 specified with any content, or intentionally empty at init time? If empty, is that an explicit requirement or an unresolved gap? [Completeness, Spec §FR-002]
- [ ] CHK008 - Does the plan.md source tree and the spec.md FR-002 directory list agree on every subdirectory and file? Both documents define the `.specforge/` structure — are they fully synchronized? [Consistency, Spec §FR-002 vs plan.md §Project Structure]

---

## CLI Flag Documentation

- [ ] CHK009 - Is the mutual exclusion of positional `NAME` and `--here` specified as a functional requirement in spec.md (FR layer), or does it exist only in contracts/cli-commands.md? A gap here means the constraint has no traceability to a spec requirement. [Completeness, Gap — present in contracts but absent from FR-003]
- [ ] CHK010 - Is the behavior of `--dry-run` combined with `--here` or `--force` specified? For example: does `specforge init --here --dry-run` preview the CWD tree? Does `--dry-run --force` preview without checking for existing files? [Coverage, Gap]
- [ ] CHK011 - Is the behavior of `--here` combined with `--no-git` specified? The `--no-git` requirement (FR-007) and `--here` requirement (FR-003) are defined independently — their combination is not addressed. [Coverage, Gap]
- [ ] CHK012 - Are default values for all flags explicitly stated in spec.md functional requirements, not only in plan.md contracts? FR-003 through FR-009, FR-016 describe flag behavior but not defaults — defaults appear only in contracts/cli-commands.md. [Completeness, Spec §FR-003–FR-009 vs contracts/cli-commands.md]

---

## Agent Detection Definition

- [ ] CHK013 - Are the executable binary names for all 6 supported agents specified in a requirements artifact (spec.md or plan.md), or only in data-model.md? Binary names are implementation-critical and should be traceable. [Traceability, data-model.md §AGENT_EXECUTABLES vs Spec §FR-008]
- [ ] CHK014 - Is the error/validation behavior for an unsupported `--agent` value (e.g., `--agent unknown`) specified with a concrete error message format, or only generally covered by FR-014? [Clarity, Spec §FR-014]
- [ ] CHK015 - Is "no agent found in PATH" explicitly specified as a non-error outcome (agnostic config + warning, not exit code 1)? FR-008 says "generate agnostic config" but does not state the exit code or warning text. [Clarity, Spec §FR-008]
- [ ] CHK016 - Is the priority order `claude → copilot → gemini → cursor → windsurf → codex` from the clarifications session reflected in FR-008 in spec.md, not only in the Clarifications section? [Traceability, Spec §Clarifications vs FR-008]

---

## Template File Format Specification

- [ ] CHK017 - Is Jinja2 as the template engine specified as a functional requirement (spec-level) or only as an architectural decision (plan-level)? FR-002 says the structure is created but does not require Jinja2 by name — the constitution does (Principle II). Is this traceability sufficient? [Traceability, Constitution §II vs Spec §FR-002]
- [ ] CHK018 - Are the template context variables (project_name, agent, stack, date, stack_hints) defined in a requirements artifact, or only in data-model.md? If a template renders incorrectly, which document is authoritative? [Completeness, data-model.md §Template Context Variables]
- [ ] CHK019 - Is the `.j2` file extension convention (templates named `*.md.j2`) specified as a requirement, or is it an undocumented implementation convention? [Clarity, Gap]

---

## Git Initialization Behavior

- [ ] CHK020 - Is the edge case "specforge init run inside an existing git repository" resolved as a requirement, or does it remain an open question in spec.md §Edge Cases? Currently listed as "What happens when specforge init is run inside an existing git repository?" with no resolution. [Gap, Spec §Edge Cases]
- [ ] CHK021 - Is the exact content or scope of the generated `.gitignore` specified, or only that "a .gitignore is created" (FR-009)? Without content requirements, the `.gitignore` could be empty and still pass FR-009. [Clarity, Spec §FR-009]
- [ ] CHK022 - Is the git commit behavior when `--here` is used (on an existing project that may already have commits) specified? Does the initial commit still happen, and if so does it conflict with the existing git history? [Coverage, Gap]

---

## Error Handling Coverage

- [ ] CHK023 - Is the error behavior for "git not installed + no --no-git flag" resolved as a requirement with a specific error message and exit code? Currently listed as an open question in spec.md §Edge Cases, not resolved as an FR. [Gap, Spec §Edge Cases]
- [ ] CHK024 - Is the error behavior for "write permission denied on target directory" specified with a concrete message format? FR-014 covers the exit code requirement generally but no scenario-specific wording is given. [Clarity, Spec §FR-014]
- [ ] CHK025 - Is the behavior for "interrupted mid-scaffold (partial directory tree)" specified as a requirement? spec.md §Edge Cases lists this as an open question — is recovery/cleanup expected, or is partial state acceptable with no rollback? [Gap, Spec §Edge Cases]
- [ ] CHK026 - Are error messages for all 4 invalid-flag scenarios (unsupported agent, unsupported stack, invalid project name, NAME + --here conflict) specified with exact wording, or only with the general format rule in contracts/cli-commands.md? [Completeness, contracts/cli-commands.md §Error Message Standards]

---

## Constitution Alignment

- [ ] CHK027 - Does plan.md §Constitution Check list all 10 gates from constitution.md by name with an explicit ✅/❌ status for this feature? [Completeness, plan.md §Constitution Check]
- [ ] CHK028 - Are the 30-line function and 200-line class limits from Constitution §III traceable to a tasks.md enforcement mechanism (e.g., ruff rule, PR gate)? tasks.md does not yet exist — is this constraint documented in plan.md for task authors? [Traceability, Constitution §III vs plan.md]
- [ ] CHK029 - Is the TDD ordering requirement (Constitution §IV: test files before implementation files) reflected explicitly in plan.md task sequencing guidance, so that `/speckit.tasks` generates tasks in the correct TDD order? [Traceability, Constitution §IV vs plan.md §Phase 1]
- [ ] CHK030 - Is the `Result[T]` pattern requirement traceable from Constitution §III ("Functions MUST return Result[T] instead of raising exceptions") through plan.md and into a concrete data-model definition? Is the chain spec → plan → data-model → tasks unbroken for this constraint? [Traceability, Constitution §III → plan.md §R-01 → data-model.md §Result Wrapper]

---

## Requirement Consistency

- [ ] CHK031 - Does spec.md FR-006 ("agnostic/generic templates with stack placeholder left empty") define what "stack placeholder left empty" means concretely? An implementer needs to know whether this means a blank field, a comment, or omitted content. [Clarity, Spec §FR-006]
- [ ] CHK032 - Are the success criteria SC-001 through SC-006 each traceable to at least one FR that governs them? For example, SC-006 ("100% of existing files preserved") — is this captured in FR-004 or FR-003, or only in the success criteria section? [Traceability, Spec §Success Criteria]
- [ ] CHK033 - Is the term "merge" used consistently between User Story 1 scenario 5 ("merged into the existing directory"), User Story 2 scenario 3 ("missing files are created, existing preserved"), and FR-004 ("preserving existing files and only adding missing ones")? Do all three definitions describe the same behavior? [Consistency, Spec §User Stories vs FR-004]

---

## Notes

- Items marked **[Gap]** indicate requirements that are present as open questions in spec.md §Edge Cases but have not been resolved as functional requirements.
- Items marked **[Traceability]** indicate requirements that exist but lack a clear chain between spec → plan → implementation artifacts.
- Items marked **[Consistency]** indicate potential conflicts between two sections that should describe the same behavior.
- Priority order for resolution before implementation begins: CHK023, CHK020, CHK025 (unresolved edge cases) → CHK009, CHK010, CHK011 (flag combination gaps) → CHK005, CHK006 (directory enumeration) → remaining traceability items.
