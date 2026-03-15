# Implementation Plan: Agent Instruction Prompt File System

**Branch**: `003-agent-prompt-governance` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-agent-prompt-governance/spec.md`

## Summary

Implement the governance layer that generates, loads, and validates 7 domain-specific
prompt files in `.specforge/prompts/`. These files enforce hard coding constraints
on every sub-agent task. The feature extends `specforge init` to generate governance
files from Jinja2 templates, adds `PromptLoader` for programmatic loading into a
`PromptSet`, and adds `specforge validate-prompts` for cross-file conflict detection.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x, Jinja2 3.x, Rich 13.x (all pre-existing); zero new deps in `core/`
**Storage**: Filesystem — `.specforge/prompts/` directory; `.specforge/config.json` for project metadata (stack, version)
**Testing**: pytest, pytest-cov, syrupy (snapshot tests for rendered governance templates)
**Target Platform**: Cross-platform CLI (Windows/macOS/Linux)
**Project Type**: CLI tool extension — new subcommand + new core module
**Performance Goals**: `PromptLoader.load_for_feature()` completes in ≤500 ms (FR-011, SC-003)
**Constraints**: Zero external dependencies in `src/specforge/core/`; all Markdown parsing via Python `re` + `str` built-ins
**Scale/Scope**: 7 governance domains × 6 stacks = up to 42 template variants; each file ~200–500 lines of Markdown

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle | Status | Notes |
|------|-----------|--------|-------|
| G-01 | Spec-First: spec.md + plan.md exist before code | ✅ PASS | This plan is Phase 1 output |
| G-02 | Architecture: core/ has zero external deps | ✅ PASS | Markdown parsing via `re` only |
| G-03 | Architecture: Jinja2 for all file generation | ✅ PASS | All 7 governance templates are `.md.j2` files |
| G-04 | Code Quality: Python 3.11+ strict type hints | ✅ PASS | Enforced at implementation |
| G-05 | Code Quality: functions ≤30 lines, classes ≤200 lines | ✅ PASS | Split into focused helper methods |
| G-06 | Code Quality: Result[T] for recoverable errors | ✅ PASS | `PromptLoader` returns `Result[PromptSet, str]` |
| G-07 | Code Quality: DI via constructor injection | ✅ PASS | All new classes accept `project_root: Path` via constructor |
| G-08 | Code Quality: no magic strings | ✅ PASS | `GOVERNANCE_DOMAINS`, `PRECEDENCE_ORDER` added to `config.py` |
| G-09 | Testing: TDD — tests written before implementation | ✅ PASS | Enforced by tasks ordering |
| G-10 | File Structure: modules placed in correct layer | ✅ PASS | core/ for domain logic, cli/ for command, templates/governance/ for .j2 |

**Complexity Tracking**: No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-prompt-governance/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── cli-commands.md  # validate-prompts contract (extends Feature 002 contracts)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code

```text
src/specforge/
├── cli/
│   └── validate_prompts_cmd.py    # specforge validate-prompts command
├── core/
│   ├── prompt_manager.py          # PromptFileManager — generate + CRUD governance files
│   ├── prompt_loader.py           # PromptLoader — load + parse all 7 into PromptSet
│   ├── prompt_validator.py        # PromptValidator — cross-file conflict detection
│   └── prompt_context.py         # PromptContextBuilder — build agent context string
└── templates/
    └── base/
        └── governance/            # NEW — must be under base/ for TemplateRegistry discovery
            ├── _base_governance.md.j2 # Base template (excluded by _ prefix)
            ├── architecture.md.j2     # Agnostic only (no stack variants)
            ├── backend.md.j2          # Generic fallback
            ├── backend.dotnet.md.j2
            ├── backend.nodejs.md.j2
            ├── backend.python.md.j2
            ├── backend.go.md.j2
            ├── backend.java.md.j2
            ├── frontend.md.j2         # Agnostic only
            ├── database.md.j2         # Agnostic only
            ├── security.md.j2         # Agnostic only
            ├── testing.md.j2          # Generic fallback
            ├── testing.dotnet.md.j2
            ├── testing.nodejs.md.j2
            ├── testing.python.md.j2
            ├── testing.go.md.j2
            ├── testing.java.md.j2
            ├── cicd.md.j2             # Generic fallback
            └── cicd.github-actions.md.j2

