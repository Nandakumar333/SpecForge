# Implementation Plan: Interactive AI Model Selection & Commands Directory

**Branch**: `014-interactive-model-selection` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-interactive-model-selection/spec.md`

## Summary

Add interactive AI agent selection during `specforge init` and automatic creation of agent-native commands directories with pipeline-stage prompt files. When `--agent` is not provided in an interactive terminal, Rich's `Prompt.ask()` presents all 24+ registered plugins (sorted alphabetically, "generic" last). The selected agent determines a `commands_dir` property on the plugin (e.g., `.claude/commands/`, `.github/prompts/` for Copilot) where `specforge.{stage}.md` files are rendered in the agent's native format (Markdown or TOML) with agent-specific argument placeholders. Config.json is extended with `agent` and `commands_dir` fields. The term "agnostic" is unified to "generic" across the codebase.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (interactive prompts + terminal output), Jinja2 3.x (template rendering)
**Storage**: File system — `.specforge/config.json`, agent-native commands directories
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)
**Project Type**: CLI tool
**Performance Goals**: N/A — interactive CLI, sub-second operations
**Constraints**: No new dependencies beyond what's already in `pyproject.toml`; Rich `Prompt.ask()` already used in 2 modules
**Scale/Scope**: 25 agent plugins, 8 pipeline stages, ~15 files modified + ~10 new templates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-Design Status |
|-----------|------|-------------------|
| I. Spec-First | spec.md complete before implementation | PASS — spec exists with 25 FRs, 10 clarifications |
| II. Architecture | Core logic has zero external deps; Jinja2 templates for all file generation; plugin system for agents | PASS — new `commands_dir`/`command_format`/`args_placeholder` properties on existing plugin base; prompt files rendered via Jinja2 templates |
| III. Code Quality | Functions ≤30 lines; classes ≤200 lines; strict types; no magic strings; Result returns; constructor injection | PASS — all new code follows existing patterns; constants in `config.py` |
| IV. Testing | TDD: test files before implementation; unit + integration + snapshot | PASS — test plan: unit tests for command registrar, integration tests for init with CliRunner, snapshot tests for rendered prompt files |
| V. Commit Strategy | Conventional Commits; one commit per task | PASS |
| VI. File Structure | Modules in correct architectural layer; no cross-layer imports | PASS — `core/command_registrar.py` (domain logic), `cli/init_cmd.py` (CLI layer), `plugins/agents/*.py` (plugin layer) |
| VII. Governance | Constitution supersedes all other docs | PASS |

**All gates PASS. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/014-interactive-model-selection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   └── init_cmd.py              # Modified — add interactive prompt + commands registration
├── core/
│   ├── config.py                # Modified — "agnostic" → "generic", new command constants
│   ├── agent_detector.py        # Modified — fallback "agnostic" → "generic"
│   ├── project.py               # Modified — "agnostic" → "generic" defaults
│   ├── command_registrar.py     # NEW — renders + writes command files per agent
│   ├── prompt_manager.py        # Modified — config.json writes agent + commands_dir
│   └── prompt_loader.py         # Modified — reads new config.json fields
├── plugins/
│   └── agents/
│       ├── base.py              # Modified — add abstract commands_dir, command_format, args_placeholder
│       ├── single_file_base.py  # Modified — add default property implementations
│       ├── directory_base.py    # Modified — add default property implementations
│       ├── generic_plugin.py    # Modified — custom commands_dir handling
│       ├── claude_plugin.py     # Modified — commands_dir = ".claude/commands"
│       ├── copilot_plugin.py    # Modified — commands_dir = ".github/prompts"
│       ├── gemini_plugin.py     # Modified — commands_dir = ".gemini/commands", format = "toml"
│       └── [20 other plugins]   # Modified — add commands_dir defaults
└── templates/
    └── base/
        └── commands/            # NEW directory — 8 Jinja2 templates
            ├── specforge.decompose.md.j2
            ├── specforge.specify.md.j2
            ├── specforge.research.md.j2
            ├── specforge.plan.md.j2
            ├── specforge.tasks.md.j2
            ├── specforge.implement.md.j2
            ├── specforge.status.md.j2
            ├── specforge.check.md.j2
            └── copilot-prompt-stub.md.j2

tests/
├── unit/
│   ├── test_command_registrar.py    # NEW — unit tests for command rendering + writing
│   └── test_agent_plugins_props.py  # NEW — verify all plugins expose new properties
├── integration/
│   └── test_init_interactive.py     # NEW — CliRunner tests for interactive init
└── snapshots/
    └── test_command_templates/      # NEW — snapshot tests for rendered command files
```

**Structure Decision**: Existing single-project layout. New domain logic in `core/command_registrar.py`, new templates in `templates/base/commands/`, modifications to existing plugin base classes and init CLI.

## Complexity Tracking

> No constitution violations. All changes fit within existing architectural layers.

## Design Decisions

### D-01: Concrete default properties on AgentPlugin base class

**Decision**: New `commands_dir`, `command_format`, `command_extension`, and `args_placeholder` are concrete properties with defaults on the `AgentPlugin` ABC — NOT abstract methods.

**Rationale**: Making them abstract would require all 25 existing plugin subclasses to implement stubs even when the default is correct. Concrete defaults with selective overrides minimizes code churn while preserving extensibility.

**Overrides needed**: Only 6 plugins need overrides: Claude (dir), Copilot (dir + extension), Gemini (dir + format + extension), Cursor (dir), Windsurf (dir), Codex (dir). All others use defaults.

### D-02: CommandRegistrar as standalone core service

**Decision**: Create `core/command_registrar.py` as a new domain service separate from `scaffold_builder.py`.

**Rationale**: The scaffold builder generates the `.specforge/` structure (constitution, governance, templates). Command registration is a distinct concern — it writes to agent-native directories *outside* `.specforge/`. Separating them follows single-responsibility and keeps the scaffold builder focused. The init command orchestrates both.

### D-03: Universal placeholder token in templates

**Decision**: Jinja2 command templates use `{{ arguments }}` as a context variable. The `CommandRegistrar` passes the agent's `args_placeholder` value as the `arguments` context variable during rendering.

**Rationale**: Avoids post-rendering string replacement. The Jinja2 template system already handles variable substitution, so using `{{ arguments }}` is the natural approach. No need for `convert_placeholder()` — the template renders directly with the correct value.

### D-04: "agnostic" → "generic" scope limitation

**Decision**: Only agent-context occurrences of "agnostic" change to "generic". Stack-context "agnostic" (e.g., `StackName`, `STACK_HINTS["agnostic"]`, `AGNOSTIC_GOVERNANCE_DOMAINS`) is preserved.

**Rationale**: "Language-agnostic" is semantically correct for stacks. "Generic" is the right term for "no specific agent". These are independent naming domains — changing both would cause confusion and unnecessary test churn in stack-related code.

### D-05: Interactive prompt only when no --agent AND TTY

**Decision**: The interactive agent prompt fires ONLY when: (1) `--agent` is not provided, AND (2) `sys.stdin.isatty()` returns `True`. All other paths use existing behavior unchanged.

**Rationale**: This preserves 100% backward compatibility. CI pipelines, piped input, and explicit `--agent` flags work exactly as before. The prompt is purely additive for interactive terminal users.

### D-06: Single-agent registration at init time

**Decision**: `init` registers commands for only the selected agent. Multi-agent registration is deferred to a future `specforge register` command.

**Rationale**: The interactive prompt asks the user to pick ONE agent. Writing to multiple agent directories would be confusing and contradicts the explicit selection UX. Users who need multiple agents can re-init with `--force` or use the future `register` command.

### D-07: Copilot dual-file strategy

**Decision**: For Copilot, command files go to `.github/prompts/` as `specforge.{stage}.prompt.md` with full prompt content. No separate companion stub needed — the `.prompt.md` IS the command file for Copilot.

**Rationale**: Copilot discovers slash commands via `.prompt.md` files in `.github/prompts/`. Unlike Spec-Kit which writes commands to a separate `.github/agents/` directory and generates companion stubs, SpecForge writes directly to the discovery location. This simplifies the Copilot path to a single file per command.

### D-08: Template directory structure

**Decision**: New templates go in `src/specforge/templates/base/commands/` as `specforge.{stage}.md.j2`. One Jinja2 template per pipeline stage, shared across all agents (format differences handled by the registrar, not the template).

**Rationale**: Templates contain the prompt content which is agent-independent. The registrar handles format wrapping (Markdown frontmatter vs TOML block) and placeholder injection. This avoids duplicating 8 templates per format.

## Implementation Phases

### Phase A: Foundation (no user-visible change)

1. **Rename "agnostic" → "generic"** in agent-related code (`config.py`, `agent_detector.py`, `project.py`, `prompt_manager.py`)
2. **Add properties to AgentPlugin base class** — `commands_dir`, `command_format`, `command_extension`, `args_placeholder` with concrete defaults
3. **Update plugin subclasses** — override properties for claude, copilot, gemini, cursor, windsurf, codex, kiro, roocode, amp, antigravity, bob, kilocode, trae, generic
4. **Add constants to config.py** — `PIPELINE_STAGES`, `COMMAND_PREFIX`
5. **Extend config.json write** — modify `_write_config_json()` to accept `agent` and `commands_dir`
6. **Unit tests** for all new plugin properties

### Phase B: Command Registrar (core domain logic)

1. **Create `core/command_registrar.py`** — `CommandRegistrar` class with `register_commands()`, `build_command_files()`, `_render_markdown()`, `_render_toml()`
2. **Create 8 Jinja2 command templates** in `templates/base/commands/`
3. **Unit tests** for command rendering (Markdown + TOML formats)
4. **Snapshot tests** for rendered command file output

### Phase C: Interactive Prompt + Init Integration

1. **Modify `init_cmd.py`** — add TTY detection, Rich `Prompt.ask()` for agent selection, generic commands-dir prompt
2. **Wire `CommandRegistrar.register_commands()`** into init flow after scaffold
3. **Update dry-run preview** to include command files
4. **Update summary output** to show commands directory info
5. **Integration tests** with `CliRunner` for interactive init scenarios

### Phase D: Polish & Validation

1. **Extend config.json reader** in `prompt_loader.py` — read `agent` and `commands_dir` with fallbacks
2. **Update `ScaffoldResult`** with `commands_written` field
3. **End-to-end integration tests** — full init → config.json → commands dir verification
4. **Snapshot update** for any changed template outputs

## Post-Design Constitution Re-Check

| Principle | Post-Design Status |
|-----------|-------------------|
| I. Spec-First | PASS — spec, plan, data-model, contracts all complete before implementation |
| II. Architecture | PASS — `CommandRegistrar` in `core/`, templates in `templates/`, plugins in `plugins/`; no cross-layer imports |
| III. Code Quality | PASS — `CommandRegistrar` ~60 lines, `register_commands()` ≤30 lines; all functions typed; constants in `config.py`; `Result` returns |
| IV. Testing | PASS — unit tests in Phase A+B, integration tests in Phase C, snapshots in Phase B+D |
| V. Commit Strategy | PASS — each phase sub-step maps to a conventional commit |
| VI. File Structure | PASS — all new files in correct architectural layers |
| VII. Governance | PASS — no conflicts with constitution |

**All gates PASS after Phase 1 design.**
