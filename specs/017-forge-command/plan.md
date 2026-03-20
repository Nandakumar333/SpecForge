# Implementation Plan: Forge Command — Zero-Interaction Full Spec Generation

**Branch**: `017-forge-command` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-forge-command/spec.md`

## Summary

Add a `specforge forge` command that orchestrates the entire spec generation pipeline — auto-init, LLM-driven decompose, parallel 7-phase spec generation, validation, and reporting — in a single unattended invocation. Includes structured artifact extraction to replace raw concatenation, enriched Jinja2-based phase prompts, persistent forge state for resume, and a Rich Live progress dashboard. All LLM calls use the existing SubprocessProvider.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output + Live dashboard), Jinja2 3.x (template rendering), GitPython 3.x, PyYAML 6.x — all existing
**Storage**: File system — `.specforge/forge-state.json` (forge progress), `.specforge/features/<slug>/` (per-service artifacts), `.specforge/reports/forge-report.md` (completion report)
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)
**Project Type**: CLI tool (extending existing SpecForge CLI)
**Performance Goals**: Token budget for phase prompts — structured extraction must reduce token usage by 30%+ vs raw concatenation (SC-005).
**Scale/Scope**: 56+ LLM calls per full forge run (7 phases × 8 services). Up to 4 concurrent workers default. Single user per forge run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Gate | Status | Notes |
|---|-----------|------|--------|-------|
| I | Spec-First Development | spec.md exists before implementation | PASS | spec.md complete with 6 user stories, 18 FRs, 7 SCs, 11 edge cases |
| II | Architecture | Core logic has zero external deps; plugin system for agents; Jinja2 for output | PASS | All file output via Jinja2 templates (enrichment templates). Plugin-style agent adapters preserved. No new external deps in core. |
| III | Code Quality | Type hints, ≤30 line functions, ≤200 line classes, Result[T], no magic strings, constructor injection | PASS | All new modules follow existing patterns. Constants in config.py. Result[T,E] for all recoverable errors. |
| IV | Testing | TDD — test files before implementation; unit + integration + snapshot | PASS | Test files listed in spec. Unit tests for all new core modules, integration test for end-to-end CLI. |
| V | Commit Strategy | Conventional commits, one per task | PASS | Will follow existing pattern. |
| VI | File Structure | Modules in correct architectural layer; no cross-layer imports | PASS | CLI in `cli/`, domain logic in `core/`, templates in `templates/`. No `core` → `cli` imports. |
| VII | Governance | Constitution supersedes all other docs | PASS | No conflicts. |

**Gate violations requiring justification:**

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | No constitution violations in current scope. | HttpApiProvider (httpx dependency) was removed from scope per spec clarifications. |

## Project Structure

### Documentation (this feature)

```text
specs/017-forge-command/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── forge-cli.md     # CLI command contract
│   └── forge-state.md   # forge-state.json schema
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── main.py                    # Modified: add forge command
│   └── forge_cmd.py               # NEW: "specforge forge" Click command
├── core/
│   ├── config.py                  # Modified: add forge constants
│   ├── prompt_assembler.py        # Modified: use ArtifactExtractor
│   ├── phase_prompts.py           # Modified: add enrichment_template field
│   ├── forge_orchestrator.py      # NEW: orchestrates init→decompose→spec→validate
│   ├── forge_state.py             # NEW: persisted forge state for resume
│   ├── artifact_extractor.py      # NEW: structured extraction from prior artifacts
│   ├── enriched_prompts.py        # NEW: rich phase prompt builders
│   └── forge_progress.py          # NEW: live Rich dashboard for forge
├── templates/
│   └── base/
│       └── enrichment/            # NEW: Jinja2 enrichment templates per phase
│           ├── spec_enrichment.md.j2
│           ├── research_enrichment.md.j2
│           ├── datamodel_enrichment.md.j2
│           ├── edgecase_enrichment.md.j2
│           ├── plan_enrichment.md.j2
│           ├── checklist_enrichment.md.j2
│           ├── tasks_enrichment.md.j2
│           └── decompose_enrichment.md.j2
└── ...

tests/
├── unit/
│   ├── test_forge_orchestrator.py  # NEW
│   ├── test_artifact_extractor.py  # NEW
│   ├── test_enriched_prompts.py    # NEW
│   └── test_forge_state.py         # NEW
└── integration/
    └── test_forge_end_to_end.py    # NEW
```

**Structure Decision**: Single project structure (Option 1). All new modules follow existing layer conventions — CLI commands in `cli/`, domain logic in `core/`, templates in `templates/base/enrichment/`. No new top-level directories needed. 5 new source files, 3 modified source files, 8 new enrichment templates.

## Constitution Check — Post-Design Re-evaluation

| # | Principle | Gate | Status | Notes |
|---|-----------|------|--------|-------|
| I | Spec-First Development | spec.md, plan.md, research.md, data-model.md exist | PASS | All design artifacts complete. |
| II | Architecture | Core has zero external deps; Jinja2 for output | PASS | No new external deps in core. All enrichment output via Jinja2 templates. No string concatenation for generated files. |
| III | Code Quality | ≤30 line functions, ≤200 line classes, Result[T], constructor injection | PASS | ForgeOrchestrator: ~180 lines total. ArtifactExtractor: stateless, each method ~15 lines. All use Result[T,E]. All use constructor injection. |
| IV | Testing | TDD — tests before implementation | PASS | 4 unit test files + 1 integration test file planned. Unit tests cover all new core modules. Integration test covers CLI end-to-end. |
| V | Commit Strategy | Conventional commits | PASS | One commit per task from tasks.md. |
| VI | File Structure | Correct architectural layers | PASS | forge_cmd.py in `cli/`, all domain logic in `core/`, enrichment templates in `templates/base/enrichment/`. No cross-layer imports. |
| VII | Governance | Constitution supersedes | PASS | No unresolved conflicts. |

**Post-design gate result**: ALL PASS. No new external dependencies required — all LLM calls use existing SubprocessProvider.
