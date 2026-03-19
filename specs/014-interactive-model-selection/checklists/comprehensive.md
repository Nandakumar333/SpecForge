# Comprehensive Checklist: Interactive AI Model Selection & Commands Directory

**Purpose**: Validate requirement completeness, clarity, consistency, and coverage across spec, plan, data model, and contracts — PR reviewer depth
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Are requirements defined for how the agent list is presented visually (layout, grouping, scrolling for 24+ items)? [Gap]
- [ ] CHK002 - Are requirements specified for what happens when the plugin registry returns zero agents (empty list scenario)? [Gap]
- [ ] CHK003 - Is the exact prompt wording ("Which AI agent do you want to use?") defined as a constant or left as implementation detail? [Clarity, Spec §FR-001]
- [ ] CHK004 - Are requirements specified for all 8 pipeline stage template contents (decompose, specify, research, plan, tasks, implement, status, check)? [Gap, Spec §FR-007]
- [ ] CHK005 - Is the governance scaffold behavior for recognized agents (non-generic) explicitly stated — do they also get constitution + 7 domain prompts, or only generic? [Gap, Spec §FR-018]
- [ ] CHK006 - Are requirements defined for how `--agent` values are validated against the plugin registry? [Gap, Spec §FR-004]
- [ ] CHK007 - Is the behavior specified when `--agent` receives an unrecognized agent name? [Edge Case, Gap]
- [ ] CHK008 - Are requirements for the `ScaffoldResult.commands_written` field defined in the spec, or only in the plan? [Traceability, Gap]
- [ ] CHK009 - Is the default `commands_dir` for each of the 25 plugins explicitly documented or only in research R3? [Completeness]
- [ ] CHK010 - Are requirements specified for the Copilot `.prompt.md` YAML frontmatter structure (exact fields, values)? [Gap, Spec §FR-022]

## Requirement Clarity

- [ ] CHK011 - Is "ready-to-use prompt appropriate for its pipeline stage" (FR-007) quantified with specific content expectations per stage? [Clarity, Spec §FR-007]
- [ ] CHK012 - Is "agent-appropriate paths for others" (FR-008) defined for all 25 plugins, or only the 6 with explicit overrides? [Ambiguity, Spec §FR-008]
- [ ] CHK013 - Is the distinction between FR-020 ("abstract property") and Design Decision D-01 ("concrete defaults, not abstract") reconciled? [Conflict, Spec §FR-020 vs Plan §D-01]
- [ ] CHK014 - Is "project-specific context variables filled in" (Story 2, Scenario 3) specified — which variables exactly? [Clarity, Spec §US-2]
- [ ] CHK015 - Is the term "force flag preserves existing files" precise about what "preserve" means (skip, backup, merge)? [Clarity, Spec §FR-013]
- [ ] CHK016 - Is "all registered agent plugins" (FR-002) explicitly defined as runtime discovery or compile-time list? [Ambiguity, Spec §FR-002]
- [ ] CHK017 - Is the "minimum 8 files" qualifier (FR-006) clear about when more than 8 files would be generated? [Clarity, Spec §FR-006]
- [ ] CHK018 - Are the agent-specific argument placeholders defined beyond Claude (`$ARGUMENTS`) and Gemini (`{{args}}`)? What do the other 22 agents use? [Clarity, Spec §FR-023]

## Requirement Consistency

