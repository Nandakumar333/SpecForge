# Implementation Plan: Plugin System for Multi-Agent and Multi-Stack Support

**Branch**: `013-plugin-system` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-plugin-system/spec.md`

## Summary

Build the plugin system that enables architecture-aware prompt file generation across multiple technology stacks and AI coding agents. Stack plugins (.NET, Node.js, Python in v1) return rule overrides parameterized by architecture type (microservice/monolith/modular-monolith), which are layered on top of base governance rules. Agent plugins (25+ in v1) generate agent-specific configuration files (CLAUDE.md, .cursorrules, .github/copilot-instructions.md, etc.). A PluginManager handles discovery, registration, and conflict resolution for both plugin types. Integration flows through init_cmd.py → PluginManager → PromptFileManager (merges rules into governance files) → PromptContextBuilder (reads merged files, unchanged).

## Technical Context

**Language/Version**: Python 3.11+ (existing)
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering) — all existing, no new dependencies
**Storage**: File system — `.specforge/prompts/` (governance files), `.specforge/config.json` (project metadata), agent config files at project root
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting) — all existing
**Target Platform**: Cross-platform CLI tool (Windows, macOS, Linux)
**Project Type**: CLI tool (Python package)
**Performance Goals**: Plugin discovery < 100ms for all built-in plugins; no user-perceptible delay at init
**Constraints**: Zero new external dependencies; all plugin rules bundled in package (no network fetches)
**Scale/Scope**: 3 stack plugins × 3 architectures = 9 rule combinations; 25+ agent plugins; custom plugin loading from project directory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Spec-First | ✅ PASS | spec.md completed with 6 user stories, 27 FRs, 5 clarifications |
| II. Architecture | ✅ PASS | Plugins in `src/specforge/plugins/`, domain logic in `core/`, templates in `templates/`. Clean Architecture boundaries preserved. All output via Jinja2 templates. |
| III. Code Quality | ✅ PASS | Type hints on all signatures, Result pattern for errors, constants in config.py. 30-line function / 200-line class limits apply. |
| IV. Testing | ✅ PASS | TDD: tests written before implementation. Unit tests for plugin logic, integration tests for CLI flow, snapshot tests for generated governance files. |
| V. Commit Strategy | ✅ PASS | Conventional commits, one per task. |
| VI. File Structure | ✅ PASS | All new modules in correct architectural layers. No cross-layer imports. |
| VII. Governance | ✅ PASS | No conflicts with constitution. |

**Gate result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/013-plugin-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── plugin-interfaces.md
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/
├── plugins/
│   ├── __init__.py              # EXISTING (empty → re-export PluginManager)
│   ├── plugin_manager.py        # NEW: Discovery, loading, registration
│   ├── stack_plugin_base.py     # NEW: StackPlugin ABC (arch-parameterized)
│   ├── agents/
│   │   ├── __init__.py          # EXISTING
│   │   ├── base.py              # EXISTING: AgentPlugin ABC (unchanged)
│   │   ├── claude_plugin.py     # NEW: Claude Code → CLAUDE.md
│   │   ├── copilot_plugin.py    # NEW: Copilot → .github/copilot-instructions.md + .github/prompts/
│   │   ├── cursor_plugin.py     # NEW: Cursor → .cursorrules
│   │   ├── gemini_plugin.py     # NEW: Gemini → .gemini/
│   │   ├── windsurf_plugin.py   # NEW: Windsurf → .windsurfrules
│   │   ├── codex_plugin.py      # NEW: Codex CLI → codex config
│   │   ├── kiro_plugin.py       # NEW: Kiro CLI config
│   │   ├── amp_plugin.py        # NEW: Amp config
│   │   ├── auggie_plugin.py     # NEW: Auggie CLI config
│   │   ├── codebuddy_plugin.py  # NEW: CodeBuddy CLI config
│   │   ├── bob_plugin.py        # NEW: IBM Bob config
│   │   ├── jules_plugin.py      # NEW: Jules config
│   │   ├── kilocode_plugin.py   # NEW: Kilo Code config
│   │   ├── opencode_plugin.py   # NEW: opencode config
│   │   ├── pi_plugin.py         # NEW: Pi Coding Agent config
│   │   ├── qoder_plugin.py      # NEW: Qoder CLI config
│   │   ├── qwen_plugin.py       # NEW: Qwen Code config
│   │   ├── roocode_plugin.py    # NEW: Roo Code config
│   │   ├── shai_plugin.py       # NEW: SHAI (OVHcloud) config
│   │   ├── tabnine_plugin.py    # NEW: Tabnine CLI config
│   │   ├── mistral_plugin.py    # NEW: Mistral Vibe config
│   │   ├── kimi_plugin.py       # NEW: Kimi Code config
│   │   ├── antigravity_plugin.py # NEW: Antigravity (agy) config
│   │   ├── trae_plugin.py       # NEW: Trae config
│   │   └── generic_plugin.py    # NEW: Generic fallback (user-specified dir)
│   └── stacks/
│       ├── __init__.py          # NEW
│       ├── dotnet_plugin.py     # NEW: .NET rules (micro + mono + modular)
│       ├── nodejs_plugin.py     # NEW: Node.js rules (micro + mono + modular)
│       └── python_plugin.py     # NEW: Python rules (micro + mono + modular)
├── core/
│   ├── config.py                # MODIFIED: add ArchitectureType enum, plugin constants
│   ├── prompt_manager.py        # MODIFIED: accept extra_rules from stack plugins
│   └── prompt_context.py        # UNCHANGED (reads merged governance files)
├── cli/
│   └── init_cmd.py              # MODIFIED: integrate PluginManager into init flow
└── templates/
    └── base/
        └── governance/
            ├── backend.dotnet.md.j2   # MODIFIED: add architecture-conditional rule blocks
            ├── backend.python.md.j2   # MODIFIED: add architecture-conditional rule blocks
            ├── backend.nodejs.md.j2   # MODIFIED: add architecture-conditional rule blocks
            └── _base_governance.md.j2 # UNCHANGED

tests/
├── unit/
│   ├── test_stack_plugin_base.py     # NEW: StackPlugin ABC contract tests
│   ├── test_plugin_manager.py        # NEW: Discovery, registration, conflict resolution
│   ├── test_dotnet_plugin.py         # NEW: .NET rule generation (3 arch types)
│   ├── test_nodejs_plugin.py         # NEW: Node.js rule generation (3 arch types)
│   ├── test_python_plugin.py         # NEW: Python rule generation (3 arch types)
│   ├── test_agent_plugins.py         # NEW: Agent config file generation (all 25+)
│   └── test_generic_plugin.py        # NEW: Generic fallback behavior
├── integration/
│   ├── test_init_with_plugins.py     # NEW: CLI init with --stack + --agent + --arch
│   └── test_custom_plugin_loading.py # NEW: Custom plugin from .specforge/plugins/
└── snapshots/
    ├── test_dotnet_microservice_rules/ # NEW: snapshot for .NET+microservice
    ├── test_dotnet_monolith_rules/     # NEW: snapshot for .NET+monolith
    ├── test_python_microservice_rules/ # NEW: snapshot for Python+microservice
    └── ...                             # 9 total stack×arch snapshots
```

**Structure Decision**: Extends existing single-project structure. All new plugin modules go in `src/specforge/plugins/` (agents/ and stacks/ subdirectories). Domain logic for plugin discovery goes in `plugins/plugin_manager.py`. No new top-level directories.

## Complexity Tracking

> No constitution violations — table not needed.
