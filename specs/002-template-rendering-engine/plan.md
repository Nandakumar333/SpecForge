# Implementation Plan: Template Rendering Engine

**Branch**: `002-template-rendering-engine` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-template-rendering-engine/spec.md`

## Summary

Build the template rendering engine that powers all file generation in SpecForge. This replaces the current minimal `template_loader.py` (single function, no validation, no overrides) with a complete system: a **TemplateRegistry** for discovery and resolution, a **TemplateRenderer** wrapping Jinja2 with custom filters and extends/block inheritance, a **TemplateValidator** for post-render quality checks, and a **StackAdapter** mapping tech stacks to template variable sets. The engine supports user overrides via `.specforge/templates/`, stack-specific prompt variants via dot-notation naming, reusable partials, and generation headers on all output.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Jinja2 3.x (rendering engine), Click 8.x (existing CLI), Rich 13.x (existing output)
**Storage**: File system — `.md.j2` template files in package + user project directory
**Testing**: pytest + pytest-cov + syrupy (snapshot tests) + ruff (linting)
**Target Platform**: Cross-platform CLI tool (Windows, macOS, Linux)
**Project Type**: CLI tool / Library
**Performance Goals**: Any single template renders in < 100ms; full scaffold (30+ files) in < 2 seconds
**Constraints**: Must remain backward-compatible with Feature 001 scaffold pipeline during migration; all existing snapshot tests must continue to pass or be intentionally updated
**Scale/Scope**: ~30 built-in templates (17 existing migrated + 13 new); 5 supported stacks × 7 prompt types = up to 35 stack variants; unlimited user overrides

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md complete with clarifications; plan.md (this file) in progress; tasks.md next |
| II. Architecture | ✅ PASS | All new modules in `core/` (Clean Architecture). Jinja2 is the sanctioned template engine per constitution: "All file generation MUST use Jinja2 templates." Plugin boundary preserved — StackAdapter maps stacks without coupling core to specific tech details. |
| III. Code Quality | ✅ PASS | All functions will use strict type hints, Result[T] for errors, constructor injection for TemplateRegistry/Renderer. Functions ≤ 30 lines enforced. Constants in config.py. |
| IV. Testing | ✅ PASS | TDD enforced. Snapshot tests for all template output. Unit tests for registry, renderer, validator, adapter. Integration tests for scaffold pipeline. |
| V. Commit Strategy | ✅ PASS | Conventional Commits. One commit per task. |
| VI. File Structure | ✅ PASS | New modules follow established layer boundaries: `core/` for domain logic, `templates/` for .j2 files, `plugins/` untouched. |
| VII. Governance | ✅ PASS | Spec → Plan → Tasks flow followed. No conflicts. |

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-template-rendering-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── template-engine-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/specforge/
├── core/
│   ├── template_registry.py     # NEW — Template discovery, catalog, resolution
│   ├── template_renderer.py     # NEW — Jinja2 wrapper with filters, inheritance, header
│   ├── template_validator.py    # NEW — Post-render validation (placeholders, structure)
│   ├── stack_adapter.py         # NEW — Stack name → template variable set mapping
│   ├── template_loader.py       # DEPRECATED → replaced by template_renderer.py
│   ├── scaffold_builder.py      # MODIFIED — Use registry instead of hardcoded lists
│   ├── scaffold_writer.py       # MODIFIED — Use renderer + validator pipeline
│   ├── config.py                # MODIFIED — New template type constants, prompt/feature lists
│   ├── project.py               # MODIFIED — New dataclasses for template metadata
│   └── result.py                # UNCHANGED
├── templates/
│   ├── __init__.py              # UNCHANGED
│   ├── base/                    # NEW — Reorganized built-in templates
│   │   ├── partials/            # NEW — Reusable template fragments
│   │   │   ├── out-of-scope.md.j2
│   │   │   └── generation-header.md.j2
│   │   ├── constitution.md.j2   # MOVED from templates/ root
│   │   ├── decisions.md.j2      # MOVED from templates/ root
│   │   ├── gitignore.j2         # MOVED from templates/ root
│   │   ├── prompts/             # NEW — 7 agent prompts + base + stack variants
│   │   │   ├── _base_prompt.md.j2     # Base template with blocks
│   │   │   ├── backend.md.j2          # Generic backend (extends _base_prompt)
│   │   │   ├── backend.dotnet.md.j2   # Stack variant (extends backend.md.j2)
│   │   │   ├── backend.nodejs.md.j2
│   │   │   ├── backend.python.md.j2
│   │   │   ├── frontend.md.j2
│   │   │   ├── database.md.j2
│   │   │   ├── security.md.j2
│   │   │   ├── testing.md.j2
│   │   │   ├── cicd.md.j2
│   │   │   └── api-design.md.j2
│   │   └── features/            # MODIFIED — Renamed + 2 new templates
│   │       ├── spec.md.j2
│   │       ├── research.md.j2
│   │       ├── datamodel.md.j2
│   │       ├── plan.md.j2
│   │       ├── checklist.md.j2  # NEW
│   │       ├── edge-cases.md.j2 # NEW
│   │       └── tasks.md.j2
│   ├── prompts/                 # DEPRECATED — Old prompt templates (removed after migration)
│   └── features/                # DEPRECATED — Old feature templates (removed after migration)
└── plugins/
    └── agents/
        └── base.py              # UNCHANGED

tests/
├── unit/
│   ├── test_template_registry.py    # NEW
│   ├── test_template_renderer.py    # NEW
│   ├── test_template_validator.py   # NEW
│   ├── test_stack_adapter.py        # NEW
│   ├── test_scaffold_plan.py        # MODIFIED — Updated for registry-based builder
│   └── test_scaffold_writer.py      # MODIFIED — Updated for renderer+validator pipeline
├── integration/
│   └── test_init_cmd.py             # MODIFIED — E2E tests with new template system
└── snapshots/
    ├── test_template_rendering.py   # MODIFIED — New templates + stack variants
    └── __snapshots__/
        └── test_template_rendering.ambr  # REGENERATED
```

**Structure Decision**: Single project layout. All new code in existing `src/specforge/core/` and `src/specforge/templates/` directories. No new top-level packages or architectural layers. Templates reorganized under a `base/` subdirectory to cleanly separate built-in templates from the user-override discovery path.

## Complexity Tracking

No constitution violations to justify. All design decisions align with established patterns.