- [ ] CHK019 - Does FR-020 ("abstract property") conflict with the data model showing "concrete defaults on base class"? [Conflict, Spec §FR-020 vs Data Model]
- [ ] CHK020 - Is the `commands_dir` default consistent between spec ("`.specforge/commands`" vs "`commands/`") for non-overriding agents vs generic? [Consistency, Spec §FR-008 vs Contract]
- [ ] CHK021 - Is the `"generic"` terminology consistently used across all 5 user stories, 25 FRs, and edge cases — no residual "agnostic" in agent context? [Consistency, Spec §FR-019]
- [ ] CHK022 - Are the naming conventions consistent: FR-006 says `specforge.{stage}` + extension, while User Story 2 says `specforge.{stage}.prompt.md` — do all agents get `.prompt.md` or only Copilot? [Conflict, Spec §FR-006 vs §US-2]
- [ ] CHK023 - Is the Copilot path consistent between FR-008 (`.github/prompts/`) and D-07 ("no separate companion stub") — does Copilot get ONE file or TWO per stage? [Conflict, Spec §FR-022 vs Plan §D-07]
- [ ] CHK024 - Does the edge case "no commands directory mapping → falls back to `.specforge/commands/`" align with the contract default of `.specforge/commands`? [Consistency, Edge Cases vs Contract]
- [ ] CHK025 - Is the `config.json` version field consistent — contract says "remains `1.0`" for additive fields, but spec has `"version": "1.0"` — should it note this explicitly? [Consistency, Contract §config-json-schema]

## Acceptance Criteria Quality

- [ ] CHK026 - Can SC-001 ("under 60 seconds") be objectively measured — is this a soft target or a hard gate? [Measurability, Spec §SC-001]
- [ ] CHK027 - Can SC-005 ("slash commands work immediately") be objectively verified for all agents, or only for specifically supported ones (Claude, Copilot, Gemini)? [Measurability, Spec §SC-005]
- [ ] CHK028 - Is SC-002 ("100% of recognized agents") testable given that agents vary in commands_dir support? [Measurability, Spec §SC-002]
- [ ] CHK029 - Are acceptance scenarios for User Stories 3–5 sufficient — does Story 3 test path validation rejection cases? [Coverage, Spec §US-3]
- [ ] CHK030 - Is SC-007 ("preserves 100% of edits") measurable — how is "edit preservation" verified (content diff, hash check, timestamp)? [Measurability, Spec §SC-007]

## Scenario Coverage

- [ ] CHK031 - Are requirements defined for the flow when `--agent` and interactive TTY are both present (explicit flag should win)? [Coverage, Spec §FR-004/FR-005]
- [ ] CHK032 - Are requirements defined for the re-init scenario: running `init` again on an already-initialized project without `--force`? [Gap]
- [ ] CHK033 - Are requirements specified for what happens when the commands directory is manually deleted between runs? [Gap, Edge Case]
- [ ] CHK034 - Are requirements defined for the dry-run + non-interactive combination (no TTY, `--dry-run`)? [Coverage, Spec §FR-014]
- [ ] CHK035 - Is the flow specified when `--agent generic --dry-run` is used — does the commands dir prompt still appear? [Coverage, Spec §FR-009/FR-014]
- [ ] CHK036 - Are requirements defined for concurrent init runs in the same directory (race condition)? [Gap, Edge Case]

## Edge Case & Boundary Coverage

- [ ] CHK037 - Is the behavior defined for `--agent CLAUDE` (case sensitivity) — must the value be lowercase? [Edge Case, Gap]
- [ ] CHK038 - Is path validation (FR-010) specified for edge inputs: empty string, whitespace-only, Windows backslashes, Unicode characters? [Edge Case, Spec §FR-010]
- [ ] CHK039 - Is the behavior defined when the custom commands directory path already exists as a file (not a directory)? [Edge Case, Gap]
- [ ] CHK040 - Is the maximum path length for custom commands directory specified or bounded? [Edge Case, Spec §FR-010]
- [ ] CHK041 - Are requirements defined for symlink handling — commands directory pointing to a symlink? [Edge Case, Gap]
- [ ] CHK042 - Is the behavior specified when template rendering fails for one stage but succeeds for others (partial failure)? [Edge Case, Gap]
- [ ] CHK043 - Is the Ctrl+C edge case (FR-015) defined for partial directory creation — what if 3 of 8 files are written before interrupt? [Edge Case, Spec §FR-015]

