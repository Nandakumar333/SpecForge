<div align="center">
    <h1>⚙️ SpecForge</h1>
    <h3><em>From One Prompt to Production-Ready Features.</em></h3>
</div>

<p align="center">
    <strong>An open source, AI-powered spec-driven development engine that takes a single natural-language prompt, auto-decomposes it into bounded features, and implements each one through isolated sub-agents governed by strict coding standards.</strong>
</p>

<p align="center">
    <em>Inspired by GitHub Spec Kit &nbsp;|&nbsp; Built for Enterprise AI Agents</em>
</p>

<p align="center">
    <a href="https://github.com/your-org/specforge/actions/workflows/release.yml"><img src="https://github.com/your-org/specforge/actions/workflows/release.yml/badge.svg" alt="Release"/></a>
    <a href="https://github.com/your-org/specforge/stargazers"><img src="https://img.shields.io/github/stars/your-org/specforge?style=social" alt="GitHub stars"/></a>
    <a href="https://github.com/your-org/specforge/blob/main/LICENSE"><img src="https://img.shields.io/github/license/your-org/specforge" alt="License"/></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
    <img src="https://img.shields.io/badge/install%20with-uv-violet" alt="Install with uv"/>
    <img src="https://img.shields.io/badge/version-1.0--March%202026-orange" alt="Version 1.0"/>
</p>

---

## Table of Contents