tests/
├── unit/
│   ├── test_prompt_manager.py     # PromptFileManager unit tests
│   ├── test_prompt_loader.py      # PromptLoader unit tests
│   ├── test_prompt_validator.py   # Conflict detection unit tests
│   └── test_prompt_context.py    # PromptContextBuilder unit tests
├── integration/
│   └── test_validate_prompts_cmd.py  # CLI integration test (tmp_path)
└── snapshots/
    └── test_governance_templates/ # syrupy snapshots per domain+stack
        └── (auto-generated)
```

**Structure Decision**: Single-project layout extending the existing `src/specforge/` tree.
Governance templates placed at `src/specforge/templates/base/governance/` — MUST be under
`base/` because `TemplateRegistry._discover_built_in()` anchors to `templates/base/` and
iterates `_TYPE_MAP` subdirectories beneath it. A new `"governance": TemplateType.governance`
entry added to `_TYPE_MAP` enables auto-discovery. `frontend`, `database`, and `security`
have no stack-specific variants — only agnostic files are generated for these domains.

## Key Decisions

| ID | Decision | Rationale | Alternative Rejected |
|----|----------|-----------|----------------------|
| R-01 | Governance templates in `templates/base/governance/` as a new `TemplateType.governance` | Must be under `base/` for `TemplateRegistry._discover_built_in()` to auto-discover them; avoids mixing with agent-operation prompts | Top-level `templates/governance/` — not scanned by registry; would be dead code |
| R-02 | File naming: `{domain}.{stack}.prompts.md` for stack-specific, `{domain}.prompts.md` for agnostic | Allows multiple stacks to coexist in same project directory without overwriting; enables future multi-stack projects | Flat naming `backend.prompts.md` with stack in content only — loses the ability to have dotnet + nodejs governance side-by-side |
| R-03 | Markdown parsing via Python `re` + heading traversal — no external parser | Constitution Gate G-02: core/ must have zero external deps | `python-frontmatter` or `mistune` — external deps prohibited in core/ |
| R-04 | SHA-256 checksum in `## Meta` section for change detection on `--force` | Deterministic: any edit to the file changes the hash; no separate tracking file needed | External tracking file (`.specforge/prompts/.checksums.json`) — extra file, more failure modes |
| R-05 | `PromptContextBuilder` loads all 7 files (per spec clarification) — task type affects ordering only, not filtering | Spec Q2 answer: "always load all 7 to avoid mis-classification bugs" | Filtering by task type — contradicts spec clarification, risks excluding relevant constraints |
| R-06 | `PromptLoader` reads project stack from `.specforge/config.json` (new) | `PromptLoader.load_for_feature(feature_id)` has no stack parameter; the loader must independently know the project's stack | Re-parsing all `.specforge/prompts/` filenames to infer stack — fragile, breaks with custom filenames |
| R-07 | `TemplateRegistry` extended to discover `governance/` subdirectory | Reuses proven discovery/resolution machinery; governance templates benefit from the same 4-step resolution chain (user-override → built-in, stack-specific → generic) | Separate loader class — code duplication |
| R-08 | Intra-group conflicts (backend/frontend/database same threshold, different values) → `ConflictEntry.is_ambiguous=True` + reported, not silently resolved | Spec clarification: equal-priority conflicts "flagged for manual resolution" | Picking the first-encountered file's value — non-deterministic, masks governance drift |

## Phase 0: Research

See [`research.md`](research.md) — all unknowns resolved.

## Phase 1: Design

See [`data-model.md`](data-model.md) for complete entity definitions, parsing
algorithm, and conflict detection flow.

See [`contracts/cli-commands.md`](contracts/cli-commands.md) for `validate-prompts`
binding contract.

