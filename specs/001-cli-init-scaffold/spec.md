# Feature Specification: SpecForge CLI Init & Scaffold

**Feature Branch**: `001-cli-init-scaffold`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Build the core CLI entry point for SpecForge. When a user runs 'specforge init <project-name>', the tool should create a new project directory with complete .specforge/ structure, detect installed AI agents, initialize a git repository, and support flags for agent, stack, here, force, and no-git. Also includes 'specforge check' and 'specforge decompose' commands."

## Clarifications

### Session 2026-03-14

- Q: What is the agent detection priority order when multiple agents are installed? → A: `claude → copilot → gemini → cursor → windsurf → codex`
- Q: What are the default tech stack templates when `--stack` is not specified? → A: Agnostic/generic — language-neutral templates with stack placeholder left empty; no stack-specific content applied
- Q: Should `init` create an initial git commit, and if so what is the message? → A: Yes — commit message is `"chore: init specforge scaffold"`
- Q: Should the CLI support a `--dry-run` flag? → A: Yes — prints file tree that would be created without writing any files
- Q: What Python packaging format should be used, and should `uv tool install` be supported? → A: `pyproject.toml` with `uv`; CLI must be installable via `uv tool install specforge`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scaffold New Project from Scratch (Priority: P1)

A developer starts a brand-new project and wants to immediately use SpecForge for spec-driven development. They run a single command with their project name and get a fully configured project directory ready to use, with no additional setup required.

**Why this priority**: This is the primary entry point to the entire SpecForge workflow. Without it, nothing else works. Every other feature depends on a properly initialized project structure.

**Independent Test**: Can be fully tested by running `specforge init myapp` in an empty parent directory and verifying the resulting file tree and git repository state — delivers a fully usable, ready-to-work SpecForge project.

**Acceptance Scenarios**:

1. **Given** an empty parent directory, **When** the user runs `specforge init myapp`, **Then** a `myapp/` directory is created containing the complete `.specforge/` structure, a git repository is initialized, a `.gitignore` is created, an initial commit with message `"chore: init specforge scaffold"` is made, and a summary of created files and next steps is displayed.
2. **Given** the user specifies `--agent claude`, **When** `specforge init myapp --agent claude` is run, **Then** Claude-specific config files are generated inside `.specforge/` and the summary confirms the agent was configured.
3. **Given** the user specifies `--stack dotnet`, **When** `specforge init myapp --stack dotnet`, **Then** stack-appropriate defaults are reflected in the generated templates and constitution.
4. **Given** the project directory already exists and `--force` is NOT passed, **When** `specforge init myapp` is run, **Then** the command aborts with a clear error explaining how to use `--force` to proceed.
5. **Given** the project directory already exists, **When** `specforge init myapp --force` is run, **Then** the `.specforge/` structure is added to the existing directory without overwriting existing files or deleting unrelated files.
6. **Given** the user passes `--dry-run`, **When** `specforge init myapp --dry-run` is run, **Then** the complete file tree that would be created is printed to stdout and no files are written, no git repository is initialized.

---

### User Story 2 - Initialize SpecForge in an Existing Project (Priority: P2)

A developer is already working on a project and wants to adopt SpecForge without moving their codebase. They need to add the `.specforge/` structure into their current working directory.

**Why this priority**: Many developers will be adopting SpecForge mid-project. Supporting `--here` is critical to adoption without disrupting existing workflows.

**Independent Test**: Can be fully tested by running `specforge init --here` inside an existing non-empty directory and verifying that `.specforge/` was created alongside existing files with no data loss.

**Acceptance Scenarios**:

1. **Given** a developer is in an existing project directory, **When** they run `specforge init --here`, **Then** `.specforge/` is created in the current directory without creating a subdirectory, and existing files are untouched.
2. **Given** `.specforge/` already exists and `--force` is NOT passed, **When** `specforge init --here` is run, **Then** the command aborts with a clear error and instructions to use `--force`.
3. **Given** `.specforge/` already exists, **When** `specforge init --here --force` is run, **Then** missing files are created and existing files are preserved (not overwritten).

---

### User Story 3 - Verify Prerequisites with `specforge check` (Priority: P3)

A developer setting up a new machine wants to confirm their environment has everything SpecForge needs before starting work. They run a single verification command that lists all required tools with their installed/missing status.

**Why this priority**: Reduces setup friction and support burden. Developers get immediate, actionable feedback rather than cryptic errors later.

**Independent Test**: Can be fully tested by running `specforge check` on a machine and verifying that the output lists each required tool (git, python, uv, AI agent CLI) with a clear pass/fail status per tool.

**Acceptance Scenarios**:

1. **Given** all required tools are installed, **When** `specforge check` is run, **Then** each tool is listed with a green/pass indicator and an overall "all prerequisites met" message is shown.
2. **Given** one or more required tools are missing, **When** `specforge check` is run, **Then** missing tools are listed with a red/fail indicator and a hint on how to install each missing tool.
3. **Given** an `--agent` flag is provided, **When** `specforge check --agent gemini` is run, **Then** the check includes verification of the specified agent CLI in addition to common prerequisites.

---

### User Story 4 - Auto-Detect Installed AI Agent (Priority: P3)

A developer runs `specforge init` without specifying `--agent` and expects the tool to automatically detect which AI coding agent is available on their system and configure the project accordingly.

**Why this priority**: Reduces configuration friction for the majority of users who only have one agent installed. Manual specification via `--agent` remains the override.

**Independent Test**: Can be fully tested by running `specforge init myapp` on a machine with a known agent installed (e.g., `claude` CLI in PATH) and verifying that agent-specific config files appear in `.specforge/` without the user passing `--agent`.

**Acceptance Scenarios**:

1. **Given** only the `claude` CLI is present in PATH, **When** `specforge init myapp` is run without `--agent`, **Then** Claude-specific config files are generated and the summary confirms auto-detected agent as "claude".
2. **Given** no supported agent CLI is found in PATH, **When** `specforge init myapp` is run, **Then** a generic/agnostic config is generated and the summary warns that no agent was detected with instructions to re-run with `--agent`.
3. **Given** multiple agent CLIs are installed, **When** `specforge init myapp` is run without `--agent`, **Then** the tool detects the first in priority order (`claude → copilot → gemini → cursor → windsurf → codex`) and notifies the user which agent was selected, with instructions to override via `--agent`.

---

### User Story 5 - Decompose App Description into Features (Priority: P4)

A developer provides a one-line description of their application and wants SpecForge to break it down into a list of features they can spec out individually.

**Why this priority**: This is a forward-looking entry point to the spec pipeline. The command exists at the CLI layer but delegates to the App Analyzer agent; its success here is limited to correct invocation and output display.

**Independent Test**: Can be fully tested by running `specforge decompose "A task management app with team collaboration"` and verifying the command invokes the App Analyzer and displays a structured feature list.

**Acceptance Scenarios**:

1. **Given** a one-line description is provided, **When** `specforge decompose "A task manager with team collaboration"` is run, **Then** the App Analyzer (Feature 004) is invoked with the description and a list of identified features is displayed to the user.
2. **Given** no description is provided, **When** `specforge decompose` is run without arguments, **Then** the command displays a usage error with an example of correct usage.

---

### Edge Cases

- What happens when the project name contains special characters or spaces?
  → **Resolved in FR-015**: name is validated against `^[a-zA-Z0-9_-]+$`; invalid names produce an error with exit code 1.
- What happens when the user lacks write permissions in the target directory?
  → **Resolved in FR-018**: the CLI MUST detect permission errors and exit 1 with the message `"Error: Permission denied writing to '<path>'. Check directory permissions."`
- What happens when git is not installed and `--no-git` is not passed?
  → **Resolved in FR-019**: the CLI MUST detect that `git` is not in PATH before attempting `Repo.init()` and exit 1 with the message `"Error: git is not installed. Install git or use --no-git to skip git initialization."`
- What happens when an unsupported `--agent` or `--stack` value is provided?
  → **Resolved by Click**: `click.Choice` rejects invalid values with exit code 2 and a usage hint.
- What happens when `specforge init` is run inside an existing git repository?
  → **Resolved in FR-020**: the CLI MUST skip `git init` when the target directory is already inside a git repository, but still stage and commit the new `.specforge/` contents into the existing repo.
- How does the tool behave if it is interrupted mid-scaffold (partial directory tree)?
  → **Accepted risk**: partial state is left on disk; no rollback. The user can re-run with `--force` to complete the scaffold. This is documented in quickstart.md troubleshooting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST provide an `init` command that accepts a project name as a positional argument.
- **FR-002**: The `init` command MUST create the complete `.specforge/` directory structure including:
  - `constitution.md` (project constitution template)
  - `memory/constitution.md` and `memory/decisions.md`
  - `features/` subdirectory (empty)
  - `prompts/` subdirectory with 7 agent prompt files: `app-analyzer.md`, `feature-specifier.md`, `implementation-planner.md`, `task-decomposer.md`, `code-reviewer.md`, `test-writer.md`, `debugger.md`
  - `templates/features/` subdirectory with 7 per-feature templates: `spec-template.md`, `plan-template.md`, `tasks-template.md`, `research-template.md`, `data-model-template.md`, `quickstart-template.md`, `contracts-template.md`
  - `scripts/` subdirectory (empty at init time)