- [🤔 What is Spec-Driven Development?](#-what-is-spec-driven-development)
- [⚡ What Makes SpecForge Different](#-what-makes-specforge-different)
- [🚀 Get Started](#-get-started)
- [📂 Project Structure](#-project-structure)
- [📋 Per-Feature Pipeline](#-per-feature-pipeline)
- [🤖 Supported AI Agents](#-supported-ai-agents)
- [🔧 CLI Reference](#-cli-reference)
- [📖 Slash Commands](#-slash-commands)
- [🌟 Development Phases (Roadmap)](#-development-phases-roadmap)
- [🎯 Feature Decomposition Example](#-feature-decomposition-example)
- [🔒 Agent Instruction Prompts](#-agent-instruction-prompts)
- [⚠️ Edge Cases as First-Class Citizens](#️-edge-cases-as-first-class-citizens)
- [🔧 Prerequisites](#-prerequisites)
- [📋 Detailed Process](#-detailed-process)
- [🔍 Troubleshooting](#-troubleshooting)
- [💬 Support](#-support)
- [📄 License](#-license)

---

## 🤔 What is Spec-Driven Development?

Spec-Driven Development **flips the script** on traditional software development. For decades, code has been king — specifications were just scaffolding we built and discarded once the "real work" of coding began. Spec-Driven Development changes this: **specifications become executable**, directly generating working implementations rather than just guiding them.

SpecForge is the engine that makes this workflow concrete at enterprise scale. One prompt. Twelve features. Every feature fully specified, planned, and implemented — independently, in parallel, with strict coding governance enforced at every step.

```
"Create a webapp for PersonalFinance"
         │
         ▼
  App Analyzer Agent
  Identifies 12 bounded features
         │
         ▼
  Per-Feature Pipeline (×12)
  spec → research → data-model → plan → checklist → edge-cases → tasks
         │
         ▼
  Sub-Agent Executor (isolated per feature)
  Implements, tests, auto-fixes, commits
         │
         ▼
  Integration Orchestrator
  Merges features, resolves contracts, runs integration tests
         │
         ▼
  Production-Ready Application
```

---

## ⚡ What Makes SpecForge Different

| Feature | Spec Kit | SpecForge |
|---------|----------|-----------|
| Feature identification | Manual — you define each feature | **Automatic** — one-line prompt → AI decomposes into 10–15 bounded features |
| Sub-agent execution | Single agent, sequential | **Isolated sub-agents per feature** — no context window pollution, parallel execution |
| Coding governance | Templates and guidelines | **Agent Instruction Prompts** — hard constraints enforced at generation time, violations trigger rejection + re-generation |
| Edge cases | Listed in spec | **First-class artifact** — dedicated `edge-cases.md` per feature, analyzed before implementation |
| Industry standard bias | Follows common defaults | **Zero bias** — no assumptions about architecture, patterns, or libraries unless you define them |
| Auto-fix loop | None | **Built-in** — tests fail → agent fixes → re-tests (max 3 iterations before escalation) |

---

## 🚀 Get Started

### 1. Install SpecForge

#### Option 1: Persistent Installation (Recommended)

```bash
uv tool install specforge --from git+https://github.com/your-org/specforge.git
```

Then use the tool directly:

```bash
# Scaffold a new project
specforge init <PROJECT_NAME>

# Or initialize in an existing project
specforge init --here --agent claude

# Verify your environment
specforge check
```

To upgrade:

```bash
uv tool install specforge --force --from git+https://github.com/your-org/specforge.git
```

#### Option 2: One-time Usage

```bash
uvx --from git+https://github.com/your-org/specforge.git specforge init <PROJECT_NAME>
```

---

### 2. Establish project principles

Launch your AI assistant in the project directory. The `/specforge.*` commands are available after initialization.

Use **`/specforge.constitution`** to define the governance rules that every sub-agent will follow:

```
/specforge.constitution Create principles for a .NET microservices backend with Clean Architecture.
Functions must not exceed 30 lines. SOLID principles enforced. Result<T> pattern for all error handling.
No magic strings. 100% unit test coverage for domain logic.
```

---

### 3. Decompose your app into features

Use **`specforge decompose`** to have the App Analyzer Agent break your one-line description into bounded feature modules:

```bash
specforge decompose "Create a webapp for PersonalFinance"
```

SpecForge identifies 10–15 independent features, builds a dependency graph, and scaffolds a numbered directory for each one.

---

### 4. Run the per-feature pipeline

For each feature, run the full 7-phase pipeline:

```
/specforge.specify  →  /specforge.clarify  →  /specforge.plan  →  /specforge.tasks  →  /specforge.implement
```

Or let SpecForge orchestrate the entire pipeline automatically:

```bash
specforge implement --all --parallel
```

---

## 📂 Project Structure

SpecForge generates the following structure for every project:

```text
project-root/
├── .specforge/
│   ├── constitution.md                    # Project-wide governance
│   ├── memory/
│   │   ├── constitution.md                # Governance rules (AI-readable)
│   │   └── decisions.md                   # Architecture Decision Records
│   ├── prompts/                           # AGENT INSTRUCTION FILES
│   │   ├── architecture.prompts.md        # System-wide architecture rules
│   │   ├── backend.prompts.md             # Backend coding standards
│   │   ├── frontend.prompts.md            # Frontend coding standards
│   │   ├── database.prompts.md            # Database design rules
│   │   ├── security.prompts.md            # Security requirements
│   │   ├── testing.prompts.md             # Testing strategy & standards
│   │   ├── cicd.prompts.md                # CI/CD pipeline rules
│   │   └── api-design.prompts.md          # API contract rules
│   ├── features/
│   │   ├── 001-authentication/
│   │   │   ├── spec.md
│   │   │   ├── research.md
│   │   │   ├── data-model.md
│   │   │   ├── plan.md
│   │   │   ├── checklist.md
│   │   │   ├── edge-cases.md              # ← SpecForge exclusive
│   │   │   ├── tasks.md
│   │   │   └── contracts/
│   │   │       └── api-spec.json
│   │   ├── 002-accounts-wallets/
│   │   │   └── (same 7-artifact structure)
│   │   └── (all features)
│   ├── templates/
│   │   ├── spec-template.md
│   │   ├── plan-template.md
│   │   ├── tasks-template.md
│   │   ├── checklist-template.md
│   │   ├── research-template.md
│   │   ├── datamodel-template.md
│   │   └── edge-cases-template.md
│   └── scripts/
│       ├── decompose.sh
│       ├── generate-feature.sh
│       └── run-sub-agent.sh
├── src/                                   # Generated application code
│   ├── backend/
│   ├── frontend/
│   └── shared/
└── tests/
```

---

## 📋 Per-Feature Pipeline

Every feature — regardless of complexity — goes through an identical 7-phase pipeline before a single line of implementation code is written.

| Phase | Artifact | What It Contains |
|-------|----------|-----------------|
| 1 | `spec.md` | User stories (Given/When/Then), functional requirements, non-functional SLOs, explicit out-of-scope, edge case stubs |
| 2 | `research.md` | Technology options with pros/cons, library version verification, third-party service evaluation, security considerations |
| 3 | `data-model.md` | All entities with fields and types, relationships, value objects, index strategy, migration plan |
| 4 | `plan.md` | Architecture decisions, component breakdown, API endpoint design, frontend tree, constitution compliance gate |
| 5 | `checklist.md` | Quality gate — all items must pass before implementation begins |
| 6 | `edge-cases.md` | Concurrency, network failure, data boundaries, state machine gaps, security edge cases, UI edge cases |
| 7 | `tasks.md` | Dependency-ordered tasks with `[P]` parallel markers, test-before-implementation (TDD enforced), file paths per task |

> **Spec-First Rule**: No implementation begins until all 7 artifacts exist and the checklist gate passes.

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

**Auto-detection priority order**: `claude → copilot → gemini → cursor → windsurf → codex`

When `--agent` is not specified, SpecForge scans PATH in the order above and configures the first agent found.

---

## 🔧 CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `specforge init <project>` | Scaffold project with `.specforge/` directory, prompt files, templates, and agent config |
| `specforge decompose <description>` | Take a one-line app description and auto-split into bounded feature modules |
| `specforge check` | Verify all required tools (`git`, `python`, `uv`, agent CLI) are installed |
| `specforge implement --all` | Execute all features respecting the dependency graph |
| `specforge status` | Show progress dashboard across all features |

---

### `specforge init` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<project-name>` | Argument | — | Project directory name. Required unless `--here`. Allowed: `[a-zA-Z0-9_-]` |
| `--agent` | Option | (auto-detect) | AI agent: `claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex` |
| `--stack` | Option | (agnostic) | Tech stack for prompt defaults: `dotnet`, `nodejs`, `python`, `go`, `java` |
| `--here` | Flag | `False` | Scaffold `.specforge/` into current directory. Mutually exclusive with `<project-name>` |
| `--force` | Flag | `False` | Allow existing directory — preserves existing files, only adds missing ones |
| `--no-git` | Flag | `False` | Skip `git init`, `.gitignore`, and initial commit |
| `--dry-run` | Flag | `False` | Preview the full file tree without writing anything |

---

### Examples

```bash
# Scaffold a new project (auto-detects agent)
specforge init PersonalFinance

# Scaffold with specific agent and stack
specforge init PersonalFinance --agent claude --stack dotnet

# Decompose app description into features
specforge decompose "Create a webapp for PersonalFinance"

# Initialize in an existing project
specforge init --here --agent copilot

# Add missing .specforge/ files without overwriting existing ones
specforge init --here --force --agent gemini

# Preview what would be created
specforge init PersonalFinance --dry-run

# Skip git initialization
specforge init PersonalFinance --agent claude --no-git

# Check all prerequisites
specforge check

# Check prerequisites including a specific agent
specforge check --agent claude
```

---

## 📖 Slash Commands

After running `specforge init`, your AI agent has access to these slash commands:

### Core Commands

| Command | Description |
|---------|-------------|
| `/specforge.constitution` | Create or update project governing principles — the foundational governance for all sub-agents |
| `/specforge.specify` | Generate `spec.md` — user stories, functional requirements, NFRs, edge case stubs |
| `/specforge.clarify` | Identify and resolve underspecified areas before planning (recommended before `/specforge.plan`) |
| `/specforge.plan` | Generate `plan.md` — technical blueprint with architecture decisions and constitution gate |
| `/specforge.tasks` | Generate `tasks.md` — dependency-ordered, TDD-structured, parallelizable task list |
| `/specforge.implement` | Execute all tasks for a feature via isolated sub-agent |

### Quality & Validation Commands

| Command | Description |
|---------|-------------|
| `/specforge.analyze` | Cross-artifact consistency and coverage analysis — run after `/specforge.tasks`, before `/specforge.implement` |
| `/specforge.checklist` | Generate quality checklists that validate requirements completeness, clarity, and consistency |

---

## 🌟 Development Phases (Roadmap)

SpecForge is built in 4 phases. Phase 1 is complete.

### Phase 1 — Foundation ✅
CLI scaffold, constitution generator, 7 prompt files, 7 feature templates, git branching, slash commands.

### Phase 2 — Intelligence Layer
App Analyzer Agent, feature decomposer with dependency graph, edge-case analyzer, research agent, clarification engine.

### Phase 3 — Sub-Agent Engine
Isolated sub-agent execution per feature, parallel feature implementation, auto-fix loop (tests fail → fix → re-test), quality gate, cross-feature integration orchestrator, real-time progress dashboard.

### Phase 4 — Polish & Ecosystem
Multi-stack prompt plugins (Node.js, Python, Go, Java, React, Vue), brownfield mode (generate specs from existing code), auto-PR creation per feature, custom prompt authoring UI, VS Code extension.

---

## 🎯 Feature Decomposition Example

When you run `specforge decompose "Create a webapp for PersonalFinance"`, the App Analyzer identifies and orders these features:

| # | Feature | Depends On | Priority |
|---|---------|-----------|----------|
| 001 | Authentication & User Management | — | P0 — Critical Path |
| 002 | Accounts & Wallets | 001 | P0 — Critical Path |
| 003 | Transactions | 001, 002 | P0 — Critical Path |
| 004 | Budgeting | 001, 002, 003 | P1 — High |
| 005 | Investments | 001, 002 | P1 — High |
| 006 | Bills & Subscriptions | 001, 002, 003 | P1 — High |
| 007 | Financial Goals | 001, 002 | P2 — Medium |
| 008 | Reports & Analytics | 001–005 | P1 — High |
| 009 | Alerts & Notifications | 001 + any | P2 — Medium |
| 010 | Data Import & Bank Integration | 001, 002, 003 | P1 — High |
| 011 | AI Financial Advisor | 001–005, 008 | P2 — Medium |
| 012 | Admin & System Management | 001 | P1 — High |

Features with no shared dependencies (e.g., 002 and 012 both only need 001) are implemented **in parallel**.

---

## 🔒 Agent Instruction Prompts

The `.specforge/prompts/` directory contains 8 agent instruction files. These are **not guidelines** — they are hard constraints. Sub-agents that violate them have their output rejected and regenerated.

### What They Enforce

**`backend.prompts.md`** — microservice architecture, Clean Architecture layers, CQRS, SOLID principles, 30-line function limit, 300-line class limit, Result\<T\> pattern, no magic strings, structured logging.

**`frontend.prompts.md`** — Atomic Design component architecture, typed state management, no prop drilling beyond 2 levels, 150-line component limit, Zod schema validation, WCAG 2.1 AA accessibility, zero `any` TypeScript.

**`database.prompts.md`** — schema-first migrations, snake_case naming, indexed foreign keys, soft deletes with `IsDeleted + DeletedAt`, audit trail on every table, no N+1 queries, connection pooling.

**`security.prompts.md`** — JWT with refresh tokens (15 min / 7 day TTL), policy-based authorization, input validation at API boundary AND domain layer, no raw SQL concatenation, CORS origin whitelist, HSTS, no secrets in code.

**`testing.prompts.md`** — xUnit + Moq, one test class per production class, 80% line coverage minimum (100% for domain logic), `MethodName_StateUnderTest_ExpectedBehavior` naming, Testcontainers for integration tests, Stryker.NET mutation testing.

**`cicd.prompts.md`** — multi-stage Docker builds, non-root Alpine images, Terraform/Pulumi IaC, Conventional Commits, automatic rollback on health check failure, SemVer artifact versioning.

**`api-design.prompts.md`** — resource-oriented URLs with plural nouns, URL-based versioning (v1/v2), `{ data, errors, meta }` response envelope, RFC 7807 Problem Details for errors, OpenAPI spec generated from code, idempotency key support.

**`architecture.prompts.md`** — system-wide rules with highest precedence. When rules conflict across prompt files, `security.prompts.md > architecture.prompts.md > domain-specific files`.

### Tech Stack Adaptation

Prompt files ship with `.NET` defaults but adapt automatically to your stack. Specify `--stack python` and `FluentValidation → Pydantic`, `EF Core → SQLAlchemy`, `xUnit → pytest`. The same governance, applied to your language.

---

## ⚠️ Edge Cases as First-Class Citizens

Every feature in SpecForge has a dedicated `edge-cases.md` — generated before implementation begins, not discovered after. Categories covered:

- **Concurrency** — two users updating the same resource simultaneously
- **Network failure** — API timeouts, partial writes, third-party service down
- **Data boundaries** — empty lists, max values, special characters, encoding issues
- **State machine gaps** — session expiry mid-flow, interrupted transactions
- **Integration failures** — rate limiting, contract breaking changes, API deprecation
- **Security edge cases** — token replay, CSRF, concurrent sessions, privilege escalation
- **UI edge cases** — long text overflow, missing data, slow connections, keyboard navigation
- **Recovery** — partial implementation recovery, circular dependency detection, context window overflow

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
<summary>Click to expand the full step-by-step walkthrough</summary>

### Bootstrap your project

```bash
specforge init PersonalFinance --agent claude --stack dotnet
```

SpecForge will:
1. Create the full `.specforge/` directory structure
2. Render all Jinja2 templates with your project name, agent, and stack
3. Populate all 8 agent instruction prompt files with stack-appropriate rules
4. Initialize a git repository and make the initial commit: `chore: init specforge scaffold`
5. Print a summary of all created files and suggested next steps

Preview without writing:
```bash
specforge init PersonalFinance --dry-run
```

---

### STEP 1: Establish project principles

Open your AI coding agent in the project directory and run `/specforge.constitution`:

```
/specforge.constitution Create principles for a .NET microservices platform. Clean Architecture with Domain/Application/Infrastructure/API layers. CQRS for all commands and queries. Functions ≤30 lines, classes ≤300 lines. Result<T> for all business logic errors — no exceptions for control flow. 80% minimum test coverage, 100% for domain layer.
```

This creates `.specforge/memory/constitution.md` — the document that gates every planning, implementation, and review step.

---

### STEP 2: Decompose your app

Run the App Analyzer to identify features:

```bash
specforge decompose "Create a webapp for PersonalFinance"
```

The agent identifies bounded contexts, extracts features, builds a dependency graph, and scaffolds a numbered `features/` directory for each one. Features with no shared dependencies are flagged for parallel execution.

---

### STEP 3: Run the per-feature pipeline

For each feature, work through the 7-phase pipeline:

**Specify:**
```
/specforge.specify 001-authentication
```
Produces `spec.md` with user stories (Given/When/Then), functional requirements, NFR SLOs, and edge case stubs.

**Clarify:**
```
/specforge.clarify
```
Resolves underspecified areas through structured Q&A — answers recorded directly in the spec.

**Plan:**
```
/specforge.plan The backend uses ASP.NET Core 8 with PostgreSQL via EF Core. JWT authentication with refresh tokens.
```
Produces `plan.md`, `research.md`, `data-model.md`, `contracts/api-spec.json`, and `quickstart.md`.

**Validate:**
```
/specforge.checklist 001-authentication
```
Generates and runs the quality gate. All items must pass before tasks are generated.

**Generate tasks:**
```
/specforge.tasks
```
Produces `tasks.md` with TDD-ordered tasks, `[P]` parallel markers, exact file paths, and conventional commit labels per task.

**Implement:**
```
/specforge.implement
```
The sub-agent loads constitution + applicable prompt files + this feature's spec artifacts — nothing else. It executes tasks in order, runs tests after each task, and auto-fixes failures (max 3 iterations).

---

### STEP 4: Run all features

Once all features are specified and planned, implement them respecting the dependency graph:

```bash
specforge implement --all --parallel
```

Features in the same dependency phase run concurrently. The integration orchestrator merges them, resolves shared contracts, and runs end-to-end integration tests.

---

### STEP 5: Check progress

```bash
specforge status
```

Shows a real-time dashboard across all features: `specifying → planning → implementing → testing → complete`.

</details>

---

## 🔍 Troubleshooting

### `specforge: command not found` after install

```bash
uv tool update-shell
```

Restart your terminal, or add `~/.local/bin` (Linux/macOS) or `%USERPROFILE%\.local\bin` (Windows) to PATH.

---

### Agent detected as `agnostic` when agent is installed

```bash
specforge check
```

Shows which tools are found and which are missing with install hints. Override auto-detection:

```bash
specforge init my-project --agent claude
```

---

### Git operations fail during `specforge init`

Use `--no-git` to skip git initialization:

```bash
specforge init my-project --no-git
```

---

### `Error: Directory 'X' already exists`

Use `--force` to scaffold into an existing directory without overwriting files:

```bash
specforge init my-project --force
```

---

### Sub-agent violates prompt file rules

Sub-agents that generate code violating agent instruction prompts (e.g., function exceeds 30 lines, missing type hints) have their output automatically flagged. The agent is instructed to regenerate the affected section. After 3 failed iterations, the task is escalated with a diagnostic report for human review.

---

### Preview changes before committing

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

<div align="center">
    <em>SpecForge — Spec-First. Agent-Governed. Production-Ready.</em>
</div>