### Core Module Algorithmic Flows

#### PromptFileManager.generate(project_root, config)

```text
1. For each domain in GOVERNANCE_DOMAINS:
   a. Resolve template: registry.get(domain, TemplateType.governance, stack)
      → falls back to generic if no stack-specific variant exists
   b. Render template with Jinja2 (project_name, stack, date, stack_hint)
   c. Compute SHA-256 of rendered content
   d. Inject checksum into rendered ## Meta block
   e. Determine output filename:
      - AGNOSTIC_GOVERNANCE_DOMAINS → "{domain}.prompts.md"
      - Otherwise → "{domain}.{stack}.prompts.md"
   f. Write to .specforge/prompts/
2. Write .specforge/config.json with {stack, project_name, version}
3. Return Ok(list[Path]) of written files
```

#### PromptFileManager.is_customized(file_path, project_root, stack)

```text
1. Read file_path → parse ## Meta → extract stored checksum
2. Determine domain from filename
3. Re-render template for (domain, stack) using TemplateRegistry
4. Compute SHA-256 of freshly rendered content
5. Return stored_checksum != fresh_checksum
```

#### PromptLoader.load_for_feature(feature_id)

```text
1. Read .specforge/config.json → get stack
2. missing: list[str] = []
3. For each domain in GOVERNANCE_DOMAINS:
   a. Try: .specforge/prompts/{domain}.{stack}.prompts.md
   b. Fallback: .specforge/prompts/{domain}.prompts.md
   c. If neither found: missing.append(domain + expected paths)
4. If missing: return Err(format_missing_message(missing))
5. Parse each file: _parse_prompt_file(path, raw_content)
   → extract PromptFileMeta (domain, stack, version, precedence, checksum)
   → extract PromptRules (rule_id, title, severity, scope, description, thresholds, examples)
6. Return Ok(PromptSet(files={domain: PromptFile}, precedence=PRECEDENCE_ORDER))
   → completes within 500 ms (reads ~7 Markdown files, no network I/O)
```

#### PromptValidator.detect_conflicts(prompt_set)

```text
1. threshold_index: dict[str, list[tuple[str, str, str]]] = {}
   # threshold_key → [(domain, rule_id, value), ...]
2. For each (domain, file) in prompt_set.files:
   For each rule in file.rules:
     For each threshold in rule.thresholds:
       threshold_index[threshold.key].append((domain, rule.rule_id, threshold.value))
3. conflicts: list[ConflictEntry] = []
4. For each threshold_key, entries in threshold_index:
   If len(unique values) > 1:
     Sort entries by PRECEDENCE_ORDER index (ascending = higher priority)
     winner = entries[0]  (highest precedence)
     is_ambiguous = all entries[i].precedence_rank == entries[0].precedence_rank
     For each loser in entries[1:]:
       conflicts.append(ConflictEntry(
         rule_id=winner.rule_id, threshold_key=threshold_key,
         domain_a=winner.domain, value_a=winner.value,
         domain_b=loser.domain, value_b=loser.value,
         winning_domain=winner.domain if not is_ambiguous else "AMBIGUOUS",
         is_ambiguous=is_ambiguous,
         suggested_resolution=_build_suggestion(winner, loser, is_ambiguous)
       ))
5. Return ConflictReport(conflicts=tuple(conflicts), has_conflicts=bool(conflicts))
```

### Deferred Items

| ID | Item | Reason |
|----|------|--------|
| D-01 | Template variable substitution (`{{MAX_FUNCTION_LINES}}`) | Spec clarification: deferred to future phase; all thresholds hardcoded in template text |
| D-02 | `architecture.prompts.md` stack-specific variants | Architecture file is intentionally cross-cutting and agnostic |
| D-03 | Multi-stack project support (loading dotnet + nodejs governance simultaneously) | Not in spec scope; single active stack per project via config.json |
| D-04 | Rule severity enforcement in PromptContextBuilder output | Formatting-only concern; enforcement happens at sub-agent level via rule text |
