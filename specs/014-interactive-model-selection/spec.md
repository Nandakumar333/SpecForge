# Feature Specification: Interactive AI Model Selection & Commands Directory

**Feature Branch**: `014-interactive-model-selection`
**Created**: 2026-03-18
**Status**: Draft
**Input**: User description: "Build interactive AI model selection on specforge init --here and automatic creation of .specforge/commands/ (or root commands/) folder with one .md file per slash command — exactly matching Spec-Kit UX while keeping all existing automation."

## Clarifications

### Session 2026-03-18

- Q: Should the agent selection prompt list all 24+ agents from the plugin registry, or a curated subset? → A: Full dynamic list from plugin registry — auto-grows with new plugins, no curated subset
- Q: For "generic" mode, should the default commands directory be at project root or inside .specforge/? → A: Root-level `commands/` as default — more discoverable by generic AI tools
- Q: When "generic" is selected, should init also generate constitution.md and governance prompts? → A: Yes — full governance (constitution + 7 domain prompts in `.specforge/prompts/`) same as any recognized agent, plus the commands directory
- Q: How should the existing "agnostic" fallback reconcile with the new "generic" concept? → A: Unify on `"generic"` everywhere — replace all uses of `"agnostic"` with `"generic"` as the single fallback term
- Q: What naming convention should generated prompt files use for slash-command discoverability? → A: `specforge.{stage}` plus the agent's native extension — `.prompt.md` for Copilot (matching its discovery convention), `.md` for Claude/Cursor/etc., `.toml` for Gemini. The slash command `/specforge.decompose` is derived from the filename stem, not the extension. *(Clarified: `.prompt.md` is Copilot-specific, not universal.)*

### Session 2026-03-18 (Spec-Kit alignment)

- Q: Should each agent plugin define its own commands subdirectory matching Spec-Kit's AGENT_CONFIGS pattern? → A: Yes — each plugin defines a `commands_dir` property (`.claude/commands/`, `.gemini/commands/`, `.github/prompts/` for Copilot, etc.) so commands land where native AI tools actually scan
- Q: Should command files support agent-specific output formats (Markdown vs TOML) like Spec-Kit? → A: Yes — agent-specific formats: Markdown for Claude/Copilot/etc., TOML for Gemini; each plugin declares its format
- Q: Should command file content use agent-specific argument placeholders like Spec-Kit's convert_placeholder()? → A: Yes — agent-specific placeholders: `$ARGUMENTS` for Claude, `{{args}}` for Gemini/others; each plugin declares its placeholder via a property
- Q: Should init register commands for only the selected agent, or for ALL detected agents? → A: Selected agent only — simple and explicit; a future `specforge register` command handles additional agents
- Q: Should the agent plugin base class expose an unregister_commands() method now? → A: Defer entirely — no unregister capability in this feature; added when `specforge register` command is built

## Assumptions

- Rich is the interactive prompt library (already a project dependency); no new dependencies like `questionary` are added.
- The commands directory contains markdown prompt files that mirror SpecForge's pipeline stages: decompose, specify, research, plan, tasks, implement, status, and check.
- "Generic" agent means the user's AI tool is not among the recognized agent plugins; they need standalone prompt files they can paste or reference manually. Generic users still receive the full governance scaffold (constitution + domain prompts) in `.specforge/prompts/` — the commands directory is *in addition to* governance, not a replacement.
- When `--agent` is provided on the CLI, the interactive prompt is skipped entirely (backward-compatible).
- The interactive prompt only fires when running in an interactive terminal (TTY); in CI/scripted contexts, the existing auto-detect behavior is preserved.
- The commands directory location is agent-dependent: each agent plugin defines a `commands_dir` property matching the Spec-Kit convention (e.g., `.claude/commands/` for Claude, `.gemini/commands/` for Gemini, `.github/prompts/` for Copilot), while "generic" places files in a user-chosen directory defaulting to root-level `commands/` for maximum AI tool discoverability.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Interactive Agent Selection on Init (Priority: P1)

