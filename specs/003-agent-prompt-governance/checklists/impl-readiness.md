# Implementation Readiness Checklist: Agent Instruction Prompt File System

**Purpose**: Validate specification and plan completeness before implementation begins
**Created**: 2026-03-15
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Audience**: PR reviewer / feature author
**Depth**: Standard

---

## Requirement Completeness

- [X] CHK001 - Are all 4 user stories accompanied by complete Given/When/Then acceptance scenarios (not just a single sentence)? [Completeness, Spec §US1–US4]
- [X] CHK002 - Does US3 (PromptLoader API) have an acceptance scenario that directly tests the `precedence` field of the returned `PromptSet` — separate from conflict detection? [Completeness, Spec §US3 scenario 2]
- [X] CHK003 - Does US4 (conflict detection) have an acceptance scenario covering the **intra-group ambiguous** case (backend vs database same threshold), not just the cross-priority case? [Completeness, Spec §US4, FR-006]
- [X] CHK004 - Is the purpose and content scope of each of the 7 governance files individually described in the spec (architecture, backend, frontend, database, security, testing, cicd)? [Completeness, Gap]
- [X] CHK005 - Are the minimum content requirements per governance file (at least 2 code examples, at least 3 numeric thresholds) specified as acceptance criteria for **each domain**, or only stated once as a general rule? [Completeness, Spec §FR-004, FR-005]
- [X] CHK006 - Is `PromptContextBuilder` mentioned anywhere in the spec, or is it defined only in the plan? If only in plan, is the agent context string format a requirement or an implementation detail? [Completeness, Gap]
- [X] CHK007 - Are requirements defined for what `PromptLoader.load_for_feature()` returns when `config.json` is missing or malformed (not just when prompt files are missing)? [Completeness, Spec §FR-010, Gap]
- [X] CHK008 - Is the format of `PromptRule.rule_id` (e.g., `^[A-Z]+-\d{3}$`) specified as a requirement, or only as an implementation convention in the plan? [Completeness, Spec §Key Entities, Gap]

---

## Requirement Clarity

- [X] CHK009 - Is "meaningfully different" in FR-002 quantified — e.g., does it specify a minimum number of stack-specific constructs, library names, or rules that must differ between stacks? [Clarity, Spec §FR-002]
- [X] CHK010 - Is "the same measurable rule" (used in FR-012 and SC-004) defined with enough precision to determine when two rules across files are "the same"? The spec implies threshold key matching — is this explicitly stated? [Clarity, Spec §FR-012, SC-004]
- [X] CHK011 - Is "original generated state" (FR-014, `--force` customization detection) defined with a measurable criterion, or left to implementation? SHA-256 checksum is the plan decision (R-04) — does the spec reference this mechanism? [Clarity, Spec §FR-014, Gap]
- [X] CHK012 - Does the spec define the exact output format required for `specforge validate-prompts` (table, plain text, JSON) or only the required data fields? [Clarity, Spec §FR-012]
- [X] CHK013 - Is "a one-line suggested resolution" (FR-012, SC-004) defined precisely enough to be testable — i.e., does the spec state what a valid suggestion looks like vs an invalid one? [Clarity, Spec §FR-012]
- [X] CHK014 - Does the spec specify whether `PromptLoader` reads the project stack from `.specforge/config.json` or another source? The plan documents `config.json` (R-06) but the spec's FR-009 signature has no stack parameter — is the resolution mechanism a spec requirement? [Clarity, Spec §FR-009, Gap]

---

## Requirement Consistency

- [X] CHK015 - Does FR-001 ("7 prompt files") align with the plan's naming convention of `{domain}.{stack}.prompts.md` (which could produce more than 7 files in a multi-stack scenario)? Is the "7 files" requirement scoped to a single `specforge init` run? [Consistency, Spec §FR-001, Plan §R-02]
- [X] CHK016 - Does the spec's "all 7 prompt files always loaded" clarification (Session 2026-03-15, Q2) align with FR-009, which says `load_for_feature(feature_id)` — a feature-scoped parameter that implies selective loading might be possible? [Consistency, Spec §Clarifications, FR-009]
- [X] CHK017 - Is the precedence numbering consistent between the spec's FR-006 notation (`security > architecture > {backend=frontend=database} > testing > cicd`) and the plan's `PRECEDENCE_ORDER` list (security=1, testing=4, cicd=5)? Do equal-priority domains all have the same integer rank? [Consistency, Spec §FR-006, Plan §data-model.md]
- [X] CHK018 - Are the stack names consistent across all spec sections? FR-001 lists `dotnet, nodejs, python, go, java, agnostic` — does FR-015's "supported stack names" error message spec match this exact list? [Consistency, Spec §FR-001, FR-015]
- [X] CHK019 - Does the `StackProfile` entity description in the spec align with the existing `StackProfile` dataclass already in `template_models.py`? Are they the same concept or two different entities sharing a name? [Consistency, Spec §Key Entities, Conflict]

---

## Acceptance Criteria Quality