## Non-Functional Requirements

- [ ] CHK044 - Are performance requirements specified for the agent selection prompt (response time, rendering speed for 24+ items)? [Gap, NFR]
- [ ] CHK045 - Are accessibility requirements defined for the Rich prompt (screen reader support, keyboard navigation)? [Gap, NFR]
- [ ] CHK046 - Are requirements specified for command file encoding (UTF-8, BOM, line endings)? [Gap, NFR]
- [ ] CHK047 - Are disk space requirements or limits documented for the commands directory (8+ files × N agents)? [Gap, NFR]
- [ ] CHK048 - Are error message requirements specified for each failure mode (invalid agent, invalid path, template render error)? [Gap, NFR]

## Dependencies & Assumptions

- [ ] CHK049 - Is the assumption "Rich Prompt.ask() supports 24+ choices" validated — are there known UX issues at that list length? [Assumption]
- [ ] CHK050 - Is the assumption documented that `sys.stdin.isatty()` correctly detects all non-interactive environments (Docker, SSH, screen)? [Assumption, Spec §FR-005]
- [ ] CHK051 - Are dependencies between FR-019 (agnostic→generic rename) and existing test suites documented? [Dependency, Gap]
- [ ] CHK052 - Is the dependency on Jinja2 template availability at package install time documented? [Dependency, Spec §FR-016]
- [ ] CHK053 - Is the interaction between `--force` and the new `commands_dir` field in existing config.json specified? [Dependency, Spec §FR-013]

## Cross-Artifact Consistency

- [ ] CHK054 - Does the data model's `AgentPlugin` entity match the contract's `AgentPlugin` interface (same properties, same types, same defaults)? [Consistency, Data Model vs Contract]
- [ ] CHK055 - Is the `CommandRegistrar` interface consistent between the contract (4 methods) and the data model (4 methods) — same signatures? [Consistency, Data Model vs Contract]
- [ ] CHK056 - Do the plan's 4 implementation phases cover all 25 FRs — is there a traceability gap? [Traceability, Plan vs Spec]
- [ ] CHK057 - Does the research R3 mapping table (14 agents listed) account for all 25 plugins, or are 11 agents unmapped? [Completeness, Research vs Spec §FR-002]
- [ ] CHK058 - Are the plan's design decisions (D-01 through D-08) all traceable to specific FRs or clarifications? [Traceability, Plan vs Spec]

## Ambiguities & Conflicts

- [ ] CHK059 - Does FR-006 ("one command file per pipeline stage") conflict with FR-022 (Copilot gets a companion stub per stage, implying 2 files per stage)? [Conflict, Spec §FR-006 vs FR-022]
- [ ] CHK060 - Is the relationship between "generic" agent and the governance scaffold (FR-018) clear — why is this called out only for generic when all agents get governance? [Ambiguity, Spec §FR-018]
- [ ] CHK061 - Is the Copilot path resolved: D-07 says "no separate companion stub" but FR-022 says "generate a companion `.prompt.md` stub" — which is authoritative? [Conflict, Spec §FR-022 vs Plan §D-07]
- [ ] CHK062 - Is "sorted alphabetically with generic always last" (FR-002) clear about locale-specific sorting and case folding? [Ambiguity, Spec §FR-002]
- [ ] CHK063 - Is the distinction between `command_extension` (`.md`, `.toml`, `.prompt.md`) and file naming convention clearly specified for all agents? [Ambiguity, Spec §FR-006 vs Research §R3]

## Notes

- **Focus**: Comprehensive multi-domain review covering all spec artifacts
- **Depth**: Standard — suitable for PR reviewer validating spec readiness
- **Audience**: PR reviewer assessing spec/plan quality before implementation
- **Key concern**: The FR-020 vs D-01 conflict (abstract vs concrete properties) and the Copilot dual-file ambiguity (FR-022 vs D-07) need explicit resolution before implementation begins