A new user runs `specforge init MyApp --here` (or `specforge init MyApp`) without the `--agent` flag. Instead of silently auto-detecting or falling back to agnostic, the CLI presents a selection prompt asking "Which AI agent do you want to use?" listing all supported agents plus "generic". The user picks one, and SpecForge configures the project accordingly.

**Why this priority**: This is the core UX change — the entire feature is meaningless without the interactive selection. It is the gateway to all downstream behaviors (commands dir creation, config persistence).

**Independent Test**: Can be fully tested by running `specforge init TestApp --here` in an interactive terminal with no `--agent` flag and verifying the selection prompt appears, accepts a choice, and the resulting `.specforge/config.json` records the selected agent.

**Acceptance Scenarios**:

1. **Given** a developer runs `specforge init MyApp --here` without `--agent` in an interactive terminal, **When** the init command starts, **Then** a selection prompt is displayed listing ALL registered agent plugins (currently 24+) sorted alphabetically, with a "generic" option always last.
2. **Given** the selection prompt is displayed, **When** the user selects "claude", **Then** the project is scaffolded with Claude-specific configuration and `config.json` records `"agent": "claude"`.
3. **Given** the selection prompt is displayed, **When** the user selects "generic", **Then** the project is scaffolded with generic agent configuration and the CLI proceeds to ask for a custom commands directory path.
4. **Given** the user provides `--agent copilot` on the command line, **When** init runs, **Then** no interactive prompt is shown and Copilot is configured directly (backward-compatible).
5. **Given** the command is running in a non-interactive environment (piped input, CI), **When** `--agent` is not provided, **Then** the existing auto-detect behavior is used with no prompt displayed.

---

### User Story 2 — Automatic Commands Directory Creation (Priority: P1)

After the agent is selected (either via prompt or `--agent`), SpecForge automatically creates a commands directory populated with one `.md` prompt file per slash command. These files contain ready-to-use prompts for each pipeline stage.

**Why this priority**: Equally critical to Story 1 — without the commands directory, the interactive selection has no tangible output. Together they form the MVP.

**Independent Test**: Can be fully tested by running `specforge init MyApp --here`, selecting any agent, and verifying that the commands directory exists with the expected set of `.md` files, each containing non-empty prompt content.

**Acceptance Scenarios**:

1. **Given** the user selects "copilot" as the agent, **When** scaffolding completes, **Then** a commands directory is created at the agent-appropriate location containing at least 8 `.prompt.md` files: `specforge.decompose.prompt.md`, `specforge.specify.prompt.md`, `specforge.research.prompt.md`, `specforge.plan.prompt.md`, `specforge.tasks.prompt.md`, `specforge.implement.prompt.md`, `specforge.status.prompt.md`, `specforge.check.prompt.md`.
2. **Given** the user selects "generic" and accepts the default commands directory, **When** scaffolding completes, **Then** `commands/` is created at the project root with the same set of `specforge.{stage}.prompt.md` files.
3. **Given** each generated prompt file, **When** opened, **Then** it contains a ready-to-use prompt appropriate for the corresponding pipeline stage (decompose, specify, etc.) with project-specific context variables filled in.
4. **Given** the `--dry-run` flag is passed, **When** the user completes the agent selection, **Then** the commands directory and its files are listed in the preview tree but not written to disk.
5. **Given** the `--force` flag is used and a commands directory already exists, **When** scaffolding runs, **Then** existing prompt files are preserved (not overwritten) and only missing files are added.

---

### User Story 3 — Generic Agent Custom Commands Directory (Priority: P2)

A user who selects "generic" is prompted for a custom commands directory path. This allows users of unsupported AI tools (or those who prefer a specific layout) to control where prompt files land.

**Why this priority**: Important for the "generic" user path but not blocking for users of recognized agents. Enhances flexibility without impacting the core flow.

**Independent Test**: Can be fully tested by selecting "generic" during init and providing a custom path like `commands/`, then verifying the directory is created at that path relative to the project root with all prompt files inside.

