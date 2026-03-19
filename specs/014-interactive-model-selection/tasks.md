# Tasks: Interactive AI Model Selection & Commands Directory

**Input**: Design documents from `/specs/014-interactive-model-selection/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/
**Tests**: TDD — test files written BEFORE implementation in every phase
**Commit Strategy**: Conventional Commits — one commit per task

**Organization**: Tasks follow user's phasing preference: Foundation → CommandRegistrar → Interactive Init → Config Loader → Polish. Within each phase, tests are written first (TDD), then implementation.

**Note on dependencies**: The spec says to use Rich `Prompt.ask()` (already a project dependency per research R1). No new dependency (like `questionary`) is needed — Rich handles interactive prompts natively.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on in-progress tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in every task description

---

## Phase 1: Setup (Constants & Terminology Migration)

**Purpose**: Rename "agnostic" → "generic" in agent context, add new constants. No user-visible change. Per plan §D-04, only agent-related "agnostic" changes — stack "agnostic" is preserved.

- [X] T001 Write unit tests for "agnostic" → "generic" rename in tests/unit/test_config.py — add tests asserting `"generic"` is in `AgentName` literal, `"agnostic"` is NOT in `AgentName`, and `"agnostic"` IS still in `StackName`; assert `PIPELINE_STAGES` contains exactly 8 stages and `COMMAND_PREFIX == "specforge"`
- [X] T002 Write unit tests for updated agent_detector fallback in tests/unit/test_agent_detector.py — add test asserting `detect_agent()` with no agents in PATH returns `DetectionResult(agent="generic", source="generic")` instead of `"agnostic"`
- [X] T003 [P] Write unit tests for updated project.py defaults in tests/unit/test_project_config.py — add test asserting `ProjectConfig` default agent is `"generic"`, `ScaffoldResult` default `agent_source` is `"generic"`, `DetectionResult` source Literal includes `"interactive"` and `"generic"`
- [X] T004 Rename `"agnostic"` → `"generic"` in `AgentName` literal and add `PIPELINE_STAGES` + `COMMAND_PREFIX` constants in src/specforge/core/config.py — change `AgentName` to include `"generic"` instead of `"agnostic"` (keep `StackName` "agnostic" unchanged); add `PIPELINE_STAGES: list[str] = ["decompose", "specify", "research", "plan", "tasks", "implement", "status", "check"]` and `COMMAND_PREFIX: str = "specforge"`
- [X] T005 Rename `"agnostic"` → `"generic"` fallback in src/specforge/core/agent_detector.py — change final return from `DetectionResult(agent="agnostic", source="agnostic")` to `DetectionResult(agent="generic", source="generic")`
- [X] T006 [P] Rename `"agnostic"` → `"generic"` defaults in src/specforge/core/project.py — update `ProjectConfig.agent` default to `"generic"`, update `ScaffoldResult.agent_source` Literal to include `"interactive"` and `"generic"` (remove `"agnostic"`), update `DetectionResult.source` Literal to include `"interactive"` and `"generic"` (remove `"agnostic"`)
- [X] T007 [P] Rename `"agnostic"` → `"generic"` in `GenericPlugin.agent_name()` return value in src/specforge/plugins/agents/generic_plugin.py — verify `agent_name()` returns `"generic"` (already does; confirm and add `commands_dir` init default change from `.specforge/agent` to `commands`)
- [X] T008 Update existing test snapshots and assertions that reference `"agnostic"` in agent context — run `uv run pytest` to identify failures from the rename, then update these specific test files: tests/unit/test_agent_detector.py, tests/unit/test_project_config.py, tests/unit/test_config.py, tests/unit/test_generic_plugin.py, tests/integration/test_init_cmd.py, tests/integration/test_init_agent_detection.py, tests/integration/test_init_here_cmd.py, and any snapshot files under tests/snapshots/ that contain agent-context "agnostic" (not stack-related tests)

**Checkpoint**: All "agnostic" → "generic" agent-context references are migrated. `uv run pytest` passes. Stack "agnostic" is untouched.

> **Commit**: `refactor: rename agent "agnostic" to "generic" across codebase (FR-019)`

---

## Phase 2: Foundational (Plugin Properties — Blocking)

**Purpose**: Add `commands_dir`, `command_format`, `command_extension`, `args_placeholder` concrete properties to AgentPlugin base class and override in subclasses per contract §agent-plugin-interface. MUST complete before any CommandRegistrar or init integration work.

**⚠️ CRITICAL**: No US1/US2/US3/US4/US5 work can begin until this phase is complete.

### Tests (TDD — write first, must fail)

- [X] T009 Write unit tests for new AgentPlugin base properties in tests/unit/test_agent_plugin_bases.py — test that `AgentPlugin` subclass instances expose `commands_dir`, `command_format`, `command_extension`, `args_placeholder` properties; test `SingleFileAgentPlugin` defaults (`.specforge/commands`, `"markdown"`, `".md"`, `"$ARGUMENTS"`); test `DirectoryAgentPlugin` defaults (derive from `_dir_path + "/commands"`, `"markdown"`, `".md"`, `"$ARGUMENTS"`)
- [X] T010 [P] Write unit tests for agent-specific property overrides in tests/unit/test_agent_plugins.py — test `ClaudePlugin().commands_dir == ".claude/commands"`, `CopilotPlugin().commands_dir == ".github/prompts"`, `CopilotPlugin().command_extension == ".prompt.md"`, `GeminiPlugin().commands_dir == ".gemini/commands"`, `GeminiPlugin().command_format == "toml"`, `GeminiPlugin().command_extension == ".toml"`, `CursorPlugin().commands_dir == ".cursor/commands"`, `WindsurfPlugin().commands_dir == ".windsurf/commands"`, `GenericPlugin().commands_dir == "commands"`, `GenericPlugin("custom-dir").commands_dir == "custom-dir"`
- [X] T011 [P] Write parametrized test for ALL 25 plugin properties in tests/unit/test_agent_plugins.py — parametrize over every plugin class (amp, antigravity, auggie, bob, claude, codebuddy, codex, copilot, cursor, gemini, generic, jules, kilocode, kimi, kiro, mistral, opencode, pi, qoder, qwen, roocode, shai, tabnine, trae, windsurf): assert each has valid `commands_dir` (non-empty string), `command_format` in `("markdown", "toml")`, `command_extension` starts with `.`, `args_placeholder` is non-empty string

### Implementation

- [X] T012 Add concrete default properties to `AgentPlugin` base class in src/specforge/plugins/agents/base.py — add `commands_dir` property returning `".specforge/commands"`, `command_format` returning `"markdown"`, `command_extension` returning `".md"`, `args_placeholder` returning `"$ARGUMENTS"` as concrete (non-abstract) properties per plan §D-01
- [X] T013 Add default property overrides to `SingleFileAgentPlugin` in src/specforge/plugins/agents/single_file_base.py — override `commands_dir` to return `".specforge/commands"` (single-file agents have no directory path to derive from)
- [X] T014 [P] Add default property overrides to `DirectoryAgentPlugin` in src/specforge/plugins/agents/directory_base.py — override `commands_dir` to return `f"{self._dir_path}/commands"` (derives from existing `_dir_path`)
- [X] T015 [P] Override `commands_dir` in `ClaudePlugin` in src/specforge/plugins/agents/claude_plugin.py — add `@property def commands_dir(self) -> str: return ".claude/commands"`
- [X] T016 [P] Override `commands_dir` and `command_extension` in `CopilotPlugin` in src/specforge/plugins/agents/copilot_plugin.py — add `commands_dir` returning `".github/prompts"` and `command_extension` returning `".prompt.md"`
- [X] T017 [P] Override `commands_dir`, `command_format`, `command_extension` in `GeminiPlugin` in src/specforge/plugins/agents/gemini_plugin.py — add `commands_dir` returning `".gemini/commands"`, `command_format` returning `"toml"`, `command_extension` returning `".toml"`
- [X] T018 [P] Override `commands_dir` in `CursorPlugin` in src/specforge/plugins/agents/cursor_plugin.py — add `@property def commands_dir(self) -> str: return ".cursor/commands"`
- [X] T019 [P] Override `commands_dir` in `WindsurfPlugin` in src/specforge/plugins/agents/windsurf_plugin.py — add `@property def commands_dir(self) -> str: return ".windsurf/commands"`
- [X] T020 [P] Override `commands_dir` in `CodexPlugin` in src/specforge/plugins/agents/codex_plugin.py — add `@property def commands_dir(self) -> str: return ".codex/commands"`
- [X] T021 [P] Override `commands_dir` in directory-based plugins with custom paths — `KiroPlugin` (`.kiro/commands`) in src/specforge/plugins/agents/kiro_plugin.py, `RoocodePlugin` (`.roo/commands`) in src/specforge/plugins/agents/roocode_plugin.py, `AmpPlugin` (`.amp/commands`) in src/specforge/plugins/agents/amp_plugin.py, `AntigravityPlugin` (`.agy/commands`) in src/specforge/plugins/agents/antigravity_plugin.py, `BobPlugin` (`.bob/commands`) in src/specforge/plugins/agents/bob_plugin.py, `KilocodePlugin` (`.kilocode/commands`) in src/specforge/plugins/agents/kilocode_plugin.py, `TraePlugin` (`.trae/commands`) in src/specforge/plugins/agents/trae_plugin.py
- [X] T022 Update `GenericPlugin.__init__` to accept custom `commands_dir` defaulting to `"commands"` in src/specforge/plugins/agents/generic_plugin.py — change `__init__(self, commands_dir: str = "commands")`, add `@property def commands_dir(self) -> str: return self._commands_dir`
- [X] T023 Run full test suite to validate all plugin properties pass — `uv run pytest tests/unit/test_agent_plugin_bases.py tests/unit/test_agent_plugins.py -v`

**Checkpoint**: All 25 plugins expose `commands_dir`, `command_format`, `command_extension`, `args_placeholder`. Foundation ready for user story implementation.

> **Commit**: `feat: add commands_dir/command_format/args_placeholder properties to agent plugins (FR-020, FR-021, FR-023)`

---

## Phase 3: User Story 2 — Automatic Commands Directory Creation (Priority: P1) 🎯 MVP

**Goal**: Create the `CommandRegistrar` core service that renders Jinja2 templates into agent-native command files (Markdown or TOML) and writes them to the agent's `commands_dir`. Per user request: "Create commands/ generator" — this is the core domain logic.

**Independent Test**: Can be tested by instantiating `CommandRegistrar`, passing a mock `AgentPlugin` and `tmp_path`, and verifying 8 files are written with correct content.

### Tests (TDD — write first, must fail)

- [X] T024 Write unit tests for `CommandFile` dataclass in tests/unit/test_command_registrar.py — test `CommandFile(stage="decompose", filename="specforge.decompose.md", relative_path=Path(...), content="...")` is frozen, all fields accessible
- [X] T025 Write unit tests for `CommandRegistrar.build_command_files()` in tests/unit/test_command_registrar.py — test with mock Claude plugin: returns 8 `CommandFile` objects, filenames match `specforge.{stage}.md`, relative paths start with `.claude/commands/`, content is non-empty; test with mock Gemini plugin: returns 8 files, filenames match `specforge.{stage}.toml`, content wrapped in TOML format with `prompt = """..."""`; test with mock Copilot plugin: returns 8 files with `.prompt.md` extension
- [X] T026 [P] Write unit tests for `CommandRegistrar.register_commands()` in tests/unit/test_command_registrar.py — test with `tmp_path`: all 8 files written to disk, returns `Ok(list[Path])` with 8 paths; test with `force=True` and pre-existing file: existing file preserved (not overwritten), only missing files created; test with permission error: returns `Err(...)` message
- [X] T027 [P] Write unit tests for TOML format rendering in tests/unit/test_command_registrar.py — test `_render_toml()` output contains `description = "..."`, `prompt = """`, and ends with `"""`; verify no Markdown frontmatter in TOML output
- [X] T028 [P] Write snapshot tests for rendered command files in tests/snapshots/ — snapshot test all 8 stages rendered as Markdown (Claude context), snapshot test `specforge.decompose` rendered as TOML (Gemini context), snapshot test Copilot `.prompt.md` output

### Implementation

- [X] T029 [US2] Create `CommandFile` dataclass and `CommandRegistrar` class skeleton in src/specforge/core/command_registrar.py — implement per contract §command-registrar: frozen `CommandFile(stage, filename, relative_path, content)` dataclass; `CommandRegistrar.__init__()` creates Jinja2 `Environment` with `PackageLoader("specforge", "templates/base/commands")`
- [X] T030 [US2] Implement `CommandRegistrar.build_command_files()` in src/specforge/core/command_registrar.py — iterate `PIPELINE_STAGES`, render each template `specforge.{stage}.md.j2`, apply agent `command_format`/`command_extension`/`args_placeholder` via context variable `arguments`, wrap TOML if `command_format == "toml"`, return `list[CommandFile]`
- [X] T031 [US2] Implement `CommandRegistrar.register_commands()` in src/specforge/core/command_registrar.py — call `build_command_files()`, write each to `target_dir / commands_dir / filename`, create parent dirs, skip existing files when `force=True`, return `Result[list[Path], str]`
- [X] T032 [US2] Implement `CommandRegistrar._render_toml()` in src/specforge/core/command_registrar.py — render Markdown template first, then wrap in TOML structure: `description = "..."` + `prompt = """..."""` per research §R4
- [X] T033 [P] [US2] Create 8 Jinja2 command templates in src/specforge/templates/base/commands/ — create `specforge.decompose.md.j2`, `specforge.specify.md.j2`, `specforge.research.md.j2`, `specforge.plan.md.j2`, `specforge.tasks.md.j2`, `specforge.implement.md.j2`, `specforge.status.md.j2`, `specforge.check.md.j2`; each uses `{{ arguments }}` token, includes `{{ project_name }}`, `{{ stack }}`, pipeline stage description; add Markdown frontmatter with `description` field

**Checkpoint**: `CommandRegistrar` renders all 8 templates in Markdown and TOML, writes to disk, handles `--force`. All unit + snapshot tests pass.

> **Commit**: `feat: add CommandRegistrar core service with Jinja2 command templates (FR-006, FR-007, FR-016)`

---

## Phase 4: User Story 1 — Interactive Agent Selection on Init (Priority: P1)

**Goal**: Add interactive Rich `Prompt.ask()` agent selection to `init_cmd.py` when `--agent` is not provided and TTY is detected. Wire `CommandRegistrar` into the init flow. Per user request: "Update init_command with interactive logic".

**Independent Test**: Can be tested via `CliRunner` with input simulation — verify prompt appears, selection is recorded in `config.json`, command files are created.

### Tests (TDD — write first, must fail)

- [X] T034 Write integration tests for interactive init in tests/integration/test_init_interactive.py — test with CliRunner + simulated input `"claude\n"`: verify `.specforge/config.json` contains `"agent": "claude"`, verify `.claude/commands/` directory exists with 8 `.md` files; test with `"generic\n\n"` (accept default dir): verify `commands/` at project root with 8 files, config has `"agent": "generic"` and `"commands_dir": "commands"`
- [X] T035 [P] Write integration test for `--agent` flag bypass in tests/integration/test_init_interactive.py — test with `--agent claude` (no stdin): verify no prompt shown, `.specforge/config.json` has `"agent": "claude"`, command files created at `.claude/commands/`
- [X] T036 [P] Write integration test for non-TTY fallback in tests/integration/test_init_interactive.py — test with piped input (CliRunner default): verify auto-detect behavior, no Rich prompt exception, `config.json` has agent field
- [X] T037 [P] Write integration test for `--dry-run` with interactive in tests/integration/test_init_interactive.py — test `--dry-run` with CliRunner + input: verify no command files written to disk, output contains command file paths in preview tree
- [X] T038 [P] Write integration test for `--force` preserving existing command files in tests/integration/test_init_interactive.py — pre-create a command file with custom content, run init with `--force --agent claude`, verify custom content preserved, missing files added

### Implementation

- [X] T039 [US1] Add TTY detection and Rich `Prompt.ask()` agent selection to src/specforge/cli/init_cmd.py — import `sys` and `rich.prompt.Prompt`; after argument parsing, if `agent is None` and `sys.stdin.isatty()`: get sorted agent list from `PluginManager().list_agent_plugins()`, append `"generic"` last, call `Prompt.ask("Which AI agent do you want to use?", choices=[...], default="generic")`; set `agent` to result; wrap in try/except `KeyboardInterrupt` for clean abort (FR-015)
- [X] T040 [US1] Add "generic" custom commands-dir prompt to src/specforge/cli/init_cmd.py — if selected agent is `"generic"` and `sys.stdin.isatty()`: call `Prompt.ask("Commands directory", default="commands")`, validate the path (relative, no `..`), re-prompt on invalid input per FR-009/FR-010
- [X] T041 [US1] [US2] Wire `CommandRegistrar.register_commands()` into init flow in src/specforge/cli/init_cmd.py — after `generate_governance_files()` and agent config generation: instantiate `CommandRegistrar()`, get plugin via `PluginManager().get_agent_plugin(agent)`, call `registrar.register_commands(plugin, target_dir, context, force=force)` unless `dry_run`; for dry-run, call `build_command_files()` and add to preview tree
- [X] T042 [US1] Update init summary output to show agent source and commands directory in src/specforge/cli/init_cmd.py — after scaffold completes, print `"✓ Agent: {agent} ({source})"` and `"✓ Commands directory: {commands_dir}"` using Rich console

**Checkpoint**: `specforge init MyApp --here` shows interactive prompt, creates command files, records agent in config.json. `--agent` flag skips prompt. `--dry-run` previews. `--force` preserves existing files.

> **Commit**: `feat: add interactive agent selection prompt to init command (FR-001, FR-002, FR-003, FR-004, FR-005)`
> **Commit**: `feat: wire CommandRegistrar into init flow with dry-run and force support (FR-013, FR-014, FR-017)`

---

## Phase 5: User Story 4 — Config.json Persists Agent and Commands Dir (Priority: P2)

**Goal**: Extend config.json write/read to include `agent` and `commands_dir` fields. Per user request: "Update config loader".

**Independent Test**: Run init with any agent, read config.json, verify `agent` and `commands_dir` keys present.

### Tests (TDD — write first, must fail)

- [X] T043 Write unit tests for extended `_write_config_json()` in tests/unit/test_prompt_manager.py — test that calling `_write_config_json(root, "MyApp", "python", agent="claude", commands_dir=".claude/commands")` writes JSON with all 6 fields: `project_name`, `stack`, `agent`, `commands_dir`, `version`, `created_at`; test defaults: omitting `agent`/`commands_dir` params writes `"generic"` and `"commands"` respectively
- [X] T044 [P] Write unit tests for extended config.json reader in tests/unit/test_prompt_loader.py — test `_read_project_meta()` returns `ProjectMeta` with `agent` and `commands_dir` fields when present; test fallback: missing `agent` field returns `"generic"`, missing `commands_dir` returns `"commands"`; test backward compatibility: existing config.json without new fields still loads successfully

### Implementation

- [X] T045 [US4] Extend `_write_config_json()` and `PromptFileManager._write_config()` in src/specforge/core/prompt_manager.py — add `agent: str = "generic"` and `commands_dir: str = "commands"` parameters; include both in the config dict written to JSON per contract §config-json-schema
- [X] T046 [US4] Extend `PromptLoader._read_project_meta()` in src/specforge/core/prompt_loader.py — add `agent` and `commands_dir` to `ProjectMeta` dataclass (with defaults `"generic"` and `"commands"`); read from config dict with `.get()` fallbacks for backward compatibility; add legacy migration: if `agent == "agnostic"`, normalize to `"generic"` (handles pre-014 config.json files per FR-019)
- [X] T047 [US4] Update `scaffold_builder.generate_governance_files()` call chain to pass `agent` and `commands_dir` in src/specforge/core/scaffold_builder.py — ensure `_write_config_json()` receives the agent name and commands_dir from `ProjectConfig`
- [X] T047a [US4] Extend `_build_context()` in src/specforge/core/scaffold_builder.py — add `arguments` (set to agent's `args_placeholder` value) and `architecture` (from `config.architecture`) to the template context dict, so command templates can access these variables during rendering (per research §R8)

**Checkpoint**: config.json contains `agent` + `commands_dir` after every init. Existing config.json files load with fallback defaults.

> **Commit**: `feat: extend config.json with agent and commands_dir fields (FR-011, FR-012)`

---

## Phase 6: User Story 3 — Generic Agent Custom Commands Directory (Priority: P2)

**Goal**: When "generic" is selected, prompt for custom commands directory. Already partially implemented in T040; this phase adds path validation and edge case handling.

**Independent Test**: Select "generic" during init, provide custom path, verify directory created at correct location.

- [X] T048 [US3] Write integration test for custom commands directory path in tests/integration/test_init_interactive.py — test with input `"generic\nmy-prompts\n"`: verify `my-prompts/` created with 8 files, config.json has `"commands_dir": "my-prompts"`; test with input `"generic\n/absolute/path\ncommands\n"`: verify re-prompt on invalid path, then accepts valid default; test with input `"generic\n../escape\ncommands\n"`: verify re-prompt on traversal attempt
- [X] T049 [US3] Implement path validation helper function in src/specforge/cli/init_cmd.py — create `_validate_commands_dir(path: str) -> Result[str, str]` that rejects absolute paths (`Path(path).is_absolute()`), paths containing `..`, and empty strings; returns normalized relative path on success

**Checkpoint**: Generic path validation works. All edge cases (absolute, traversal, empty) handled.

> **Commit**: `feat: add commands-dir path validation for generic agent (FR-009, FR-010)`

---

## Phase 7: User Story 5 — Spec-Kit Migration Compatibility (Priority: P3)

**Goal**: Verify generated command files match Spec-Kit naming convention so slash commands work in AI tools.

**Independent Test**: Run init with Copilot, verify files named `specforge.{stage}.prompt.md` exist in `.github/prompts/`.

- [X] T050 [US5] Write integration test for Spec-Kit naming compatibility in tests/integration/test_init_interactive.py — test Copilot init produces `specforge.decompose.prompt.md` through `specforge.check.prompt.md` in `.github/prompts/`; test Claude init produces `specforge.decompose.md` through `specforge.check.md` in `.claude/commands/`; test Gemini init produces `specforge.decompose.toml` through `specforge.check.toml` in `.gemini/commands/`
- [X] T051 [US5] Write integration test for Copilot companion stubs in tests/integration/test_init_interactive.py — verify Copilot `.prompt.md` files contain YAML frontmatter per D-07 (Copilot writes full content directly to `.github/prompts/`, no separate stub needed); verify non-Copilot agents do NOT produce `.prompt.md` stubs

**Checkpoint**: All 3 major agent formats verified: Claude (Markdown in `.claude/commands/`), Copilot (`.prompt.md` in `.github/prompts/`), Gemini (TOML in `.gemini/commands/`).

> **Commit**: `feat: ensure Spec-Kit compatible command file naming (FR-008, FR-022)`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: ScaffoldResult update, snapshot updates, existing test fixes, final validation

- [X] T052 [P] Update `ScaffoldResult` with `commands_written` field in src/specforge/core/project.py — add `commands_written: list[Path] = field(default_factory=list)` to `ScaffoldResult` dataclass; populate from `CommandRegistrar.register_commands()` return value in init_cmd.py
- [X] T053 [P] Update dry-run preview tree to include command files in src/specforge/cli/init_cmd.py — when `dry_run=True`, call `CommandRegistrar.build_command_files()` and add each `CommandFile.relative_path` to the Rich Tree preview
- [X] T054 [P] Update existing snapshot tests affected by "agnostic" → "generic" rename — run `uv run pytest --snapshot-update` for changed template outputs; verify only agent-context snapshots changed, not stack-context snapshots
- [X] T055 [P] [US2] [FR-018] Verify generic agent receives full governance scaffold — write integration test in tests/integration/test_init_interactive.py confirming that `specforge init MyApp --here` with agent `"generic"` produces both the commands directory AND `.specforge/prompts/` with constitution.md + 7 domain governance files (identical to a recognized agent); if existing flow already handles this, test confirms it; if not, fix init_cmd.py to ensure governance generation is not gated on agent type
- [X] T056 Run full test suite validation — `uv run pytest --cov=specforge --cov-report=term-missing` and verify all tests pass with no regressions; `uv run ruff check src/ tests/` for lint compliance
- [X] T057 Run quickstart.md scenarios as manual validation — execute `specforge init TestApp --here` interactively with Claude, Copilot, Gemini, and Generic selections; verify output matches quickstart.md expected behavior

**Checkpoint**: All tests green, snapshots updated, full coverage, lint clean. Generic governance verified.

> **Commit**: `feat: add commands_written to ScaffoldResult and dry-run preview (FR-014, FR-017)`
> **Commit**: `test: verify generic agent receives full governance scaffold (FR-018)`
> **Commit**: `chore: update snapshots for agnostic-to-generic rename`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (rename must complete first) — BLOCKS all user stories
- **US2 — CommandRegistrar (Phase 3)**: Depends on Phase 2 (needs plugin properties)
- **US1 — Interactive Init (Phase 4)**: Depends on Phase 2 (plugin props) AND Phase 3 (CommandRegistrar)
- **US4 — Config Loader (Phase 5)**: Depends on Phase 2 only — can run in parallel with Phase 3
- **US3 — Generic Path (Phase 6)**: Depends on Phase 4 (init integration must exist)
- **US5 — Spec-Kit Compat (Phase 7)**: Depends on Phase 3 + Phase 4 (needs full init + commands flow)
- **Polish (Phase 8)**: Depends on all previous phases

### Within Each Phase

- Tests MUST be written and FAIL before implementation (TDD)
- Implementation tasks marked [P] can run in parallel
- Non-[P] tasks execute sequentially within dependency order

### Parallel Opportunities

```text
Phase 1: T001 → T002 → T003 (can parallel T002+T003) → T004 → T005+T006+T007 [P] → T008
Phase 2: T009+T010+T011 [P tests] → T012 → T013+T014 [P] → T015-T022 [P all] → T023
Phase 3: T024+T025+T026+T027+T028 [P tests] → T029 → T030 → T031 → T032+T033 [P]
Phase 4: T034+T035+T036+T037+T038 [P tests] → T039 → T040 → T041 → T042
Phase 5: T043+T044 [P tests] → T045+T046 [P] → T047+T047a [P]
                               ↕ (Phase 5 can run in parallel with Phase 3)