- [X] CHK020 - Is SC-001 ("under 5 seconds") measurable end-to-end — does it specify the measurement boundary (wall clock from CLI invocation to process exit, or just file write time)? [Measurability, Spec §SC-001]
- [X] CHK021 - Is SC-006 ("at least 80% of tasks on first generation attempt") measurable given that sub-agent task output quality is not deterministic? Does the spec define how this metric would be collected or validated? [Measurability, Spec §SC-006]
- [X] CHK022 - Is SC-004 ("detects 100% of direct threshold conflicts") precisely scoped — does it clarify that "direct threshold conflicts" means only numeric threshold key collisions, not semantic contradictions between rule descriptions? [Measurability, Spec §SC-004]
- [X] CHK023 - Does US4's acceptance scenario 1 ("both values, both source file names, the winning value per precedence") constitute a complete and testable Given/When/Then, or does it omit the "Given" setup state? [Acceptance Criteria Quality, Spec §US4 scenario 1]

---

## Scenario Coverage

- [X] CHK024 - Are requirements defined for tech-stack auto-detection when multiple stack markers co-exist in the same directory (e.g., both `package.json` and `pyproject.toml` present)? [Coverage, Spec §FR-016, Gap]
- [X] CHK025 - Are requirements defined for the output of `specforge validate-prompts` when called on a project where only a **subset** of the 7 governance files exist (partial initialization)? [Coverage, Spec §Edge Cases]
- [X] CHK026 - Are requirements defined for what `specforge init --stack ruby` (unsupported stack) returns — specifically the exit code, error message content, and enumeration of supported stacks? [Coverage, Spec §FR-015, Edge Cases]
- [X] CHK027 - Is there an acceptance scenario for US1 covering the `agnostic` stack (no `--stack` flag, no detectable markers) — confirming that agnostic files are generated and have language-agnostic content? [Coverage, Spec §US1 scenario 4]
- [X] CHK028 - Are requirements specified for the behaviour of `validate-prompts` when `.specforge/config.json` is absent but governance files exist? [Coverage, Gap]

---

## Edge Case Coverage

- [X] CHK029 - Is the edge case of a malformed governance file (broken Markdown, missing `## Meta` section) addressed in both FR-010 and the edge cases list — and does FR-010 cover parse errors, not just missing files? [Edge Cases, Spec §FR-010, Edge Cases section]
- [X] CHK030 - Is the edge case of all 7 governance files deleted after initialization addressed in FR-010? Does the error message requirement specify that ALL missing files are listed in a single call (not one per call)? [Edge Cases, Spec §FR-010, Edge Cases section]
- [X] CHK031 - Are requirements defined for the edge case where a governance file contains a rule with a threshold key that is a duplicate within the same file (not a cross-file conflict)? [Edge Cases, Gap]
- [X] CHK032 - Is the edge case of `specforge init --force` on a project where some governance files are missing (never generated) and others are customized addressed — distinguishing "missing" from "customized"? [Edge Cases, Spec §FR-014, Edge Cases section]

---

## Non-Functional Requirements

- [X] CHK033 - Is the ≤500 ms performance requirement (FR-011, SC-003) specified for the worst-case scenario (all 7 files at maximum expected size), or only for "any supported project" without bounding file size? [NFR — Performance, Spec §FR-011]
- [X] CHK034 - Are security requirements defined for governance file content — specifically, is there a requirement preventing governance files from containing executable code, scripts, or injection payloads that a sub-agent might execute? [NFR — Security, Gap]
- [X] CHK035 - Are requirements defined for governance file encoding (UTF-8 assumed, but specified?) and maximum file size, given that the parser uses in-memory string operations? [NFR — Robustness, Gap]

---

## Dependencies & Assumptions

- [X] CHK036 - Is the integration contract between `PromptLoader` and the sub-agent executor (referenced as "Feature 009") documented anywhere in this feature's spec or plan — or is Feature 009 an undocumented external dependency? [Dependency, Gap]
- [X] CHK037 - Is the assumption that `.specforge/config.json` is always written by `specforge init` documented as a precondition in FR-009 or FR-016? A project initialized with an older SpecForge version that predates `config.json` would cause `PromptLoader` to fail. [Assumption, Spec §FR-009]
- [X] CHK038 - Is the dependency on `TemplateRegistry` (existing Feature 002 infrastructure) explicitly stated in this feature's spec or plan as a prerequisite? [Dependency, Gap]
- [X] CHK039 - Is the assumption that governance templates (`templates/governance/`) are shipped with the SpecForge package (not user-provided) stated as a requirement? [Assumption, Gap]

---

## Priority Resolution Guide

Items requiring spec updates before implementation can begin (highest risk):

1. **CHK006** — PromptContextBuilder not in spec at all; if it needs spec coverage, add now
2. **CHK011** — "original generated state" definition; without it FR-014 is untestable
3. **CHK014** — `config.json` as the stack source; spec-level gap creates ambiguity for implementers
4. **CHK019** — `StackProfile` name collision; spec entity vs existing dataclass in codebase
5. **CHK036** — Feature 009 dependency undocumented; blocks integration planning