**Acceptance Scenarios**:

1. **Given** the user selects "generic" in the agent prompt, **When** the commands directory prompt appears, **Then** it shows a default value of `commands/` and allows the user to type a custom path.
2. **Given** the user enters `my-prompts/` as the custom path, **When** scaffolding completes, **Then** `my-prompts/` is created at the project root with all prompt files inside, and `config.json` records `"commands_dir": "my-prompts/"`.
3. **Given** the user presses Enter without typing (accepting the default), **When** scaffolding completes, **Then** `commands/` is created at the project root.
4. **Given** the user provides an absolute path or a path traversing outside the project, **When** the input is validated, **Then** an error is shown and the user is re-prompted.

---

### User Story 4 — Config.json Persists Agent and Commands Dir (Priority: P2)

The `.specforge/config.json` file is extended to store the chosen agent name and the commands directory path, so subsequent SpecForge commands know the project's agent context.

**Why this priority**: Necessary for downstream commands to operate correctly (e.g., `specforge status` needs to know the agent), but not visible to the user as a standalone feature.

**Independent Test**: Can be fully tested by running init with a selected agent, then reading `.specforge/config.json` and verifying the `agent` and `commands_dir` keys exist with correct values.

**Acceptance Scenarios**:

1. **Given** the user selects "claude" during init, **When** scaffolding completes, **Then** `.specforge/config.json` contains `"agent": "claude"` and `"commands_dir"` set to the appropriate agent-specific path.
2. **Given** the user selects "generic" with custom path `prompts/`, **When** scaffolding completes, **Then** `config.json` contains `"agent": "generic"` and `"commands_dir": "prompts/"`.
3. **Given** the user provides `--agent gemini` on the CLI, **When** scaffolding completes, **Then** `config.json` contains `"agent": "gemini"` with the correct commands directory for that agent.
4. **Given** the `--force` flag is used on an existing project, **When** config.json already exists, **Then** the `agent` and `commands_dir` fields are updated while other existing fields are preserved.

---

### User Story 5 — Spec-Kit Migration Compatibility (Priority: P3)

A developer switching from Spec-Kit to SpecForge wants zero-friction onboarding. Running `specforge init --here` in their existing project produces the same slash-command structure they are used to, so commands like `/specforge.decompose` or `/specforge.specify` work immediately.

**Why this priority**: Important for adoption but depends on Stories 1–2 being complete. The core feature serves new users first; migration users benefit automatically.

**Independent Test**: Can be fully tested by running `specforge init --here` in a directory, selecting an agent, then verifying that the generated prompt files are named and structured such that slash-command invocation (e.g., `/specforge.decompose "description"`) works in the corresponding AI tool.

**Acceptance Scenarios**:

1. **Given** a developer runs `specforge init --here` and selects "copilot", **When** they open their project in VS Code with Copilot, **Then** slash commands matching the generated `specforge.{stage}.prompt.md` files are available (e.g., `/specforge.decompose`).
2. **Given** the generated prompt files, **When** compared to Spec-Kit's command structure, **Then** the pipeline stages (decompose, specify, research, plan, tasks, implement, status, check) match one-to-one with the `specforge.{stage}.prompt.md` naming convention.
3. **Given** a developer previously using Spec-Kit, **When** they run `specforge init --here --force`, **Then** the commands directory is created alongside their existing project files without disrupting anything.

---

### Edge Cases

- What happens when the terminal is non-interactive (piped input, CI runner) and `--agent` is not provided?
  → The existing auto-detect behavior is used; no interactive prompt is shown. If no agent is detected, "generic" is used (per FR-019).
- What happens when the user presses Ctrl+C during the interactive prompt?
  → The init command aborts cleanly with exit code 130 and no partial files are written.
- What happens when the user selects "generic" but provides an empty commands directory path?
  → The default `commands/` (root-level) is used.
- What happens when the commands directory already exists with custom-edited prompt files and `--force` is used?
  → Existing files are preserved; only missing prompt files are added. No overwrites.