- **FR-003**: The `init` command MUST support a `--here` flag that scaffolds `.specforge/` into the current working directory instead of creating a new subdirectory.
- **FR-004**: The `init` command MUST support a `--force` flag that allows scaffolding into an existing directory, adding missing files without overwriting existing ones.
- **FR-005**: The `init` command MUST support an `--agent` flag accepting values: `claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex` — and generate the appropriate agent-specific configuration files.
- **FR-006**: The `init` command MUST support a `--stack` flag accepting values: `dotnet`, `nodejs`, `python`, `go`, `java` — and apply stack-appropriate defaults to generated templates. When `--stack` is not specified, agnostic/generic templates are generated: the `stack` context variable is set to `"agnostic"` and stack-specific template sections are excluded via Jinja2 conditionals.
- **FR-007**: The `init` command MUST support a `--no-git` flag that skips git repository initialization.
- **FR-008**: When `--agent` is not specified, the tool MUST auto-detect installed agent CLIs from PATH in this priority order: `claude → copilot → gemini → cursor → windsurf → codex`. The first found is used; if none found, generate agnostic config.
- **FR-009**: The `init` command MUST initialize a git repository, create a `.gitignore`, and create an initial git commit with the message `"chore: init specforge scaffold"`, unless `--no-git` is passed.
- **FR-010**: The `init` command MUST display a summary of all created directories and files, the detected/configured agent, and suggested next steps upon completion.
- **FR-011**: The CLI MUST provide a `check` command that verifies the presence of: `git`, `python`, `uv`, and the selected/detected AI agent CLI.
- **FR-012**: The `check` command MUST report each prerequisite individually as installed or missing, with install hints for missing tools.
- **FR-013**: The CLI MUST provide a `decompose` command that accepts a one-line application description and invokes the App Analyzer agent (Feature 004) with that description.
- **FR-014**: The CLI MUST return a non-zero exit code and a human-readable error message for all failure conditions (missing args, permission errors, invalid flags, unsupported values).
- **FR-015**: Project names MUST be validated: only alphanumeric characters, hyphens, and underscores allowed; an error MUST be shown for invalid names.
- **FR-016**: The `init` command MUST support a `--dry-run` flag that prints the complete file tree that would be created, without writing any files or initializing git. `--dry-run` is orthogonal to all other flags: `--dry-run --here` previews the CWD tree, `--dry-run --force` previews without checking for existing files, `--dry-run --no-git` previews without the `.gitignore` and git commit entries.
- **FR-017**: The CLI MUST be packaged using `pyproject.toml` with `uv` as the build/dependency tool and MUST be installable via `uv tool install specforge`.
- **FR-018**: When a write permission error occurs on the target directory, the CLI MUST exit 1 with the message `"Error: Permission denied writing to '<path>'. Check directory permissions."`
- **FR-019**: When `git` is not found in PATH and `--no-git` is not passed, the CLI MUST exit 1 with the message `"Error: git is not installed. Install git or use --no-git to skip git initialization."`
- **FR-020**: When `specforge init` is run inside an existing git repository, the CLI MUST skip `git init` but still stage and commit the new `.specforge/` contents into the existing repo.

### Key Entities

- **Project**: The scaffolded SpecForge project — has a name, target directory, agent configuration, stack selection, git state, and `.specforge/` structure.
- **Agent Configuration**: The set of files and settings generated to support a specific AI coding agent within `.specforge/prompts/` and any agent-specific config files.
- **Stack Profile**: A set of default template values and constitution hints associated with a technology stack (dotnet, nodejs, python, go, java).
- **Prerequisite**: A required external tool (git, python, uv, agent CLI) that must be discoverable in the system PATH for SpecForge to function.

### Constraints & Tradeoffs

- **CT-001**: The CLI MUST be implemented in Python, packaged with `pyproject.toml` and `uv` as the build/dependency tool.
- **CT-002**: The CLI MUST be installable via `uv tool install specforge` as the primary distribution mechanism.
- **CT-003**: Agent detection is PATH-only (no registry or config file scanning); this is an explicit tradeoff favoring simplicity over completeness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from zero to a fully scaffolded SpecForge project in under 30 seconds by running a single command.
- **SC-002**: Running `specforge init myapp` with no flags produces a complete, valid project structure with zero manual follow-up steps required before starting spec work.
- **SC-003**: Auto-detection correctly identifies the installed AI agent in 100% of cases where exactly one supported agent CLI is present in PATH.
- **SC-004**: `specforge check` covers all required prerequisites and reports each with a clear pass/fail — 0 ambiguous or missing tool checks.
- **SC-005**: All CLI error messages include actionable guidance — 0 errors that leave the user without a next step.
- **SC-006**: The `--here --force` workflow preserves 100% of existing files in the target directory (no unintended deletions or overwrites).
