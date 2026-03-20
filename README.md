<div align="center">

# ⚙️ SpecForge

### *From One Prompt to Production-Ready Features.*

**An open-source, AI-powered spec-driven development engine that takes a single natural-language prompt, auto-decomposes it into bounded features, and implements each one through isolated sub-agents governed by strict coding standards.**

*Inspired by GitHub Spec Kit &nbsp;|&nbsp; Built for Enterprise AI Agents*

[![Release](https://github.com/Nandakumar333/SpecForge/actions/workflows/release.yml/badge.svg)](https://github.com/Nandakumar333/SpecForge/actions/workflows/release.yml)
[![GitHub stars](https://img.shields.io/github/stars/Nandakumar333/SpecForge?style=social)](https://github.com/Nandakumar333/SpecForge/stargazers)
[![License](https://img.shields.io/github/license/Nandakumar333/SpecForge)](https://github.com/Nandakumar333/SpecForge/blob/main/LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Install with uv](https://img.shields.io/badge/install%20with-uv-violet)
![Version 0.1.0](https://img.shields.io/badge/version-0.1.0--March%202026-orange)

---

**One prompt. Dozens of features. Each one fully spec'd, planned, and implemented — independently, in parallel, with strict governance at every step.**

[Quick Start](#-quick-start) · [How It Works](#-how-it-works) · [CLI Reference](#-cli-reference) · [Why SpecForge?](#-why-specforge) · [Troubleshooting](#-troubleshooting)

</div>

---

## 📖 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [💡 What is Spec-Driven Development?](#-what-is-spec-driven-development)
- [🔥 Why SpecForge?](#-why-specforge)
- [⚙️ How It Works](#️-how-it-works)
- [🤖 Supported AI Agents (25+)](#-supported-ai-agents-25)
- [🔧 CLI Reference](#-cli-reference)
- [📖 Slash Commands](#-slash-commands)
- [📂 Project Structure](#-project-structure)
- [🔒 Governance & Coding Standards](#-governance--coding-standards)
- [🧪 Quality Validation (11 Checkers)](#-quality-validation-11-checkers)
- [⚡ Parallel Execution](#-parallel-execution)
- [🔌 Plugin System](#-plugin-system)
- [🏗️ Architecture & Roadmap](#️-architecture--roadmap)
- [📋 Step-by-Step Walkthrough](#-step-by-step-walkthrough)
- [🔍 Troubleshooting](#-troubleshooting)
- [💬 Support & License](#-support--license)

---

## 🚀 Quick Start

### Prerequisites

| Tool | Required For |
|------|-------------|
| [Python 3.11+](https://www.python.org/downloads/) | Core runtime |
| [uv](https://docs.astral.sh/uv/) | Package management & install |
| [Git](https://git-scm.com/downloads) | Version control |
| A [supported AI agent](#-supported-ai-agents-25) | Code generation |
| [Docker](https://docs.docker.com/get-docker/) | Microservice architecture only |

### Install

```bash
# Install globally (recommended)
uv tool install specforge --from git+https://github.com/Nandakumar333/SpecForge.git

# Or run once without installing
uvx --from git+https://github.com/Nandakumar333/SpecForge.git specforge init <PROJECT_NAME>
```

### Create Your First Project — One Command

```bash
specforge forge "Create a webapp for PersonalFinance"
```

That's it. One command handles **everything**: project init, feature decomposition, 7-phase spec generation for every service (in parallel), validation, and a completion report.

> **💡 Already have a project?** Run `forge` from an existing `.specforge/` directory and it picks up where you left off with `--resume`.

<details>
<summary><strong>Step-by-step alternative (full control)</strong></summary>

```bash
# 1️⃣ Scaffold a new project
specforge init MyApp --agent claude

# 2️⃣ Verify your environment
specforge check

# 3️⃣ Decompose your app into features
specforge decompose "Create a webapp for PersonalFinance"

# 4️⃣ Implement everything
specforge implement
```

</details>

> **💡 Tip:** Run `specforge init` without `--agent` to get an interactive agent selection menu with 25+ options.

<details>
<summary><strong>🔄 Upgrade to latest version</strong></summary>

```bash
uv tool install specforge --force --from git+https://github.com/Nandakumar333/SpecForge.git
```

</details>

---

## 💡 What is Spec-Driven Development?

Traditional development treats specifications as throwaway scaffolding — you write them, then discard them once coding begins. **Spec-Driven Development flips this entirely**: specifications become the executable source of truth, directly generating working implementations.

```
specforge forge "Create a webapp for PersonalFinance"
         │
         ▼
  🔧 Auto-Init — scaffold project, detect agent & stack
         │
         ▼
  🧠 App Analyzer — identifies 12 bounded features
         │
         ▼
  📋 Per-Feature Pipeline (×12, in parallel)
  spec → research → data-model → edge-cases → plan → checklist → tasks
         │
         ▼
  ✅ Validation — verify all artifacts exist per service
         │
         ▼
  📊 Completion Report — summary with per-service status
```

> **No feature begins implementation until all 7 specification artifacts exist and the quality gate passes.** This isn't a suggestion — it's enforced by the engine.

---

## 🔥 Why SpecForge?

### How SpecForge Compares

| Capability | Traditional Spec Kit | ✨ SpecForge |
|-----------|---------------------|-------------|
| **Feature identification** | Manual — you define each feature | **Automatic** — one prompt → 8–15 domain-aware features |
| **Architecture awareness** | Single mode | **Three architectures** — monolithic, microservice, modular monolith |
| **Agent execution** | Single agent, sequential | **Isolated sub-agents per feature** — no context pollution |
| **Coding governance** | Templates & guidelines | **7-domain governance prompts** with conflict detection |
| **Edge cases** | Listed in spec | **First-class artifact** — architecture-aware, severity-scored |
| **Quality validation** | None | **11 pluggable checkers** — build, lint, test, coverage, secrets, and more |
| **Auto-fix** | None | **Built-in** — categorized fix prompts, regression detection, auto-revert |
| **Task generation** | Manual task lists | **DAG-based dependency ordering** with effort estimates |
| **Multi-service orchestration** | None | **Phased execution** with contract verification |
| **Industry bias** | Follows common defaults | **Zero bias** — no assumptions unless you define them |

### Key Highlights

- 🎯 **One prompt → Full application** — Describe your app in one sentence; SpecForge does the rest
- 🏛️ **Architecture-aware** — Monolithic, microservice, or modular monolith with architecture-specific artifacts at every phase
- 🤖 **25+ AI agents supported** — Claude, Copilot, Gemini, Cursor, Windsurf, Codex, and many more
- 🔒 **Governance enforced** — 7-domain coding standards with threshold conflict detection
- ⚡ **Parallel execution** — Concurrent spec generation and dependency-wave implementation
- 🧪 **Quality gates built-in** — 11 automated checkers with auto-fix and regression prevention
- 📦 **Resumable everything** — Interrupt and resume at any point; state is always persisted
- 🔌 **Extensible** — Plugin system for custom agents and tech stacks

---

## ⚙️ How It Works

Every feature goes through an identical **7-phase pipeline** before a single line of implementation code is written:

### The 7-Phase Pipeline

| Phase | Artifact | What Gets Generated |
|:-----:|----------|-------------------|
| 1 | `spec.md` | User stories (Given/When/Then), functional requirements, non-functional SLOs, out-of-scope boundaries |
| 2 | `research.md` | Technology options with pros/cons, library verification, structured findings (RESOLVED / UNVERIFIED / BLOCKED / CONFLICTING) |
| 3 | `data-model.md` | Entities, relationships, value objects, index strategy, migration plan — scoped by architecture |
| 4 | `edge-cases.md` | Architecture-aware edge cases with deterministic severity scoring and YAML frontmatter |
| 5 | `plan.md` | Architecture decisions, component blueprint, API design, constitution compliance gate |
| 6 | `checklist.md` | Quality gate — all items must pass before implementation begins |
| 7 | `tasks.md` | Dependency-ordered tasks with TDD, effort estimates (S/M/L/XL), governance references |

### Feature Decomposition Example

When you run `specforge decompose "Create a webapp for PersonalFinance"`, SpecForge executes:

**Step 1 — Architecture Decision Gate**
```
? Which architecture pattern for this project?
  ❯ 1. Monolithic — All features in a single deployable unit
    2. Microservice — Features mapped to independent services
    3. Modular Monolith — Single deploy with strict module boundaries
```

**Step 2 — Automatic Feature Identification**

The domain analyzer matches "PersonalFinance" to the **finance** domain pattern and generates:

| # | Feature | Category | Priority |
|---|---------|----------|----------|
| 001 | Authentication & User Management | foundation | P0 |
| 002 | Accounts & Wallets | core | P0 |
| 003 | Transactions | core | P0 |
| 004 | Budgeting | core | P1 |
| 005 | Investments | core | P1 |
| 006 | Bills & Subscriptions | supporting | P1 |
| 007 | Financial Goals | supporting | P2 |
| 008 | Reports & Analytics | supporting | P1 |
| 009 | Alerts & Notifications | integration | P2 |
| 010 | Data Import & Bank Integration | integration | P1 |
| 011 | AI Financial Advisor | supporting | P3 |
| 012 | Admin & System Management | admin | P1 |

**Step 3 — Service Mapping** *(microservice only)*

12 features → 8 services via affinity scoring:

| Service | Features | Rationale |
|---------|----------|-----------|
| Identity Service | 001 | Foundation — every other service depends on it |
| Ledger Service | 002, 003 | Shared bounded context — accounts and transactions access same data |
| Planning Service | 004, 006, 007 | All are future financial planning with shared domain vocabulary |
| Portfolio Service | 005 | Specialized domain with unique external dependencies |
| Analytics Service | 008, 011 | Both read-heavy consumers with same data pipeline |
| Notification Service | 009 | Purely async, multi-channel, different scaling profile |
| Integration Service | 010 | External API dependency with rate limiting and circuit-breakers |
| Admin Service | 012 | System management with different access control |

> **Output:** `manifest.json` + `communication-map.md` (Mermaid diagram) + feature directories under `.specforge/features/`

---

## 🤖 Supported AI Agents (25+)

SpecForge automatically generates command files in each agent's native discovery location.

| Agent | Commands Directory | Format | Auto-Detect |
|-------|-------------------|--------|:-----------:|
| [Claude Code](https://www.anthropic.com/claude-code) | `.claude/commands/` | Markdown | ✅ Priority 1 |
| [GitHub Copilot](https://github.com/features/copilot) | `.github/prompts/` | `.prompt.md` | ✅ Priority 2 |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `.gemini/commands/` | TOML | ✅ Priority 3 |
| [Cursor](https://cursor.com) | `.cursor/commands/` | Markdown | ✅ Priority 4 |
| [Windsurf](https://windsurf.com) | `.windsurf/commands/` | Markdown | ✅ Priority 5 |
| [Codex CLI](https://github.com/openai/codex) | `.codex/commands/` | Markdown | ✅ Priority 6 |
| [Kiro](https://kiro.dev) | `.kiro/commands/` | Markdown | — |
| [Roo Code](https://roo.dev) | `.roo/commands/` | Markdown | — |
| [Amp](https://amp.dev), [Trae](https://trae.ai), [Mistral](https://mistral.ai), [Qwen](https://qwen.ai), + 15 more | `.specforge/commands/` | Markdown | — |
| Generic (any agent) | `commands/` (customizable) | Markdown | Fallback |

> **How agent selection works:** Without `--agent`, SpecForge shows an interactive selection prompt. In CI/non-interactive environments, it auto-detects from PATH using the priority order above.

---

## 🔧 CLI Reference

### All Commands at a Glance

| Command | What It Does |
|---------|-------------|
| `specforge forge <description>` | **One-command full pipeline** — init → decompose → spec gen → validate → report |
| `specforge init <project>` | Scaffold a new project with `.specforge/`, governance prompts, templates, and agent config |
| `specforge check` | Verify all required tools are installed (`git`, `python`, `uv`, agent CLI) |
| `specforge validate-prompts` | Detect threshold conflicts across governance prompt files |
| `specforge decompose <description>` | Break your app description into features and services |
| `specforge specify <target>` | Run the full 7-phase spec pipeline for a feature/service |
| `specforge clarify <target>` | Detect ambiguities and resolve them via interactive Q&A |
| `specforge research <target>` | Generate structured technology research findings |
| `specforge edge-cases <target>` | Generate architecture-aware edge case analysis |
| `specforge pipeline-status [target]` | Show pipeline phase status per service/module |
| `specforge implement [target]` | Execute implementation with quality gates and auto-fix |
| `specforge status [target]` | View project-wide status dashboard with progress metrics |
| `specforge plugins` | List installed agent and stack plugins |

### `specforge forge` — One-Command Full Pipeline

```bash
specforge forge "<description>" [OPTIONS]
```

Runs the entire SpecForge pipeline end-to-end with zero human interaction: auto-init → decompose → parallel 7-phase spec generation → validation → completion report.

| Option | Default | Description |
|--------|---------|-------------|
| `--arch <pattern>` | `monolithic` | Architecture (`monolithic`, `microservice`, `modular-monolith`) |
| `--stack <name>` | `auto` | Tech stack (`python`, `dotnet`, `nodejs`, `go`, `java`, `auto`) |
| `--max-parallel <n>` | `4` | Max concurrent workers for spec generation |
| `--dry-run` | — | Generate `.prompt.md` files only — no LLM calls |
| `--resume` | — | Resume from last saved state (mutually exclusive with `--force`) |
| `--force` | — | Overwrite existing forge state |
| `--skip-init` | — | Skip auto-init — fail if `.specforge/` doesn't exist |

**Exit codes:** `0` = all services succeeded, `1` = partial failure, `2` = total failure

```bash
# Basic usage
specforge forge "Create a personal finance app"

# Microservice with 8 parallel workers
specforge forge "Build an e-commerce platform" --arch microservice --max-parallel 8

# Preview prompts without calling the LLM
specforge forge "Todo app" --dry-run

# Resume after interruption
specforge forge --resume
```

### `specforge init` — Scaffold a Project

```bash
specforge init <project-name> [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--agent <name>` | Interactive / auto-detect | AI agent (`claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex`, etc.) |
| `--stack <name>` | Auto-detect | Tech stack (`dotnet`, `nodejs`, `python`, `go`, `java`) |
| `--arch <pattern>` | `monolithic` | Architecture (`monolithic`, `microservice`, `modular-monolith`) |
| `--here` | — | Scaffold into current directory instead of creating new one |
| `--force` | — | Allow existing directory — preserves customized files (SHA-256 check) |
| `--no-git` | — | Skip git initialization |
| `--dry-run` | — | Preview the file tree without writing anything |

### `specforge decompose` — Feature Decomposition

```bash
specforge decompose "<description>" [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--arch <pattern>` | Auto | Architecture: `monolithic`, `microservice`, `modular-monolith` |
| `-i`, `--interactive` | — | Enable interactive prompts (default: auto with parallel) |
| `--sequential` | — | Run spec pipelines one at a time |
| `--strict` | — | Stop on first failure |
| `--remap <arch>` | — | Re-map existing features to a new architecture |

### `specforge specify` — Spec Pipeline

```bash
specforge specify <target> [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--force` | — | Reset all phases and re-run from scratch |
| `--from <phase>` | — | Start from a specific phase (`spec`, `research`, `datamodel`, `edgecase`, `plan`, `checklist`, `tasks`) |

### `specforge implement` — Code Generation

```bash
specforge implement [target] [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--resume` | — | Resume from last completed task |
| `--sequential` | — | Run services one at a time |
| `--strict` | — | Stop on first failure |

<details>
<summary><strong>📌 More Command Options</strong></summary>

#### `specforge clarify`
```bash
specforge clarify <target> [--report]
```
- `--report` — Generate non-interactive report instead of interactive Q&A

#### `specforge status`
```bash
specforge status [target]
```
- `[target]` — Optional service slug for drill-down view

#### `specforge plugins`
```bash
specforge plugins [--agents] [--stacks]
```
- `--agents` — List only agent plugins
- `--stacks` — List only stack plugins

</details>

### Usage Examples

```bash
# ── One-Command Pipeline (recommended) ──
specforge forge "Create a webapp for PersonalFinance"                    # Full auto pipeline
specforge forge "Build an e-commerce platform" --arch microservice       # Microservice arch
specforge forge "Todo app" --dry-run                                     # Preview prompts only
specforge forge --resume                                                 # Resume interrupted run

# ── Project Setup ──
specforge init PersonalFinance                          # Interactive agent selection
specforge init PersonalFinance --agent claude --stack dotnet  # Specific agent + stack
specforge init --here --agent copilot                   # Init in current directory
specforge init PersonalFinance --dry-run                # Preview what gets created
specforge init --here --force --agent gemini            # Add missing files only

# ── Feature Decomposition ──
specforge decompose "Create a webapp for PersonalFinance"         # Auto mode (parallel)
specforge decompose "Create a webapp for PersonalFinance" -i      # Interactive mode
specforge decompose "Create a personal finance app" --arch microservice  # Pre-select arch

# ── Spec Pipeline ──
specforge specify ledger-service                        # Full 7-phase pipeline
specforge specify ledger-service --from edgecase        # Start from specific phase
specforge clarify ledger-service                        # Interactive Q&A
specforge clarify ledger-service --report               # Non-interactive report
specforge research ledger-service                       # Standalone research
specforge edge-cases ledger-service                     # Standalone edge case analysis

# ── Implementation ──
specforge implement                                     # All services (parallel waves)
specforge implement ledger-service                      # Single service
specforge implement --resume                            # Resume interrupted work
specforge implement --strict                            # Stop on first failure

# ── Monitoring ──
specforge status                                        # Project-wide dashboard
specforge pipeline-status                               # Pipeline status overview
specforge pipeline-status ledger-service                # Specific service status
specforge plugins                                       # List installed plugins
specforge check                                         # Verify environment
specforge validate-prompts                              # Check governance conflicts
```

---

## 📖 Slash Commands

After `specforge init`, your AI agent has access to these slash commands through auto-generated command files:

| Command | Description |
|---------|-------------|
| `/specforge.decompose` | Decompose an application into features |
| `/specforge.specify` | Generate `spec.md` — user stories, requirements, NFRs |
| `/specforge.research` | Generate `research.md` — structured technology findings |
| `/specforge.plan` | Generate `plan.md` — technical blueprint with architecture decisions |
| `/specforge.tasks` | Generate `tasks.md` — dependency-ordered, TDD task list |
| `/specforge.implement` | Execute tasks via isolated sub-agent with auto-fix |
| `/specforge.status` | Show project-wide status dashboard |
| `/specforge.check` | Run quality checks against governance rules |
| `/specforge.analyze` | Cross-artifact consistency analysis |
| `/specforge.checklist` | Generate quality gate checklists |
| `/specforge.edge-cases` | Generate architecture-aware edge case analysis |

---

## 📂 Project Structure

After running `specforge init`, your project looks like this:

```
project-root/
├── .claude/commands/                  # Agent-specific commands (varies by agent)
│   ├── specforge.decompose.md        #   Slash command files (8 total)
│   ├── specforge.specify.md
│   ├── specforge.implement.md
│   └── ...
│
├── .specforge/
│   ├── config.json                   # Agent, stack, and project settings
│   ├── constitution.md               # Project-wide governance principles
│   ├── manifest.json                 # Architecture + feature→service mapping
│   ├── communication-map.md          # Mermaid service dependency diagram
│   │
│   ├── memory/
│   │   ├── constitution.md           # Governance rules (AI-readable)
│   │   └── decisions.md              # Architecture Decision Records
│   │
│   ├── prompts/                      # 7 GOVERNANCE PROMPT FILES
│   │   ├── architecture.prompts.md   # System-wide architecture rules
│   │   ├── backend.prompts.md        # Backend coding standards
│   │   ├── frontend.prompts.md       # Frontend standards
│   │   ├── database.prompts.md       # Database design rules
│   │   ├── security.prompts.md       # Security requirements
│   │   ├── testing.prompts.md        # Testing strategy & standards
│   │   └── cicd.prompts.md           # CI/CD pipeline rules
│   │
│   ├── features/                     # Created by `specforge decompose`
│   │   ├── 001-authentication/
│   │   │   ├── spec.md               # User stories & requirements
│   │   │   ├── research.md           # Technology research
│   │   │   ├── data-model.md         # Entities & relationships
│   │   │   ├── edge-cases.md         # Edge case analysis
│   │   │   ├── plan.md               # Architecture blueprint
│   │   │   ├── checklist.md          # Quality gate
│   │   │   ├── tasks.md              # Implementation task list
│   │   │   └── contracts/            # API specs, event schemas
│   │   └── 002-accounts-wallets/
│   │       └── ... (same structure)
│   │
│   └── templates/                    # Jinja2 pipeline templates
│
├── src/                              # Generated application code
└── tests/                            # Generated tests
```

> **📝 Note:** Commands directory varies by agent — `.claude/commands/` for Claude, `.github/prompts/` for Copilot, `.gemini/commands/` for Gemini (TOML format), etc.

> **📝 Note:** Stack-specific governance files use `{domain}.{stack}.prompts.md` format (e.g., `backend.dotnet.prompts.md`).

---

## 🔒 Governance & Coding Standards

SpecForge includes **7 governance prompt files** that act as **hard constraints** — not guidelines. Sub-agents that violate them have their output rejected and regenerated automatically.

### The 7 Governance Domains

| # | Domain | File | What It Enforces |
|:-:|--------|------|-----------------|
| 1 | **Architecture** | `architecture.prompts.md` | Clean Architecture layers, SOLID principles, dependency direction, no circular deps |
| 2 | **Security** | `security.prompts.md` | JWT with refresh tokens, input validation, no raw SQL, CORS whitelist, HSTS |
| 3 | **Backend** | `backend.prompts.md` | 30-line function limit, 300-line class limit, Result\<T\> pattern, structured logging |
| 4 | **Frontend** | `frontend.prompts.md` | Atomic Design, typed state management, 150-line components, WCAG 2.1 AA |
| 5 | **Database** | `database.prompts.md` | Schema-first migrations, indexed FKs, soft deletes, audit trails, no N+1 queries |
| 6 | **Testing** | `testing.prompts.md` | 80% coverage minimum (100% for domain), test naming conventions, integration containers |
| 7 | **CI/CD** | `cicd.prompts.md` | Multi-stage Docker builds, non-root Alpine images, IaC, Conventional Commits |

> **Precedence rule:** When rules conflict, higher-numbered domains yield to lower-numbered ones. Architecture (1) always wins; Security (2) overrides Backend (3), etc.

### Conflict Detection

```bash
specforge validate-prompts
```

Automatically detects threshold conflicts between governance files. For example, if `backend.prompts.md` sets max function length to 30 lines but `testing.prompts.md` sets it to 50, the validator flags it.

### Stack Adaptation

Governance prompts automatically adapt to your tech stack. Set `--stack python` during `specforge init` and rules translate accordingly:
- `FluentValidation` → **Pydantic**
- `EF Core` → **SQLAlchemy**
- `xUnit` → **pytest**

Same governance rules, applied to your language and ecosystem.

---

## 🧪 Quality Validation (11 Checkers)

Every piece of generated code passes through a pluggable quality validation system before being committed.

### Standard Checkers (All Architectures)

| Checker | What It Validates |
|---------|------------------|
| 🔨 **Build** | Project compiles without errors |
| 🧹 **Lint** | Code passes ruff/eslint with structured output |
| ✅ **Test** | All tests pass |
| 📊 **Coverage** | Meets threshold (default: 80%, domain logic: 100%) |
| 📏 **Line Limit** | Functions ≤30 lines, classes ≤200 lines (via AST analysis) |
| 🔑 **Secrets** | No hardcoded secrets (regex + entropy detection) |
| 📝 **TODO Scan** | No unresolved TODO/FIXME/HACK markers |
| 📋 **Prompt Rules** | Compliance with governance thresholds |

### Architecture-Specific Checkers

| Checker | Architecture | What It Validates |
|---------|-------------|------------------|
| 🐳 **Docker Build** | Microservice | Docker image builds successfully |
| 💓 **Docker Health** | Microservice | Container starts and passes health check |
| 📜 **Contract Tests** | Microservice | Pact consumer tests pass |
| 🔗 **URL Detection** | Microservice | No hardcoded service URLs |
| 🔲 **Interface Validation** | Microservice | Proto files compile, event schemas validate |
| 🚧 **Boundary** | Modular-monolith | No cross-module direct DB access |
| 🗄️ **Migration Safety** | Modular-monolith | Shared migrations respect module boundaries |

### Auto-Fix with Regression Prevention

When quality checks fail, SpecForge doesn't just say "fix it" — it categorizes the error and generates a **targeted fix prompt**:

```
Quality Check → FAIL → Categorize Error → Targeted Fix Prompt
     → Agent Applies Fix → Re-Check
         → PASS → Commit ✓
         → REGRESSION → Auto-Revert → Next Attempt
         → SAME ERROR → Next Attempt (max 3)
         → EXHAUSTED → Diagnostic Report for Human Review
```

---

## ⚡ Parallel Execution

SpecForge supports concurrent execution to dramatically reduce wall-clock time.

### Parallel Spec Generation

```bash
specforge decompose "Personal Finance App"
```

Discovers services and generates all 7-phase spec artifacts concurrently across services using a configurable worker pool.

### Parallel Implementation

```bash
specforge implement
```

Services are grouped into **dependency waves** via topological sort. Within each wave, independent services run concurrently:

```
Wave 0: identity-service, admin-service     ← parallel (no deps)
Wave 1: ledger-service, portfolio-service   ← parallel (depend on Wave 0)
Wave 2: analytics-service                   ← depends on Wave 1
```

### Architecture-Aware Parallelism

| Architecture | Strategy |
|---|---|
| **Microservice** | Topological dependency waves from service graph |
| **Monolithic** | Single wave — all modules run in parallel |
| **Modular Monolith** | Dependency waves if communication entries exist, otherwise single wave |

### Error Handling

| Mode | Behavior |
|------|----------|
| **Resilient** (default) | Failed services don't block unrelated ones |
| **Fail-fast** (`--strict`) | First failure cancels everything |
| **Resume** | Re-running skips completed services |
| **SIGINT** | Graceful shutdown — completed work is preserved |

### Configuration

Add to `.specforge/config.json`:

```json
{
  "parallel": {
    "max_workers": 4
  }
}
```

---

## 🔌 Plugin System

SpecForge is extensible through **agent plugins** and **stack plugins**, discovered at runtime.

### Agent Plugins (25+)

All major AI coding agents are supported with a unified `AgentPlugin` interface:

| Plugin | Purpose |
|--------|---------|
| Claude, Copilot, Gemini, Cursor, Windsurf, Codex | Primary agents with auto-detect |
| Kiro, Roo Code, Amp, Trae, Mistral, Qwen | Additional agents |
| Generic | Fallback — copy-paste flow for any agent |

### Stack Plugins

| Stack | Build | Lint | Test | Docker Base |
|-------|-------|------|------|-------------|
| **dotnet** | `dotnet build` | StyleCop | `dotnet test` | `mcr.microsoft.com/dotnet/aspnet:8` |
| **nodejs** | `npm run build` | ESLint | `npm test` | `node:20-alpine` |
| **python** | `python -m pytest` | Ruff | `pytest` | `python:3.11-slim` |

### Extending with Custom Plugins

Implement the `AgentPlugin` or `StackPlugin` protocol:

```python
# Custom Agent Plugin
class MyAgentPlugin(AgentPlugin):
    def execute_task(self, prompt: str, context: dict) -> str: ...
    def configure(self) -> Result[str]: ...

# Custom Stack Plugin
class MyStackPlugin(StackPlugin):
    def get_build_command(self) -> str: ...
    def get_lint_command(self) -> str: ...
    def get_test_command(self) -> str: ...
```

```bash
# List all installed plugins
specforge plugins
specforge plugins --agents   # Agent plugins only
specforge plugins --stacks   # Stack plugins only
```

---

## 🏗️ Architecture & Roadmap

SpecForge is built as **15 incrementally developed features**, each fully specified and implemented following its own spec-first methodology.

### Feature Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SpecForge Feature Architecture                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FOUNDATION                                                          │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │
│  │ 001 CLI   │ │ 002 Templ │ │ 003 Gov.  │ │ 013 Plugin│           │
│  │ Init      │ │ Engine    │ │ Prompts   │ │ System    │           │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘           │
│        │              │             │             │                   │
│  PIPELINE                                                            │
│  ┌─────▼─────┐ ┌───────────┐ ┌─────▼─────┐      │                   │
│  │ 004 Arch  │◄┤ 006 Rsch  │ │ 007 Edge  │      │                   │
│  │ Decompose │ │ & Clarify │ │ Cases     │      │                   │
│  └─────┬─────┘ └───────────┘ └─────┬─────┘      │                   │
│  ┌─────▼─────┐                     │             │                   │
│  │ 005 Spec  │◄────────────────────┘             │                   │
│  │ Pipeline  │                                   │                   │
│  └─────┬─────┘                                   │                   │
│  ┌─────▼─────┐                                   │                   │
│  │ 008 Task  │                                   │                   │
│  │ Generation│                                   │                   │
│  └─────┬─────┘                                   │                   │
│                                                                      │
│  EXECUTION                                                           │
│  ┌─────▼─────┐ ┌───────────┐                     │                   │
│  │ 009 Sub-  │◄┤ 010 Qual. │◄────────────────────┘                   │
│  │ Agent Exec│ │ Validation│                                         │
│  └─────┬─────┘ └───────────┘                                         │
│                                                                      │
│  ORCHESTRATION & MONITORING                                          │
│  ┌─────▼─────┐ ┌───────────┐ ┌───────────┐                           │
│  │ 011 Impl  │ │ 012 Status│ │ 016 Paral.│                           │
│  │ Orchestr. │ │ Dashboard │ │ Execution │                           │
│  └───────────┘ └───────────┘ └─────┬─────┘                           │
│                                                                      │
│  ONE-COMMAND                                                         │
│  ┌─────────────────────────────────▼─────┐                           │
│  │ 017 Forge — Full Pipeline Orchestrator│                           │
│  │ init → decompose → spec → validate    │                           │
│  └───────────────────────────────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Development Phases

| Phase | Status | Features | Highlights |
|:-----:|:------:|----------|-----------|
| 1 | ✅ | 001 CLI Scaffold, 002 Template Engine | `specforge init`, Jinja2 templates, agent detection |
| 2 | ✅ | 003 Governance Prompts, 004 Decomposer | 7-domain prompts, architecture-aware decomposition |
| 3 | ✅ | 005 Spec Pipeline, 006 Research, 007 Edge Cases, 008 Tasks | Full 7-phase pipeline with research, edge cases, task generation |
| 4 | ✅ | 009 Sub-Agent Executor, 010 Quality Validation | Context-isolated execution, 11 quality checkers, auto-fix |
| 5 | ✅ | 011 Implementation Orchestrator | Phased execution, contract verification, integration testing |
| 6 | ✅ | 012 Dashboard, 013 Plugins, 014 Agent Selection | Rich status dashboard, 25+ agent plugins, interactive selection |
| 7 | ✅ | 016 Parallel Execution Engine | Concurrent spec generation, dependency-wave implementation |
| 8 | ✅ | 017 Forge Command | One-command full pipeline with resume, dry-run, enriched prompts |
| 9 | 🔜 | Brownfield mode, auto-PR, custom prompt UI, VS Code extension | Coming soon |

---

## 📋 Step-by-Step Walkthrough

<details>
<summary><strong>Click to expand the full step-by-step guide</strong></summary>

### Step 1: Bootstrap Your Project

```bash
specforge init PersonalFinance --agent claude --stack dotnet
```

SpecForge will:
1. Create the `.specforge/` directory with all configuration files
2. Render Jinja2 templates with your project name, agent, and stack
3. Generate 7 governance prompt files with stack-appropriate rules
4. Write `config.json` with agent, stack, and project metadata
5. Initialize a git repository with initial commit
6. Print a summary with suggested next steps

> **Preview first:** `specforge init PersonalFinance --dry-run`

---

### Step 2: Establish Project Principles

Open your AI coding agent and define your constitution:

```
/specforge.constitution Create principles for a .NET microservices platform.
Clean Architecture with Domain/Application/Infrastructure/API layers.
CQRS for all commands and queries. Functions ≤30 lines, classes ≤300 lines.
Result<T> for all business logic errors. 80% minimum test coverage.
```

This creates `.specforge/memory/constitution.md` — the governance document that gates every planning, implementation, and review step.

---

### Step 3: Decompose Your App

```bash
specforge decompose "Create a webapp for PersonalFinance"
```

The system runs a 3-step pipeline:
1. **Architecture Decision Gate** — Monolithic / Microservice / Modular Monolith
2. **Feature Decomposition** — Matches domain patterns and generates 8–15 features
3. **Service Mapping** (microservice only) — Groups features via affinity scoring

> **Resumable:** State saves after each step. If interrupted, re-run to resume.

---

### Step 4: Run the Per-Feature Pipeline

```bash
# Full pipeline for a specific service
specforge specify ledger-service

# Optional: Detect and resolve ambiguities
specforge clarify ledger-service

# Optional: Enhanced research
specforge research ledger-service

# Implement with quality gates
specforge implement ledger-service
```

---

### Step 5: Implement All Services

```bash
# Implement all services with phased orchestration
specforge implement
```

The orchestrator computes dependency phases, implements services per phase, verifies contracts between phases, and runs integration tests.

---

### Step 6: Monitor Progress

```bash
specforge status                           # Project-wide dashboard
specforge pipeline-status                  # Pipeline status
specforge pipeline-status ledger-service   # Specific service
specforge plugins                          # Installed plugins
```

</details>

---

## 🔍 Troubleshooting

<details>
<summary><strong><code>specforge: command not found</code> after install</strong></summary>

```bash
uv tool update-shell
```

Restart your terminal, or add the appropriate path:
- **Linux/macOS:** `~/.local/bin`
- **Windows:** `%USERPROFILE%\.local\bin`

</details>

<details>
<summary><strong>Agent detected incorrectly or as "generic"</strong></summary>

Run `specforge check` to see which agents are detected. Override manually:

```bash
specforge init my-project --agent claude
```

</details>

<details>
<summary><strong>Git operations fail during init</strong></summary>

Skip git initialization:

```bash
specforge init my-project --no-git
```

</details>

<details>
<summary><strong>Directory already exists</strong></summary>

Use `--force` to add missing files without overwriting customized ones:

```bash
specforge init my-project --force
```

</details>

<details>
<summary><strong>Pipeline interrupted mid-execution</strong></summary>

All operations are resumable — state is saved after each phase/task:

```bash
specforge forge --resume                # Resumes forge from last completed stage
specforge specify ledger-service        # Auto-resumes from last phase
specforge implement --resume            # Resumes from last task
```

</details>

<details>
<summary><strong>Forge state already exists</strong></summary>

If a previous forge run left state behind:

```bash
specforge forge "My app" --force        # Overwrite existing state and start fresh
specforge forge --resume                # Or resume from where it stopped
```

</details>

<details>
<summary><strong>Sub-agent violates governance rules</strong></summary>

When code violates governance prompts (e.g., function exceeds 30 lines), the quality validation system:
1. Flags the violation via one of 11 checkers
2. Generates a targeted fix prompt
3. Instructs the agent to regenerate
4. After 3 failed attempts, creates a diagnostic report for human review

</details>

<details>
<summary><strong>Contract verification fails between phases</strong></summary>

Fix contracts in `.specforge/features/<slug>/contracts/` and re-run:

```bash
specforge implement --resume
```

</details>

<details>
<summary><strong>Docker health check fails</strong></summary>

For microservice projects:
1. Check the service's Dockerfile and health endpoint (`GET /health`)
2. Verify the service starts within 30 seconds
3. The auto-fix loop will attempt resolution up to 3 times automatically

</details>

---

## 💬 Support & License

### Get Help

- 🐛 **Bug reports:** [Open a GitHub issue](https://github.com/Nandakumar333/SpecForge/issues/new)
- 💡 **Feature requests:** [Open a GitHub issue](https://github.com/Nandakumar333/SpecForge/issues/new)
- 💬 **Questions:** [GitHub Discussions](https://github.com/Nandakumar333/SpecForge/discussions)

### License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for details.

---

<div align="center">

**⚙️ SpecForge** — *Spec-First. Agent-Governed. Production-Ready.*

[⬆ Back to Top](#️-specforge)

</div>