- What happens when the auto-detected agent has no commands directory mapping?
  → Falls back to `.specforge/commands/` as default.
- What happens when `--dry-run` and the interactive prompt are combined?
  → The interactive prompt still runs (to collect user intent), but no files are written; the preview tree shows what would be created.
- What happens when the user wants commands registered for multiple AI agents simultaneously?
  → Out of scope for `init`. The user runs init with their primary agent. A future `specforge register --agent <name>` command will add commands for additional agents.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `--agent` is NOT provided and the terminal is interactive, the `init` command MUST display a selection prompt asking "Which AI agent do you want to use?" with all registered agent plugins plus a "generic" option.
- **FR-002**: The selection prompt MUST list ALL agents dynamically from the plugin registry (currently 24+), not from a hardcoded or curated subset, so new agent plugins are automatically included without code changes. The list MUST be sorted alphabetically with "generic" always appearing last.
- **FR-003**: When the user selects an agent from the prompt, the `init` command MUST use that selection for all downstream configuration (agent-specific config files, commands directory, config.json).
- **FR-004**: When `--agent` IS provided on the command line, the interactive prompt MUST be skipped entirely (backward-compatible with Feature 001 behavior).
- **FR-005**: When the terminal is non-interactive (no TTY), the `init` command MUST fall back to the existing auto-detect behavior without displaying any prompt.
- **FR-006**: After agent selection, the `init` command MUST create a commands directory populated with one command file per pipeline stage covering these stages: decompose, specify, research, plan, tasks, implement, status, and check (minimum 8 files). The filename convention is `specforge.{stage}` plus the agent's native extension (`.md` for Markdown agents, `.toml` for TOML agents). For Copilot, a companion `.prompt.md` file is also generated in `.github/prompts/`.
- **FR-007**: Each generated prompt file MUST contain a ready-to-use prompt appropriate for its pipeline stage, rendered from a template with project-specific context (project name, stack, architecture).
- **FR-008**: The commands directory location MUST be determined by each agent plugin's `commands_dir` property, following Spec-Kit's convention: `.claude/commands/` for Claude, `.gemini/commands/` for Gemini, `.github/prompts/` for Copilot, and agent-appropriate paths for others. "Generic" uses a user-specified or default root-level `commands/` path.
- **FR-009**: When the user selects "generic", the CLI MUST prompt for a custom commands directory path with a default value of `commands/` (root-level, for maximum AI tool discoverability).
- **FR-010**: The custom commands directory path MUST be validated: it must be a relative path that does not traverse outside the project root (no `../` escapes, no absolute paths).
- **FR-011**: The `.specforge/config.json` file MUST be extended to include an `"agent"` field recording the selected agent name.
- **FR-012**: The `.specforge/config.json` file MUST be extended to include a `"commands_dir"` field recording the relative path to the commands directory.
- **FR-013**: When `--force` is used and a commands directory already exists, existing prompt files MUST be preserved and only missing files MUST be added.
- **FR-014**: When `--dry-run` is used, the interactive prompt MUST still be shown (to collect user intent), but the commands directory and its files MUST only appear in the preview tree without being written.
- **FR-015**: When the user presses Ctrl+C or otherwise interrupts the interactive prompt, the command MUST abort cleanly with no partial files written.
- **FR-016**: The prompt file templates MUST be stored as Jinja2 `.md.j2` templates in the SpecForge package, consistent with the existing template architecture.
- **FR-017**: The commands directory MUST be included in the scaffold plan so it appears in dry-run previews and git commits. *(Note: agent-native commands directories like `.claude/commands/` are outside `.specforge/` but still part of the scaffold plan.)*
- **FR-018**: When "generic" is selected, the `init` command MUST generate the full governance scaffold (constitution.md + all 7 domain governance prompts in `.specforge/prompts/`) identical to any recognized agent, in addition to the commands directory.
- **FR-019**: The term `"agnostic"` MUST be replaced with `"generic"` across the entire codebase as the unified fallback agent value. Config.json, auto-detect fallback, and all internal references MUST use `"generic"` exclusively — no dual terminology.
- **FR-020**: Each agent plugin class MUST expose a `commands_dir` property returning the agent-native commands directory path (e.g., `.claude/commands/`, `.gemini/commands/`, `.github/prompts/`). The `AgentPlugin` base class MUST define this as a concrete property with a default value of `".specforge/commands"` — NOT abstract — so existing plugin subclasses that accept the default need no changes (per plan §D-01).
- **FR-021**: Each agent plugin class MUST expose a `command_format` property returning either `"markdown"` or `"toml"`, and a `command_extension` property returning the file extension (`.md` or `.toml`). Command files MUST be rendered in the agent's declared format.
- **FR-022**: For Copilot, the command registrar MUST write command files directly to `.github/prompts/` as `specforge.{stage}.prompt.md` with full prompt content. The `.prompt.md` file IS the command file for Copilot — no separate companion stub is needed (per plan §D-07). This enables Copilot slash-command discovery via the `.prompt.md` naming convention.
- **FR-023**: Each agent plugin class MUST expose an `args_placeholder` property returning the agent-native argument placeholder string (`$ARGUMENTS` for Claude, `{{args}}` for Gemini/others). Command templates MUST use a universal token (e.g., `{{ arguments }}`) that is replaced with the agent's placeholder during rendering.
- **FR-024**: The `init` command MUST register commands for ONLY the selected agent (not all detected agents). Multi-agent command registration is explicitly deferred to a future `specforge register --agent <name>` command.
- **FR-025**: Command unregistration (removing previously registered command files) is explicitly OUT OF SCOPE for this feature. No `unregister_commands()` method is added to the plugin base class. This capability is deferred to a future `specforge register`/`specforge unregister` command.

