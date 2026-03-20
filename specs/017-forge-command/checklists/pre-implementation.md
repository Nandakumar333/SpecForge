# Pre-Implementation Gate Checklist: Forge Command

**Purpose**: Validate requirements completeness, clarity, and consistency across spec.md, plan.md, and tasks.md before implementation begins
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 - Are all 7 CLI flags documented with types, defaults, and mutual exclusion rules? `--arch` default is "monolithic" [Spec §FR-002] but are `--resume` + `--force` mutually exclusive? [Gap] ✅ Fixed: FR-002 now states `--resume` and `--force` are mutually exclusive; empty description produces error
- [x] CHK002 - Are the exact 7 artifact filenames listed in the spec for validation purposes? FR-017 says "all 7 artifacts" but does not enumerate them (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) [Completeness, Spec §FR-017] ✅ Fixed: FR-017 now enumerates all 7 filenames
- [x] CHK003 - Is the forge-state.json schema fully defined with all fields, types, and valid values? FR-009 describes fields narratively but no formal schema is referenced [Completeness, Spec §FR-009] ✅ Fixed: FR-009 now defines stage enum values, per-service fields (status enum, phase range 0-7, retry reset, error type, timestamp)
- [ ] CHK004 - Are error message requirements defined for all user-facing error paths? (e.g., --skip-init on missing .specforge/, no provider available, all services failed) [Completeness, Gap]
- [ ] CHK005 - Are the forge-report.md required sections explicitly listed? FR-012 mentions "artifacts per service, failed services, elapsed time, stage timing" but no section headings or ordering [Completeness, Spec §FR-012]
- [ ] CHK006 - Is the decompose prompt enrichment content specified? FR-004 says "enriched decompose prompt" but does not describe what enrichment means for the decompose stage vs the 7 spec phases [Gap, Spec §FR-004]
- [x] CHK007 - Are requirements defined for what happens when `--dry-run` is combined with `--force`? Edge case lists `--dry-run` + `--resume` but not `--dry-run` + `--force` [Coverage, Gap] ✅ Fixed: FR-013 now states `--dry-run` + `--force` overwrites existing prompt files silently
- [x] CHK008 - Is the exit code behavior specified for all terminal outcomes? (success = 0, partial failure, total failure, user abort, --dry-run completion) [Gap] ✅ Fixed: FR-019 added with exit codes 0/1/2 for all outcomes
- [ ] CHK009 - Are the 7 expected artifact filenames consistent between spec (FR-017), tasks (T001 FORGE_ARTIFACTS), and plan (project structure)? US1 lists "checklist.md" but the existing pipeline may use a different name [Consistency]
- [x] CHK010 - Is the `--stack` flag behavior defined? FR-002 lists it but no FR describes what it does, how it's passed to init or decompose, or what values are valid [Gap, Spec §FR-002] ✅ Fixed: FR-002 now states --stack is passed to auto-init and decompose for stack-specific guidance

## Requirement Clarity

- [ ] CHK011 - Is "enriched decompose prompt" quantified? FR-004 distinguishes it from "thin 10-line" prompts but does not specify target line count or required sections for decompose specifically [Clarity, Spec §FR-004]
- [ ] CHK012 - Is "substantive content (not empty templates)" measurable? US1 Scenario 3 requires this but SC-002 only quantifies spec.md and plan.md (≥1500 words). Are the other 5 artifacts unquantified? [Measurability, Spec §SC-002]
- [ ] CHK013 - Is "50-100 lines per phase" for enriched prompts measured in rendered output lines or template source lines? [Clarity, Spec §FR-007]
- [ ] CHK014 - Is "at least every 5 seconds" for dashboard updates a refresh interval or a maximum staleness guarantee? [Clarity, Spec §SC-004]
- [x] CHK015 - Is "permanently failed" service status clearly distinguished from "failed"? FR-010 mentions "up to 3 retries" but does the retry count reset between forge runs or accumulate across `--resume` invocations? [Clarity, Spec §FR-010] ✅ Fixed: FR-009 states retry count resets to 0 on each new --resume invocation; FR-010 clarifies "per resume invocation"
- [x] CHK016 - Is the token estimation method for `--dry-run` defined? T024 uses `len(prompt) / 4` approximation — is this documented in the spec as the accepted method? [Clarity, Gap] ✅ Fixed: FR-013 now specifies "character count / 4" as the estimation method

