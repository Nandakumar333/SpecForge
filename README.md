<div align="center">
    <h1>⚙️ SpecForge</h1>
    <h3><em>Build high-quality software faster.</em></h3>
</div>

<p align="center">
    <strong>An open source, AI-powered spec-driven development engine that scaffolds your project, enforces your principles, and guides every feature from idea to implementation.</strong>
</p>

<p align="center">
    <a href="https://github.com/your-org/specforge/actions/workflows/release.yml"><img src="https://github.com/your-org/specforge/actions/workflows/release.yml/badge.svg" alt="Release"/></a>
    <a href="https://github.com/your-org/specforge/stargazers"><img src="https://img.shields.io/github/stars/your-org/specforge?style=social" alt="GitHub stars"/></a>
    <a href="https://github.com/your-org/specforge/blob/main/LICENSE"><img src="https://img.shields.io/github/license/your-org/specforge" alt="License"/></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
    <img src="https://img.shields.io/badge/install%20with-uv-violet" alt="Install with uv"/>
</p>

---

## Table of Contents

- [🤔 What is Spec-Driven Development?](#-what-is-spec-driven-development)
- [⚡ Get Started](#-get-started)
- [🤖 Supported AI Agents](#-supported-ai-agents)
- [🔧 SpecForge CLI Reference](#-specforge-cli-reference)
- [📚 Core Philosophy](#-core-philosophy)
- [🌟 Development Phases](#-development-phases)
- [🔧 Prerequisites](#-prerequisites)
- [📋 Detailed Process](#-detailed-process)
- [🔍 Troubleshooting](#-troubleshooting)
- [💬 Support](#-support)
- [📄 License](#-license)

---

## 🤔 What is Spec-Driven Development?

Spec-Driven Development **flips the script** on traditional software development. For decades, code has been king — specifications were just scaffolding we built and discarded once the "real work" of coding began. Spec-Driven Development changes this: **specifications become executable**, directly generating working implementations rather than just guiding them.

SpecForge is the engine that makes this workflow concrete. It scaffolds your project with a structured `.specforge/` directory, populates it with AI agent prompts and feature templates tailored to your tech stack, and provides a suite of slash commands that guide your AI coding agent through every phase — from idea to shipped feature.

---

## ⚡ Get Started

### 1. Install SpecForge

#### Option 1: Persistent Installation (Recommended)

Install once and use everywhere:

```bash
uv tool install specforge --from git+https://github.com/your-org/specforge.git
```

Then use the tool directly:

```bash
# Create a new project
specforge init <PROJECT_NAME>

# Or initialize in an existing project
specforge init --here --agent claude

# Check installed tools and prerequisites
specforge check
```

To upgrade SpecForge:

```bash
uv tool install specforge --force --from git+https://github.com/your-org/specforge.git
```

#### Option 2: One-time Usage

Run directly without installing:

```bash
# Create a new project
uvx --from git+https://github.com/your-org/specforge.git specforge init <PROJECT_NAME>

# Or initialize in an existing project
uvx --from git+https://github.com/your-org/specforge.git specforge init --here --agent claude
```

**Benefits of persistent installation:**

- Tool stays installed and available in PATH
- No need to create shell aliases
- Better tool management with `uv tool list`, `uv tool upgrade`, `uv tool uninstall`
- Cleaner shell configuration

---

### 2. Establish project principles

Launch your AI assistant in the project directory. The `/speckit.*` commands are available in the assistant after initialization.

Use the **`/speckit.constitution`** command to create your project's governing principles — the development guidelines that will steer every subsequent decision.

```
/speckit.constitution Create principles focused on code quality, testing standards, clean architecture, and performance requirements.
```

This step creates `.specforge/memory/constitution.md` — the foundational document that your AI agent references throughout specification, planning, and implementation.

---

### 3. Create the spec

Use **`/speckit.specify`** to describe what you want to build. Focus on the **what** and **why** — not the tech stack.

```
/speckit.specify Build a task management app where teams create projects, assign tasks to members, and track progress through a Kanban board with drag-and-drop cards.
```

---

### 4. Clarify the spec

Use **`/speckit.clarify`** to identify and resolve underspecified areas before investing in a technical plan. This step significantly reduces downstream rework.

```
/speckit.clarify
```

---

### 5. Create a technical implementation plan

Use **`/speckit.plan`** to provide your tech stack and architecture choices.

```
/speckit.plan The backend is Python + FastAPI with PostgreSQL. The frontend is React + TypeScript. Use Docker Compose for local development.
```

---

### 6. Break down into tasks

Use **`/speckit.tasks`** to create an actionable, dependency-ordered task list from your implementation plan.

```
/speckit.tasks
```

---

### 7. Execute implementation

Use **`/speckit.implement`** to execute all tasks and build your feature according to the plan.

```
/speckit.implement
```

---

## 🤖 Supported AI Agents

| Agent | Support | CLI Binary | Notes |
|-------|---------|-----------|-------|
| [Claude Code](https://www.anthropic.com/claude-code) | ✅ | `claude` | Auto-detected first in priority order |
| [GitHub Copilot](https://github.com/features/copilot) | ✅ | `copilot` | Standalone Copilot CLI |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | ✅ | `gemini` | |
| [Cursor](https://cursor.com) | ✅ | `cursor` | Install `cursor` command via Command Palette |
| [Windsurf](https://windsurf.com) | ✅ | `windsurf` | Requires manual PATH setup |
| [Codex CLI](https://github.com/openai/codex) | ✅ | `codex` | Requires manual PATH setup |
| Agnostic | ✅ | — | Generated when no agent is detected; use `--agent` to override |

**Auto-detection priority**: When `--agent` is not specified, SpecForge scans PATH in the order above and uses the first agent found. If none are found, an agent-agnostic configuration is generated.

---

## 🔧 SpecForge CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `init` | Scaffold a new SpecForge project with `.specforge/` structure, agent config, and git initialization |
| `check` | Verify that all required tools (`git`, `python`, `uv`, agent CLI) are installed and accessible |
| `decompose` | Break a one-line application description into a list of features to spec individually |

---

### `specforge init` Arguments & Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<project-name>` | Argument | — | Name for your new project directory. Required unless `--here` is used. Allowed characters: `[a-zA-Z0-9_-]` |
| `--agent` | Option | (auto-detect) | AI agent to configure: `claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex` |
| `--stack` | Option | (agnostic) | Tech stack for template defaults: `dotnet`, `nodejs`, `python`, `go`, `java` |
| `--here` | Flag | `False` | Scaffold `.specforge/` into the current directory instead of creating a new subdirectory. Mutually exclusive with `<project-name>` |
| `--force` | Flag | `False` | Allow scaffolding into an existing directory. Preserves existing files; only adds missing ones |
| `--no-git` | Flag | `False` | Skip `git init`, `.gitignore` creation, and initial commit |
| `--dry-run` | Flag | `False` | Preview the file tree that would be created — no files written, no git operations |

---

### `specforge check` Options

| Option | Description |
|--------|-------------|
| `--agent` | Include a specific agent CLI in the prerequisite check: `claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex` |

---

### `specforge decompose` Arguments

| Argument | Description |
|----------|-------------|
| `DESCRIPTION` | Required. A one-line description of the application to break down into features |

---

### Examples

```bash
# Basic project initialization (auto-detects installed agent)
specforge init my-project

# Initialize with a specific AI agent
specforge init my-project --agent claude

# Initialize with agent and tech stack
specforge init my-project --agent claude --stack python

# Initialize in the current directory (existing project)
specforge init --here --agent copilot

# Add missing .specforge/ files to an existing project (preserves existing files)
specforge init --here --force --agent gemini

# Preview what would be created without writing anything
specforge init my-project --dry-run

# Skip git initialization
specforge init my-project --agent claude --no-git

# Check all prerequisites
specforge check

# Check prerequisites including a specific agent
specforge check --agent claude

# Decompose an app description into features
specforge decompose "A task management app with team collaboration and Kanban boards"
```

---

### Available Slash Commands

After running `specforge init`, your AI coding agent will have access to these slash commands for structured spec-driven development:

#### Core Commands

Essential commands for the full Spec-Driven Development workflow:

| Command | Description |
|---------|-------------|
| `/speckit.constitution` | Create or update project governing principles and development guidelines |
| `/speckit.specify` | Define what you want to build — requirements, user stories, and acceptance criteria |
| `/speckit.clarify` | Identify and resolve underspecified areas before planning (recommended before `/speckit.plan`) |
| `/speckit.plan` | Create a technical implementation plan with your chosen tech stack and architecture |
| `/speckit.tasks` | Generate an actionable, dependency-ordered task list for implementation |
| `/speckit.implement` | Execute all tasks and build the feature according to the plan |

#### Optional Commands

Additional commands for quality, validation, and exploration:

| Command | Description |
|---------|-------------|
| `/speckit.analyze` | Cross-artifact consistency and coverage analysis — run after `/speckit.tasks`, before `/speckit.implement` |
| `/speckit.checklist` | Generate custom quality checklists that validate requirements completeness, clarity, and consistency — "unit tests for English" |

---

## 📚 Core Philosophy

Spec-Driven Development is a structured process that emphasizes:

- **Intent-driven development** where specifications define the *what* before the *how*
- **Constitution-first governance** — project principles established once, enforced everywhere
- **Spec-before-code** discipline — no implementation begins until `spec.md`, `plan.md`, and `tasks.md` all exist
- **Multi-step refinement** rather than one-shot code generation from prompts
- **Heavy reliance** on advanced AI model capabilities for specification interpretation and implementation

SpecForge enforces these principles through its project structure, its template system, and the constitution gates built into every slash command.

---

## 🌟 Development Phases

| Phase | Focus | Key Activities |
|-------|-------|----------------|
| **0-to-1 Development** ("Greenfield") | Generate from scratch | Start with high-level requirements → generate specifications → plan implementation → build production-ready applications |
| **Creative Exploration** | Parallel implementations | Explore diverse solutions, support multiple technology stacks and architectures, experiment with UX patterns |
| **Iterative Enhancement** ("Brownfield") | Add to existing projects | Adopt SpecForge mid-project with `--here`, add features iteratively, modernize incrementally |

---

## 🔧 Prerequisites

- **Linux / macOS / Windows**
- A [supported AI coding agent](#-supported-ai-agents) installed and accessible in PATH
- [uv](https://docs.astral.sh/uv/) — for package management and tool install
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

Run `specforge check` at any time to verify your environment.

---

## 📋 Detailed Process

<details>
<summary>Click to expand the step-by-step walkthrough</summary>

### Bootstrap your project

Use the SpecForge CLI to scaffold your project directory:

```bash
specforge init <project_name>
```

Or adopt SpecForge in an existing project:

```bash
# Scaffold .specforge/ into your current directory
specforge init --here --agent claude

# Force-add missing files alongside existing .specforge/ content
specforge init --here --force --agent claude
```

SpecForge will:
1. Create the `.specforge/` directory structure
2. Render all Jinja2 templates with your project name, agent, and stack
3. Initialize a git repository and create an initial commit: `chore: init specforge scaffold`
4. Print a summary of all created files and suggested next steps

Preview what would be created without writing anything:

```bash
specforge init my-project --dry-run
```

---

### STEP 1: Establish project principles

Open your AI coding agent in the project directory. You'll see the `/speckit.*` commands are now available.

Start with **`/speckit.constitution`** to create your project's governing principles:

```
/speckit.constitution Create principles focused on code quality and testability. All domain logic must be in the core layer with zero external dependencies. Functions must not exceed 30 lines. All recoverable errors must use Result[T] — no exceptions for control flow.
```

This creates `.specforge/memory/constitution.md` — the foundational document that gates all planning and implementation work.

---

### STEP 2: Create the spec

Use **`/speckit.specify`** and describe your feature in natural language. Focus on the *what* and *why* — leave the technology choices for the planning step.

> **Important**: Be as explicit as possible about what you are building and why. Do not mention the tech stack yet.

```
/speckit.specify Build a Kanban task board. Users log in, see their assigned projects, open a project to view its Kanban columns (To Do, In Progress, In Review, Done), and drag-and-drop task cards between columns. Cards show assignee, title, and status. Users can comment on cards and edit or delete only their own comments.
```

Once complete, a new branch is created (e.g., `001-kanban-task-board`) along with `specs/001-kanban-task-board/spec.md` containing user stories, functional requirements, success criteria, and edge cases.

---

### STEP 3: Clarify the spec

Run **`/speckit.clarify`** to surface and resolve underspecified areas before you invest in a technical plan. The command identifies up to 5 high-impact clarification questions and records the answers directly in the spec.

```
/speckit.clarify
```

This step is not optional for production work — skipping it increases downstream rework risk significantly.

---

### STEP 4: Generate the plan

Now specify your tech stack. Use **`/speckit.plan`**:

```
/speckit.plan The backend is Python 3.11 + FastAPI with PostgreSQL. Frontend is React 18 + TypeScript with Vite. Real-time updates via WebSockets. Deployed on Docker Compose locally.
```

This produces:
- `plan.md` — full technical implementation plan with constitution gates
- `research.md` — resolved technical unknowns and library decisions
- `data-model.md` — all domain entities, fields, and relationships
- `contracts/` — API contracts, CLI command schemas, or other interface specs
- `quickstart.md` — from-zero-to-running guide for the feature

---

### STEP 5: Validate the plan

Before generating tasks, use **`/speckit.analyze`** to cross-check all artifacts for consistency and coverage gaps:

```
/speckit.analyze
```

This catches mismatches between `spec.md`, `plan.md`, and your contracts before they become bugs.

You can also generate a custom validation checklist:

```
/speckit.checklist Validate all acceptance criteria are testable, all error handling is specified, and the plan references constitution coding standards.
```

---

### STEP 6: Generate tasks

Use **`/speckit.tasks`** to create a dependency-ordered, TDD-structured task list:

```
/speckit.tasks
```

This creates `tasks.md` containing:
- Tasks organized by user story
- Dependencies respected (models before services, services before endpoints)
- Test files ordered before their implementation counterparts (TDD enforced)
- Parallel execution markers `[P]` for tasks that can run concurrently
- Exact file paths for every task

---

### STEP 7: Implement

Use **`/speckit.implement`** to execute the full task list:

```
/speckit.implement
```

The command validates prerequisites (constitution ✓, spec ✓, plan ✓, tasks ✓), then executes tasks in order — respecting dependencies, following TDD sequence, and providing progress updates throughout.

> **Note**: SpecForge will run local CLI commands (e.g., `pytest`, `npm`, `dotnet`) as part of implementation. Ensure required tools are installed on your machine.

</details>

---

## 🔍 Troubleshooting

### `specforge: command not found` after install

The `uv tool` bin directory may not be in your PATH. Run:

```bash
uv tool update-shell
```

Then restart your terminal, or manually add `~/.local/bin` (Linux/macOS) or `%USERPROFILE%\.local\bin` (Windows) to your PATH.

---

### Agent detected as `agnostic` when agent is installed

Your agent CLI may not be in PATH, or its binary name differs. Run:

```bash
specforge check
```

This shows which tools are found and which are missing with install hints. Use `--agent` to override auto-detection:

```bash
specforge init my-project --agent claude
```

---

### Git operations fail during `specforge init`

Git may not be installed, or the target directory may be in a restricted location. Either install git, or skip git initialization:

```bash
specforge init my-project --no-git
```

---

### `Error: Directory 'X' already exists`

The target directory exists. Use `--force` to scaffold into it without overwriting existing files:

```bash
specforge init my-project --force
```

---

### Preview changes before committing

Use `--dry-run` to see the full file tree without writing anything:

```bash
specforge init my-project --dry-run
```

---

## 💬 Support

For support, please open a [GitHub issue](https://github.com/your-org/specforge/issues/new). Bug reports, feature requests, and questions about spec-driven development are all welcome.

---

## 📄 License

This project is licensed under the terms of the MIT open source license. Please refer to the [LICENSE](./LICENSE) file for the full terms.

---