### Key Entities

- **Agent Selection**: The user's choice of AI agent — determines config files generated, commands directory location, and prompt file content. Values: any registered agent plugin name or "generic" (unified fallback replacing the former "agnostic" value).
- **Commands Directory**: A folder containing one `.md` prompt file per pipeline stage. Location varies by agent; stored in `config.json` as `commands_dir`.
- **Prompt File**: A command file named `specforge.{stage}` plus the agent's native extension (`.md` for Markdown agents, `.toml` for TOML agents like Gemini). Contains a ready-to-use prompt for a specific pipeline stage with the agent-native argument placeholder (`$ARGUMENTS` for Claude, `{{args}}` for Gemini/others). For Copilot, a companion `specforge.{stage}.prompt.md` stub is also generated in `.github/prompts/` with YAML frontmatter for slash-command discovery. Rendered from Jinja2 templates with project context.
- **Config.json (extended)**: The existing project configuration file, now additionally storing `agent` and `commands_dir` fields alongside `project_name`, `stack`, and `version`. The `agent` field uses `"generic"` as the unified fallback (replacing former `"agnostic"`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can go from `specforge init MyApp --here` to a fully configured project with ready-to-use slash commands in under 60 seconds, including the interactive prompt.
- **SC-002**: 100% of recognized agent selections produce a commands directory at the agent-appropriate location with all 8+ prompt files present and non-empty.
- **SC-003**: The "generic" agent path prompts for a custom directory and correctly creates it at the specified location in 100% of cases.
- **SC-004**: Existing `--agent <name>` CLI usage continues to work without any interactive prompt — zero breaking changes to the current interface.
- **SC-005**: Users can immediately invoke generated prompt files as slash commands (e.g., `/specforge.decompose`) in their AI tool after init completes — zero manual file creation required.
- **SC-006**: The `config.json` file correctly records both `agent` and `commands_dir` after every init invocation, regardless of selection method (interactive, `--agent` flag, or auto-detect).
- **SC-007**: Running `specforge init --here --force` on an existing project with custom-edited prompt files preserves 100% of those edits while adding any missing prompt files.