## Requirement Consistency

- [x] CHK017 - Does plan.md still reference HttpApiProvider, httpx, and httpx-sse as dependencies despite the spec clarification removing them from scope? Plan summary says "Includes a direct HTTP API provider for Anthropic (httpx + SSE streaming)" — this contradicts the spec [Conflict, plan.md §Summary vs Spec §Clarifications] ✅ Fixed: plan.md fully updated to remove all HttpApiProvider/httpx references
- [x] CHK018 - Does the plan.md project structure list `http_api_provider.py` and `test_http_api_provider.py` as NEW files despite those being removed from scope? [Conflict, plan.md §Project Structure vs Spec §Clarifications] ✅ Fixed: plan.md project structure cleaned
- [x] CHK019 - Does the plan.md Complexity Tracking justify httpx as a dependency when it's no longer needed? The justification references HttpApiProvider which is out of scope [Conflict, plan.md §Complexity Tracking vs Spec §Clarifications] ✅ Fixed: Complexity Tracking table cleared
- [x] CHK020 - Does the plan.md Performance Goals reference "HTTP API provider" and "SC-002" / "SC-004" metrics that were removed from the spec? [Conflict, plan.md §Technical Context vs Spec §Success Criteria] ✅ Fixed: Performance goals updated to current SCs
- [ ] CHK021 - Are the user story numbers consistent between spec and tasks? Spec has US1-US6, tasks has US1-US6, but the original spec had US1-US7 before clarification — is the renumbering complete? [Consistency]
- [ ] CHK022 - Does T001 FORGE_ARTIFACTS constant match the 7 filenames used in US1 Scenario 3 and FR-017 validation? [Consistency, tasks.md §T001 vs Spec §FR-017]

## Acceptance Criteria Quality

- [ ] CHK023 - Is SC-002 (≥1500 words for spec.md and plan.md) testable without running a full LLM-backed forge? Can unit tests verify prompt quality produces this outcome? [Measurability, Spec §SC-002]
- [x] CHK024 - Is SC-005 (30% token reduction) testable? Are there baseline measurements of raw concatenation token counts to compare against? [Measurability, Spec §SC-005] ✅ Fixed: SC-005 now specifies measurement method (character count / 4) and validation approach (3 test projects)
- [ ] CHK025 - Is SC-006 (90% success rate) a runtime metric or a test requirement? How should this be validated during implementation? [Measurability, Spec §SC-006]
- [ ] CHK026 - Can SC-003 (resume preserves completed work) be verified in an automated test without real LLM calls? T027 uses mock providers — is this sufficient? [Measurability, Spec §SC-003]

## Scenario Coverage

- [ ] CHK027 - Are requirements defined for `--resume` when the manifest.json has been manually edited between runs? (services added/removed) [Coverage, Exception Flow, Gap]
- [x] CHK028 - Are requirements defined for concurrent forge runs on the same project directory? Is there a file lock or detection mechanism? [Coverage, Gap] ✅ Fixed: FR-020 added with PID/timestamp lock and 1-hour stale lock auto-clear
- [x] CHK029 - Are requirements defined for what happens when the user provides an empty description string? [Coverage, Edge Case, Gap] ✅ Fixed: FR-002 now states empty description MUST produce clear error message
- [x] CHK030 - Are requirements defined for `--max-parallel 0` or `--max-parallel` with a negative value? [Coverage, Edge Case, Gap] ✅ Fixed: Edge case added — Click IntRange(min=1) validation
- [x] CHK031 - Are requirements defined for decompose producing zero services? (e.g., description too vague for LLM and DomainAnalyzer) [Coverage, Edge Case, Gap] ✅ Fixed: Edge case added — falls back to DomainAnalyzer, then fails with exit code 2 if still zero
- [x] CHK032 - Are requirements defined for what `--dry-run` does during the decompose stage? FR-013 says "runs auto-init and decompose" — does decompose make an LLM call in dry-run or use DomainAnalyzer only? [Coverage, Spec §FR-013] ✅ Fixed: FR-013 now clarifies decompose runs via LLM (or reads existing manifest if one exists)

## Edge Case Coverage