Phase 6: T048 → T049
Phase 7: T050+T051 [P]
Phase 8: T052+T053+T054+T055 [P] → T056 → T057
```

### Critical Path

```
T001→T004→T005→T009→T012→T024→T029→T030→T031→T034→T039→T041→T056
```

---

## Implementation Strategy

### MVP Scope (User Stories 1 + 2)

Phases 1–4 deliver the complete MVP:
- Interactive agent selection prompt (US1)
- Commands directory creation with 8 prompt files (US2)
- Config.json persistence is partially delivered via Phase 4 init integration

Ship after Phase 4 — users can select agents interactively and get working slash commands immediately.

### Incremental Delivery

- **Phase 5**: Config persistence (US4) — enables downstream commands to read agent context
- **Phase 6**: Generic path validation (US3) — enhances generic user path
- **Phase 7**: Spec-Kit compatibility verification (US5) — validates migration path
- **Phase 8**: Polish — snapshots, dry-run preview, ScaffoldResult update

### Commit Sequence (Conventional)

| Phase | Commit Message |
|-------|---------------|
| 1 | `refactor: rename agent "agnostic" to "generic" across codebase (FR-019)` |
| 2 | `feat: add commands_dir/command_format/args_placeholder properties to agent plugins (FR-020, FR-021, FR-023)` |
| 3 | `feat: add CommandRegistrar core service with Jinja2 command templates (FR-006, FR-007, FR-016)` |
| 4a | `feat: add interactive agent selection prompt to init command (FR-001–FR-005)` |
| 4b | `feat: wire CommandRegistrar into init flow with dry-run and force support (FR-013, FR-014, FR-017)` |
| 5 | `feat: extend config.json with agent and commands_dir fields (FR-011, FR-012)` |
| 6 | `feat: add commands-dir path validation for generic agent (FR-009, FR-010)` |
| 7 | `feat: ensure Spec-Kit compatible command file naming (FR-008, FR-022)` |
| 8a | `feat: add commands_written to ScaffoldResult and dry-run preview (FR-014, FR-017)` |
| 8b | `chore: update snapshots for agnostic-to-generic rename` |