- [x] CHK033 - Is the behavior of `.draft.md` files on resume fully specified? FR-014 says they're saved on Ctrl+C, but does `--resume` detect and retry them vs ignore them? [Edge Case, Spec §FR-014] ✅ Fixed: FR-010 now states services with .draft.md MUST be retried from the phase that produced the draft
- [ ] CHK034 - Are disk space error requirements defined? A full 8-service forge produces ~56 files — what if the disk fills mid-generation? [Edge Case, Gap]
- [x] CHK035 - Is the forge-state.json save frequency specified? Is it saved after each phase completion, each stage completion, or only on stage boundaries? FR-009 mentions "timestamp of last update" but not save frequency [Edge Case, Spec §FR-009] ✅ Fixed: FR-009 now specifies "after each stage completion and after each service phase completion"
- [ ] CHK036 - Is the behavior specified when a service directory already exists with artifacts from a previous (non-forge) run? (e.g., user manually ran decompose + specify for some services) [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK037 - Are performance requirements defined for the forge command startup time? (init stage should be <2 seconds per the user's original specification) [Gap]
- [ ] CHK038 - Is the maximum supported number of services specified? Assumptions mention "up to 20 services" for Feature 016 but the forge spec does not reference a limit [Gap]
- [ ] CHK039 - Are logging requirements defined? FR-014 mentions "logs a warning" for corrupt state, but is there a general logging strategy for forge operations? [Gap]
- [ ] CHK040 - Are memory requirements defined for parallel execution? 4 concurrent workers each may hold large prompt strings in memory [Gap]

## Dependencies & Assumptions

- [ ] CHK041 - Is the assumption that ParallelPipelineRunner (Feature 016) exists validated? Can implementation proceed if that feature has API changes? [Assumption, Spec §Assumptions]
- [ ] CHK042 - Is the assumption that DomainAnalyzer (Feature 004) can produce manifests from description alone validated? Has this been tested? [Assumption, Spec §Assumptions]
- [ ] CHK043 - Is the assumption that `specforge init` logic supports non-interactive mode validated? Feature 001 may require prompts for agent/stack selection [Assumption, Spec §Assumptions]
- [ ] CHK044 - Is the assumption that governance prompt files (Feature 003) are optional correctly reflected in the enrichment templates? Templates must render without errors when no governance files exist [Assumption, Spec §Assumptions]

## Ambiguities & Conflicts

- [x] CHK045 - The plan.md is stale: it references HttpApiProvider, httpx, httpx-sse, http_api_provider.py, test_http_api_provider.py, and performance goals tied to the HTTP provider — all removed from scope per spec clarifications. Plan.md should be updated before implementation to prevent confusion [Conflict, plan.md vs Spec §Clarifications] ✅ Fixed: plan.md fully updated
- [x] CHK046 - The plan.md lists `llm_provider.py` as "Modified: add HttpApiProvider to ProviderFactory" — this modification is no longer needed. Is llm_provider.py modified for any other reason? [Ambiguity, plan.md §Project Structure] ✅ Fixed: llm_provider.py modification removed from plan.md
- [x] CHK047 - The plan.md Constitution Check justifies httpx as a dependency violation — this justification is moot since httpx is no longer needed. Should the Complexity Tracking table be cleared? [Conflict, plan.md §Complexity Tracking] ✅ Fixed: Complexity Tracking table cleared
- [x] CHK048 - FR-015 says "retry with exponential backoff matching the existing SubprocessProvider retry logic" — is this a new requirement for forge or a reminder that existing retry behavior applies? If the latter, is a separate FR needed? [Ambiguity, Spec §FR-015] ✅ Fixed: FR-015 reworded to clarify it confirms inherited behavior, not a new implementation

## Notes

- **Focus areas**: Pre-implementation gate, full depth, reviewer audience
- **Depth level**: Standard (comprehensive)
- **Actor/timing**: Reviewer before implementation begins
- **Critical finding**: plan.md is significantly stale after the HttpApiProvider removal — 6+ references to removed scope remain. Recommend updating plan.md before starting implementation to avoid confusion during tasks T005-T017.
- **Must-have items incorporated**: All 6 user-provided categories validated (Forge Command, Enriched Prompts, Artifact Extraction, Forge Orchestrator, Progress Dashboard, Integration). HTTP API Provider category intentionally excluded per spec clarification. httpx dependency conflict flagged.
