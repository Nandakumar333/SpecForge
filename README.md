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
    <a href="https://github.com/Nandakumar333/SpecForge/actions/workflows/release.yml"><img src="https://github.com/Nandakumar333/SpecForge/actions/workflows/release.yml/badge.svg" alt="Release"/></a>
    <a href="https://github.com/Nandakumar333/SpecForge/stargazers"><img src="https://img.shields.io/github/stars/Nandakumar333/SpecForge?style=social" alt="GitHub stars"/></a>
    <a href="https://github.com/Nandakumar333/SpecForge/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Nandakumar333/SpecForge" alt="License"/></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
    <img src="https://img.shields.io/badge/install%20with-uv-violet" alt="Install with uv"/>
    <img src="https://img.shields.io/badge/version-0.1.0--March%202026-orange" alt="Version 0.1.0"/>
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
- [🏗️ Architecture & Feature Overview](#️-architecture--feature-overview)
- [🌟 Development Phases (Roadmap)](#-development-phases-roadmap)
- [🎯 Feature Decomposition Example](#-feature-decomposition-example)
- [🔒 Agent Instruction Prompts](#-agent-instruction-prompts)
- [⚠️ Edge Cases as First-Class Citizens](#️-edge-cases-as-first-class-citizens)
- [🧪 Quality Validation System](#-quality-validation-system)
- [🤖 Sub-Agent Execution Engine](#-sub-agent-execution-engine)
- [🔄 Implementation Orchestrator](#-implementation-orchestrator)
- [📊 Project Status Dashboard](#-project-status-dashboard)
- [🔌 Plugin System](#-plugin-system)
- [🔧 Prerequisites](#-prerequisites)
- [📋 Detailed Process](#-detailed-process)
- [🔍 Troubleshooting](#-troubleshooting)
- [💬 Support](#-support)
- [📄 License](#-license)

---

## 🤔 What is Spec-Driven Development?

Spec-Driven Development **flips the script** on traditional software development. For decades, code has been king — specifications were just scaffolding we built and discarded once the "real work" of coding began. Spec-Driven Development changes this: **specifications become executable**, directly generating working implementations rather than just guiding them.

SpecForge is the engine that makes this workflow concrete at enterprise scale. One prompt. Thirteen features. Every feature fully specified, planned, and implemented — independently, in parallel, with strict coding governance enforced at every step.

```
"Create a webapp for PersonalFinance"
         │
         ▼
  App Analyzer Agent
  Identifies 12 bounded features
         │
         ▼
  Per-Feature Pipeline (×12)
  spec → research → data-model → edge-cases → plan → checklist → tasks
         │
         ▼
  Sub-Agent Executor (isolated per feature)
  Context-isolated prompts, auto-fix loop, quality gates, git commits
         │
         ▼
  Implementation Orchestrator
  Phased execution, contract verification, integration validation
         │
         ▼
  Production-Ready Application
```

---

## ⚡ What Makes SpecForge Different

| Feature | Spec Kit | SpecForge |
|---------|----------|-----------|
| Feature identification | Manual — you define each feature | **Automatic** — one-line prompt → architecture decision gate → 8–15 domain-aware features → service mapping |
| Architecture awareness | Single mode | **Three architectures** — monolithic, microservice, modular monolith with architecture-specific artifacts at every phase |
| Sub-agent execution | Single agent, sequential | **Isolated sub-agents per feature** — no context window pollution, context budget management (~100K tokens), dependency-ordered execution |
| Coding governance | Templates and guidelines | **7-domain governance prompts** — hard constraints with precedence rules, threshold conflict detection, stack-specific variants, prompt-rule compliance checking |
| Edge cases | Listed in spec | **First-class artifact** — architecture-aware `edge-cases.md` with YAML frontmatter, deterministic severity matrix, budget-capped analysis per service |
| Quality validation | None | **11 pluggable checkers** — build, lint, test, coverage, line-limit, secrets, TODO scan, prompt-rule compliance, Docker, contract, and boundary checks |
| Auto-fix loop | None | **Built-in** — error-categorized fix prompts → regression detection → revert on new failures (max 3 iterations before diagnostic report escalation) |
| Task generation | Manual task lists | **Architecture-specific build sequences** — 14-step microservice / 7-step monolith, DAG-based dependency ordering, T-shirt effort estimates, governance rule references |
| Multi-service orchestration | None | **Phased execution** — dependency-graph phases, inter-phase contract verification, docker-compose integration validation |
| Industry standard bias | Follows common defaults | **Zero bias** — no assumptions about architecture, patterns, or libraries unless you define them |

---

## 🚀 Get Started

### 1. Install SpecForge

#### Option 1: Persistent Installation (Recommended)

```bash
uv tool install specforge --from git+https://github.com/Nandakumar333/SpecForge.git
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
uv tool install specforge --force --from git+https://github.com/Nandakumar333/SpecForge.git
```

#### Option 2: One-time Usage

```bash
uvx --from git+https://github.com/Nandakumar333/SpecForge.git specforge init <PROJECT_NAME>
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

Use **`specforge decompose`** to break your one-line description into bounded feature modules:

```bash
specforge decompose "Create a webapp for PersonalFinance"
```

SpecForge asks your architecture preference (monolithic / microservice / modular monolith), then identifies 8–15 features using domain knowledge patterns. For microservice architecture, it intelligently groups features into services and generates a `manifest.json` with the full mapping, communication map, and event definitions.

---

### 4. Run the per-feature pipeline

For each feature, run the full 7-phase pipeline:

```
/specforge.specify  →  /specforge.clarify  →  /specforge.research  →  /specforge.plan  →  /specforge.tasks  →  /specforge.implement
```

Or let SpecForge orchestrate the entire pipeline automatically:

```bash
specforge implement --all
```

---

## 📂 Project Structure

SpecForge generates the following structure when you run `specforge init`:

```text
project-root/
├── .specforge/
│   ├── config.json                        # Agent, stack, and project config
│   ├── constitution.md                    # Project-wide governance principles
│   ├── manifest.json                      # Architecture + feature→service mapping
│   ├── communication-map.md               # Mermaid service dependency diagram
│   ├── orchestration-state.json           # Project-level implementation progress
│   ├── memory/
│   │   ├── constitution.md                # Governance rules (AI-readable)
│   │   └── decisions.md                   # Architecture Decision Records
│   ├── prompts/                           # GOVERNANCE PROMPT FILES (7 domains)
│   │   ├── architecture.prompts.md        # System-wide architecture rules
│   │   ├── backend.prompts.md             # Backend coding standards (stack-specific variants)
│   │   ├── frontend.prompts.md            # Frontend coding standards
│   │   ├── database.prompts.md            # Database design rules
│   │   ├── security.prompts.md            # Security requirements
│   │   ├── testing.prompts.md             # Testing strategy & standards (stack-specific variants)
│   │   └── cicd.prompts.md                # CI/CD pipeline rules
│   ├── features/                          # Generated after `specforge decompose`
│   │   ├── 001-authentication/
│   │   │   ├── spec.md                    # User stories, requirements, NFRs
│   │   │   ├── research.md                # Technology options, library verification
│   │   │   ├── data-model.md              # Entities, relationships, migrations
│   │   │   ├── edge-cases.md              # Architecture-aware edge case analysis
│   │   │   ├── plan.md                    # Architecture decisions, component blueprint
│   │   │   ├── checklist.md               # Quality gate — must pass before implementation
│   │   │   ├── tasks.md                   # Dependency-ordered TDD task list
│   │   │   ├── contracts/                 # API specs, event schemas
│   │   │   ├── .pipeline-state.json       # Spec pipeline phase tracking
│   │   │   └── .execution-state.json      # Implementation execution tracking
│   │   └── 002-accounts-wallets/
│   │       └── (same artifact structure)
│   ├── cross-service-infra/               # Shared infrastructure tasks (microservice)
│   │   └── tasks.md                       # Docker compose, gateway, message broker tasks
│   └── templates/                         # Jinja2 feature pipeline templates
│       ├── spec-template.md
│       ├── plan-template.md
│       ├── tasks-template.md
│       ├── checklist-template.md
│       ├── research-template.md
│       ├── datamodel-template.md
│       └── edge-cases-template.md
├── src/                                   # Generated application code
└── tests/
```

> **Governance file naming**: Stack-specific domains use `{domain}.{stack}.prompts.md` format (e.g., `backend.dotnet.prompts.md`, `testing.nodejs.prompts.md`). Stack-agnostic domains use flat naming (e.g., `architecture.prompts.md`, `security.prompts.md`).

---

## 📋 Per-Feature Pipeline

Every feature — regardless of complexity — goes through an identical 7-phase pipeline before a single line of implementation code is written.

| Phase | Artifact | What It Contains |
|-------|----------|-----------------|
| 1 | `spec.md` | User stories (Given/When/Then), functional requirements, non-functional SLOs, explicit out-of-scope, edge case stubs, service-scoped context (microservice) |
| 2 | `research.md` | Technology options with pros/cons, library version verification, structured finding statuses (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING), architecture-specific research extras |
| 3 | `data-model.md` | All entities with fields and types, relationships, value objects, index strategy, migration plan — scoped by architecture (isolated per service / shared per module) |
| 4 | `edge-cases.md` | Architecture-aware edge cases with YAML frontmatter, deterministic severity matrix, inter-service failure scenarios (microservice), interface contract violations (modular-monolith), standard categories (monolith), budget-capped analysis |
| 5 | `plan.md` | Architecture decisions, component breakdown, API endpoint design, frontend tree, constitution compliance gate, architecture-specific sections via adapter |
| 6 | `checklist.md` | Quality gate — all items must pass before implementation begins, architecture-specific checklist items |
| 7 | `tasks.md` | Dependency-ordered tasks with `[P]` parallel markers, TDD enforced, file path hints, effort estimates (S/M/L/XL), governance rule references, conventional commit suggestions |

> **Spec-First Rule**: No implementation begins until all 7 artifacts exist and the checklist gate passes.

### Pipeline State Management

The pipeline tracks phase completion in `.pipeline-state.json`, supporting:
- **Resumable execution** — interrupt and resume from any phase
- **Concurrent safety** — atomic lock files prevent parallel corruption
- **Interrupted detection** — phases left in `in-progress` state are automatically reset on resume
- **Force re-run** — `--force` flag resets all phases to pending

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

| Command | Description | Status |
|---------|-------------|--------|
| `specforge init <project>` | Scaffold project with `.specforge/` directory, governance prompts, templates, and agent config | ✅ Implemented |
| `specforge check` | Verify all required tools (`git`, `python`, `uv`, agent CLI) are installed | ✅ Implemented |
| `specforge validate-prompts` | Validate governance prompt files for threshold conflicts across domains | ✅ Implemented |
| `specforge decompose <description>` | Architecture decision gate → feature decomposition → service mapping → manifest | ✅ Implemented |
| `specforge specify <target>` | Run the 7-phase spec generation pipeline for a service/module | ✅ Implemented |
| `specforge clarify <target>` | Pattern-based ambiguity detection with interactive Q&A resolution | ✅ Implemented |
| `specforge research <target>` | Enhanced research with structured finding statuses | ✅ Implemented |
| `specforge edge-cases <target>` | Architecture-aware edge case analysis with YAML frontmatter | ✅ Implemented |
| `specforge pipeline-status [target]` | Show pipeline phase status per service/module | ✅ Implemented |
| `specforge implement <service>` | Execute all tasks for a service via isolated sub-agent | ✅ Implemented |
| `specforge implement --shared-infra` | Build cross-service infrastructure before any service | ✅ Implemented |
| `specforge implement --all` | Execute all services respecting the dependency graph with phased orchestration | ✅ Implemented |
| `specforge implement --resume` | Resume from last completed task | ✅ Implemented |
| `specforge status` | Show project-wide status dashboard with service progress, quality reports, and phase tracking | ✅ Implemented |
| `specforge plugins` | List installed agent and stack plugins with configuration status | ✅ Implemented |

---

### `specforge init` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<project-name>` | Argument | — | Project directory name. Required unless `--here`. Allowed: `[a-zA-Z0-9_-]` |
| `--agent` | Option | (auto-detect) | AI agent: `claude`, `copilot`, `gemini`, `cursor`, `windsurf`, `codex` |
| `--stack` | Option | (auto-detect) | Tech stack for governance prompt variants: `dotnet`, `nodejs`, `python`, `go`, `java` |
| `--here` | Flag | `False` | Scaffold `.specforge/` into current directory. Mutually exclusive with `<project-name>` |
| `--force` | Flag | `False` | Allow existing directory — preserves customized files (SHA-256 comparison), only adds missing ones |
| `--no-git` | Flag | `False` | Skip `git init`, `.gitignore`, and initial commit |
| `--dry-run` | Flag | `False` | Preview the full file tree without writing anything |

---

### `specforge decompose` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<description>` | Argument | — | One-line application description (e.g., `"Create a personal finance webapp"`) |
| `--arch` | Option | (interactive) | Skip architecture prompt: `monolithic`, `microservice`, `modular-monolith` |
| `--remap` | Option | — | Re-map existing features to a new architecture without losing content |
| `--no-warn` | Flag | `False` | Suppress over-engineering warnings (for scripted/CI usage) |

---

### `specforge specify` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<target>` | Argument | — | Service slug or feature number to run the pipeline for |
| `--force` | Flag | `False` | Reset all phases to pending and re-run |
| `--from` | Option | — | Start from a specific phase (`spec`, `research`, `datamodel`, `edgecase`, `plan`, `checklist`, `tasks`) |

---

### `specforge clarify` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<target>` | Argument | — | Service slug to clarify |
| `--report` | Flag | `False` | Generate non-interactive report instead of interactive Q&A session |

---

### `specforge implement` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `<target>` | Argument | — | Service slug to implement. Required unless `--shared-infra` or `--all` |
| `--shared-infra` | Flag | `False` | Build cross-service infrastructure first (microservice/modular-monolith only) |
| `--all` | Flag | `False` | Implement all services via phased orchestration |
| `--resume` | Flag | `False` | Resume from last completed task |
| `--mode` | Option | `prompt-display` | Execution mode: `prompt-display` (show prompt for manual agent use) or `agent-call` (invoke agent directly) |
| `--max-fix-attempts` | Option | `3` | Max auto-fix retry attempts per task |
| `--to-phase` | Option | — | Stop after completing a specific phase (used with `--all`) |

---

### `specforge status` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `[target]` | Argument | — | Optional service slug to drill down into a specific service's status |

---

### `specforge plugins` Options

| Argument/Option | Type | Default | Description |
|----------------|------|---------|-------------|
| `--agents` | Flag | `False` | List only agent plugins |
| `--stacks` | Flag | `False` | List only stack plugins |

---

### Examples

```bash
# Scaffold a new project (auto-detects agent)
specforge init PersonalFinance

# Scaffold with specific agent and stack
specforge init PersonalFinance --agent claude --stack dotnet

# Initialize in an existing project
specforge init --here --agent copilot

# Add missing .specforge/ files without overwriting customized ones
specforge init --here --force --agent gemini

# Preview what would be created
specforge init PersonalFinance --dry-run

# Skip git initialization
specforge init PersonalFinance --agent claude --no-git

# Check all prerequisites
specforge check

# Validate governance prompt files for conflicts
specforge validate-prompts

# Decompose app description into features (interactive architecture prompt)
specforge decompose "Create a webapp for PersonalFinance"

# Decompose with architecture pre-selected (skip interactive prompt)
specforge decompose --arch microservice "Create a webapp for PersonalFinance"

# Re-map existing features to a different architecture
specforge decompose --remap modular-monolith

# Run spec pipeline for a specific service
specforge specify ledger-service

# Run spec pipeline from a specific phase
specforge specify ledger-service --from edgecase

# Interactive clarification session
specforge clarify ledger-service

# Generate clarification report (non-interactive)
specforge clarify ledger-service --report

# Standalone research generation
specforge research ledger-service

# Architecture-aware edge case generation
specforge edge-cases ledger-service

# View pipeline status
specforge pipeline-status
specforge pipeline-status ledger-service

# Implement a single service
specforge implement ledger-service

# Build shared infrastructure first (microservice)
specforge implement --shared-infra

# Implement all services with phased orchestration
specforge implement --all

# Resume interrupted implementation
specforge implement ledger-service --resume

# Use agent-call mode (invoke agent directly)
specforge implement ledger-service --mode agent-call

# View project-wide status dashboard
specforge status

# List installed plugins
specforge plugins
```

---

## 📖 Slash Commands

After running `specforge init`, your AI agent has access to these slash commands:

### Core Commands

| Command | Description |
|---------|-------------|
| `/specforge.constitution` | Create or update project governing principles — the foundational governance for all sub-agents |
| `/specforge.specify` | Generate `spec.md` — user stories, functional requirements, NFRs, edge case stubs, service-scoped context |
| `/specforge.clarify` | Identify and resolve underspecified areas — pattern-based ambiguity detection with boundary analysis |
| `/specforge.research` | Generate `research.md` — structured findings with RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING statuses |
| `/specforge.plan` | Generate `plan.md` — technical blueprint with architecture decisions, governance compliance gate, and architecture-specific sections |
| `/specforge.tasks` | Generate `tasks.md` — dependency-ordered, TDD-structured, parallelizable task list with effort estimates and governance rule references |
| `/specforge.implement` | Execute all tasks for a feature via isolated sub-agent with auto-fix loop and quality gates |

### Quality & Validation Commands

| Command | Description |
|---------|-------------|
| `/specforge.analyze` | Cross-artifact consistency and coverage analysis — run after `/specforge.tasks`, before `/specforge.implement` |
| `/specforge.checklist` | Generate quality checklists that validate requirements completeness, clarity, and consistency |
| `/specforge.edge-cases` | Generate architecture-aware edge case analysis with deterministic severity and YAML frontmatter |

---

## 🏗️ Architecture & Feature Overview

SpecForge is built as 13 incrementally developed features, each fully specified, planned, and implemented following its own spec-first methodology.

### Feature Map

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         SpecForge Feature Architecture                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ 001 CLI     │  │ 002 Template│  │ 003 Prompt  │  │ 013 Plugin  │   │
│  │ Init/Check  │  │ Engine      │  │ Governance  │  │ System      │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │  FOUNDATION │
│  ┌──────▼──────┐         │                │                │            │
│  │ 004 Arch    │◄────────┘                │                │            │
│  │ Decomposer  │                          │                │            │
│  └──────┬──────┘                          │                │            │
│         │                                 │                │            │
│  ┌──────▼──────┐  ┌─────────────┐  ┌─────▼───────┐       │            │
│  │ 005 Spec    │  │ 006 Research│  │ 007 Edge    │       │  PIPELINE   │
│  │ Pipeline    │◄─┤ & Clarify   │  │ Case Engine │       │            │
│  └──────┬──────┘  └─────────────┘  └──────┬──────┘       │            │
│         │                                  │               │            │
│  ┌──────▼──────┐                           │               │            │
│  │ 008 Task    │◄──────────────────────────┘               │            │
│  │ Generation  │                                           │            │
│  └──────┬──────┘                                           │            │
│         │                                                  │            │
│  ┌──────▼──────┐  ┌─────────────┐                         │            │
│  │ 009 Sub-    │◄─┤ 010 Quality │◄────────────────────────┘  EXECUTION │
│  │ Agent Exec  │  │ Validation  │                                      │
│  └──────┬──────┘  └─────────────┘                                      │
│         │                                                              │
│  ┌──────▼──────┐  ┌─────────────┐                                      │
│  │ 011 Impl    │  │ 012 Project │    ORCHESTRATION                      │
│  │ Orchestrator│  │ Dashboard   │    & MONITORING                       │
│  └─────────────┘  └─────────────┘                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Feature Summaries

| # | Feature | Purpose |
|---|---------|---------|
| 001 | **CLI Init & Scaffold** | `specforge init` with agent auto-detection, stack selection, dry-run preview, git integration, `specforge check` for prerequisites |
| 002 | **Template Rendering Engine** | Jinja2-based template system with `TemplateRegistry` auto-discovery, 4-step resolution chain (user override → built-in), stack-specific variants, custom filters, variable validation |
| 003 | **Agent Prompt Governance** | 7-domain governance prompts with precedence rules, stack-specific variants, `PromptLoader` with Result pattern, `PromptValidator` for threshold conflict detection, `PromptContextBuilder` for sub-agent context |
| 004 | **Architecture Decomposer** | `specforge decompose` with 3-step flow: architecture decision gate → feature decomposition (6 domain patterns) → service mapping (affinity scoring), `manifest.json` with communication maps |
| 005 | **Spec Generation Pipeline** | 6-phase pipeline generating 7 artifacts per service/module, `ArchitectureAdapter` pattern (microservice/monolith/modular-monolith), concurrent phase execution, pipeline state tracking |
| 006 | **Research & Clarification Engine** | Pattern-based ambiguity detection, boundary analysis for cross-service concepts, interactive Q&A flow, architecture-change detection, structured research findings with 4 statuses |
| 007 | **Edge Case Analysis Engine** | Architecture-aware edge cases from declarative YAML patterns, deterministic severity matrix, inter-service failure scenarios, budget-capped analysis (formula: `6+2N+E+2(F-1)`, cap 30), YAML frontmatter |
| 008 | **Task Generation Engine** | Architecture-specific build sequences (14-step microservice / 7-step monolith), DAG-based dependency ordering, T-shirt effort estimates, governance rule references, cross-service infrastructure tasks |
| 009 | **Sub-Agent Executor** | Per-service task execution with context isolation, Mode A (prompt-display) / Mode B (agent-call), auto-fix loop with regression detection, git commit per task, Docker verification (microservice) |
| 010 | **Quality Validation System** | 11 pluggable checkers via `CheckerProtocol`, architecture-aware quality gates, error-categorized auto-fix prompts, diagnostic escalation reports, prompt-rule compliance checking |
| 011 | **Implementation Orchestrator** | Multi-service phased execution from dependency graph, inter-phase contract verification, docker-compose integration validation, monolith single-app integration test, project-level state persistence |
| 012 | **Project Status Dashboard** | Real-time project status view with `specforge status` — service progress, phase completion, quality reports, implementation metrics, Rich terminal rendering with color-coded indicators |
| 013 | **Plugin System** | Extensible architecture with 25+ agent plugins (Claude, Copilot, Gemini, Cursor, Windsurf, Codex, and more) and 3 stack plugins (dotnet, nodejs, python) with unified `AgentPlugin` and `StackPlugin` interfaces |

---

## 🌟 Development Phases (Roadmap)

SpecForge is built incrementally across 6 phases.

### Phase 1 — Foundation ✅
**Feature 001** — CLI Scaffold: `specforge init` with agent detection, stack selection, dry-run preview, git integration, `specforge check` for prerequisites.

**Feature 002** — Template Rendering Engine: Jinja2-based template system with `TemplateRegistry` auto-discovery, stack-specific variants, template inheritance, custom filters, variable validation, snapshot-tested output.

### Phase 2 — Governance & Intelligence ✅
**Feature 003** — Agent Instruction Prompt System: 7-domain governance layer (`architecture`, `backend`, `frontend`, `database`, `security`, `testing`, `cicd`), stack-specific prompt variants, `PromptLoader` with Result pattern, `PromptValidator` for threshold conflict detection, `specforge validate-prompts` command, `PromptContextBuilder` for sub-agent context assembly.

**Feature 004** — Architecture Decision Gate & Decomposer: `specforge decompose` with 3-step flow (architecture selection → feature decomposition → service mapping), 6 built-in domain patterns (finance, e-commerce, SaaS, social, healthcare, education), affinity-based service mapper, interactive review/edit, `manifest.json` generation, communication map with Mermaid diagrams, `--arch`/`--remap`/`--no-warn` flags, crash-safe state persistence.

### Phase 3 — Spec Pipeline ✅
**Feature 005** — Spec Generation Pipeline: 6-phase pipeline generating 7 specification artifacts per service/module, `ArchitectureAdapter` pattern with three implementations (microservice/monolith/modular-monolith), concurrent pipeline execution via `ThreadPoolExecutor`, `.pipeline-state.json` state tracking, atomic file locking, `specforge specify` and `specforge pipeline-status` commands.

**Feature 006** — Research & Clarification Engine: `specforge clarify` with pattern-based `AmbiguityScanner`, cross-service `BoundaryAnalyzer`, `QuestionGenerator` with ranked suggested answers, interactive Rich-based Q&A sessions, `ClarificationRecorder` for atomic spec.md updates. `specforge research` with `ResearchResolver` producing structured findings (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING), architecture-change detection via `previous_architecture` metadata.

**Feature 007** — Edge Case Analysis Engine: Declarative YAML pattern files for 13 edge case categories, `MicroserviceEdgeCaseAnalyzer` reads communication maps and events to instantiate service-specific failure scenarios, `ArchitectureEdgeCaseFilter` removes irrelevant categories, deterministic severity via `SeverityMatrix`, `EdgeCaseBudget` with formula `6+2N+E+2(F-1)` capped at 30, YAML frontmatter for machine parseability.

**Feature 008** — Task Generation Engine: `TaskGenerator` orchestrates `DependencyResolver` (DAG + topological sort + cycle detection), `ArchitectureTaskAdapter` (14-step microservice / 7-step monolith build sequences), `CrossServiceTaskGenerator` (shared contracts, Docker compose, message broker, API gateway, shared auth), `EffortEstimator` (T-shirt sizing with feature/dependency scaling), `GovernanceReader` (read-only prompt rule extraction), cross-service `XDEP` references, conditional step filtering.

### Phase 4 — Execution Engine ✅
**Feature 009** — Sub-Agent Executor: `SubAgentExecutor` processes `tasks.md` in dependency order with isolated `ExecutionContext` per task (constitution + governance + specs + contracts, ~100K token budget), `TaskRunner` with Mode A (prompt-display) and Mode B (agent-call with retry/fallback), `QualityChecker` (build + lint + test), `AutoFixLoop` with regression detection and selective revert, `SharedInfraExecutor` for cross-service infrastructure, `ContractResolver` for dependency contract loading, `DockerManager` for container build/health check/Pact contract tests (microservice only), crash-safe state with git-based committed task detection.

**Feature 010** — Quality Validation System: Pluggable `CheckerProtocol` with 11 concrete checkers (build, lint, test, coverage, line-limit, secrets, TODO scan, prompt-rule compliance, Docker build, Docker service health, contract tests) plus architecture-specific checkers (hardcoded URL detection, proto/event schema validation for microservice; module boundary enforcement, shared migration safety for modular-monolith), `QualityGate` orchestrator selecting checkers by architecture, `AutoFixEngine` with error categorization and targeted fix prompts via Jinja2, `DiagnosticReporter` for structured escalation reports, `LanguageAnalyzerProtocol` with Python AST implementation.

### Phase 5 — Orchestration ✅
**Feature 011** — Implementation Orchestrator: `IntegrationOrchestrator` reads manifest dependency graph, computes phased execution plan via topological sort, executes `SharedInfraExecutor` → per-phase `PhaseExecutor` → `ContractEnforcer` verification → `IntegrationTestRunner` validation. Within-phase services execute sequentially (continue-then-halt on failure). Contract verification via published `.specforge/features/<slug>/contracts/` files. Auto-generated integration tests from contracts. Docker-compose integration validation for microservices. Single-app integration test for monoliths. Project-level state in `.specforge/orchestration-state.json`.

### Phase 6 — Observability & Ecosystem ✅
**Feature 012** — Project Status Dashboard: `specforge status` command with Rich terminal rendering (Table, Panel, Progress, Tree). Real-time project overview showing architecture, domain, feature/service counts. Per-service status table with color-coded indicators (🟢 complete, 🟡 in-progress, 🔴 failed, ⚪ queued), task progress (N/M), quality pass/fail, and 7-phase completion tracking. Phase breakdown, quality summary, implementation progress, and integration test results. Drill-down into individual services. CI/CD-friendly summary reports.

**Feature 013** — Plugin System: Extensible architecture for custom AI agents and technology stacks. 25+ agent plugins with unified `AgentPlugin` interface (Claude, Copilot, Gemini, Cursor, Windsurf, Codex, plus 19 additional agents and a generic fallback). 3 stack plugins (`dotnet`, `nodejs`, `python`) with `StackPlugin` interface providing `get_build_command()`, `get_lint_command()`, `get_test_command()`, `get_docker_base_image()`, and `get_rules()`. Runtime plugin discovery via `PluginManager`. Rule formatter for converting stack rules to governance prompt format. `specforge plugins` command for listing and configuration.

### Phase 7 — Polish & Ecosystem 🔜
Brownfield mode (generate specs from existing code), auto-PR creation per feature, custom prompt authoring UI, VS Code extension.

---

## 🎯 Feature Decomposition Example

When you run `specforge decompose "Create a webapp for PersonalFinance"`, SpecForge executes a 3-step flow:

### Step 1 — Architecture Decision Gate

```
? Which architecture pattern for this project?
  ❯ 1. Monolithic — All features in a single deployable unit with module separation
    2. Microservice — Features mapped to independent services
    3. Modular Monolith — Single deploy but strict module boundaries (can split later)
```

### Step 2 — Feature Decomposition

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

### Step 3 — Service Mapping (Microservice only)

12 features → 8 services via affinity scoring:

| Service | Features | Rationale |
|---------|----------|-----------|
| Identity Service | 001 | **WHY SEPARATE**: Foundation — every other service depends on it |
| Ledger Service | 002, 003 | **WHY COMBINED**: Shared bounded context — accounts and transactions access the same data |
| Planning Service | 004, 006, 007 | **WHY COMBINED**: All three are future financial planning with shared domain vocabulary |
| Portfolio Service | 005 | **WHY SEPARATE**: Specialized domain with unique external dependencies (market data APIs) |
| Analytics Service | 008, 011 | **WHY COMBINED**: Both read-heavy consumers with same data pipeline and caching strategy |
| Notification Service | 009 | **WHY SEPARATE**: Purely async, multi-channel, different scaling profile |
| Integration Service | 010 | **WHY SEPARATE**: External API dependency with rate limiting and circuit-breaker patterns |
| Admin Service | 012 | **WHY SEPARATE**: System management with different access control |

Output: `manifest.json` + `communication-map.md` (Mermaid diagram) + feature directories under `.specforge/features/`.

---

## 🔒 Agent Instruction Prompts

The `.specforge/prompts/` directory contains **7 governance prompt files** across 7 domains. These are **not guidelines** — they are hard constraints. Sub-agents that violate them have their output rejected and regenerated.

### Governance Domains

| Domain | File | Precedence | Description |
|--------|------|-----------|-------------|
| Architecture | `architecture.prompts.md` | 1 (highest) | System-wide architecture rules — Clean Architecture, layering, dependency direction |
| Security | `security.prompts.md` | 2 | Auth, input validation, secrets management, CORS, HSTS |
| Backend | `backend.{stack}.prompts.md` | 3 | Backend coding standards — function/class limits, error patterns, naming |
| Frontend | `frontend.prompts.md` | 4 | Component architecture, state management, accessibility |
| Database | `database.prompts.md` | 5 | Schema-first migrations, naming, indexing, audit trails |
| Testing | `testing.{stack}.prompts.md` | 6 | Testing framework, coverage thresholds, naming conventions |
| CI/CD | `cicd.prompts.md` | 7 (lowest) | Docker builds, IaC, commit conventions, deployment |

> **Precedence rule**: When rules conflict across governance domains, higher-precedence domains win. Security always overrides backend-specific rules.

### What They Enforce

**`architecture.prompts.md`** — System-wide rules with highest precedence. Clean Architecture layers, SOLID principles, dependency direction, no circular dependencies.

**`security.prompts.md`** — JWT with refresh tokens, policy-based authorization, input validation at API boundary AND domain layer, no raw SQL concatenation, CORS origin whitelist, HSTS, no secrets in code.

**`backend.prompts.md`** — 30-line function limit, 300-line class limit, Result\<T\> pattern, no magic strings, structured logging. Stack-specific variants: `.dotnet`, `.nodejs`, `.python`, `.go`, `.java`.

**`frontend.prompts.md`** — Atomic Design component architecture, typed state management, no prop drilling beyond 2 levels, 150-line component limit, WCAG 2.1 AA accessibility.

**`database.prompts.md`** — Schema-first migrations, snake_case naming, indexed foreign keys, soft deletes with `is_deleted + deleted_at`, audit trail on every table, no N+1 queries.

**`testing.prompts.md`** — 80% line coverage minimum (100% for domain logic), `MethodName_StateUnderTest_ExpectedBehavior` naming, integration test containers. Stack-specific variants available.

**`cicd.prompts.md`** — Multi-stage Docker builds, non-root Alpine images, Terraform/Pulumi IaC, Conventional Commits, automatic rollback on health check failure.

### Conflict Detection

Run `specforge validate-prompts` to detect threshold conflicts between governance files. For example, if `backend.prompts.md` sets max function length to 30 lines but `testing.prompts.md` sets it to 50 lines, the validator flags the conflict.

### Tech Stack Adaptation

Governance prompts adapt to your stack. Specify `--stack python` during `specforge init` and `FluentValidation → Pydantic`, `EF Core → SQLAlchemy`, `xUnit → pytest`. The same governance rules, applied to your language.

---

## ⚠️ Edge Cases as First-Class Citizens

Every feature in SpecForge has a dedicated `edge-cases.md` — generated before implementation begins, not discovered after. The edge case engine is **architecture-aware**, generating different categories based on your project architecture:

### Standard Categories (All Architectures)

- **Concurrency** — two users updating the same resource simultaneously
- **Data boundaries** — empty lists, max values, special characters, encoding issues
- **State machine gaps** — session expiry mid-flow, interrupted transactions
- **UI/UX** — long text overflow, missing data, slow connections, keyboard navigation
- **Security** — token replay, CSRF, concurrent sessions, privilege escalation
- **Data migration** — schema evolution, backward compatibility, rollback scenarios

### Microservice-Specific Categories

- **Service unavailability** — dependent service returns 503 during critical operations
- **Network partition** — async message loss/delay between services
- **Eventual consistency** — consumer data lags behind producer after event publication
- **Distributed transactions** — multi-consumer coordination failures
- **Version skew** — API/schema changes affecting dependent services
- **Data ownership** — shared entity conflicts across service boundaries

### Modular-Monolith Addition

- **Interface contract violation** — module boundary violations, cross-module direct DB access

### Deterministic Severity

Edge case severity is determined by a **severity matrix** — not by LLM judgment:

| Dependency Type | Pattern | Severity |
|----------------|---------|----------|
| Required | sync-rest / sync-grpc | **Critical** |
| Required | async-event | **High** |
| Optional | sync-rest / sync-grpc | **High** |
| Optional | async-event | **Medium** |

### Budget-Capped Analysis

Edge cases are limited per service using the formula: `budget = 6 + (2 × deps) + events + (2 × max(0, features - 1))`, capped at **30 per service**. When over budget, cases are prioritized by severity × category priority before truncation.

---

## 🧪 Quality Validation System

SpecForge includes a comprehensive **pluggable quality validation system** with 11 concrete checkers organized into standard and architecture-specific categories.

### Standard Checkers (All Architectures)

| Checker | What It Validates |
|---------|------------------|
| **Build** | Project compiles without errors |
| **Lint** | Code passes ruff/eslint with structured output |
| **Test** | All tests pass (pytest/dotnet test) |
| **Coverage** | Meets threshold from `testing.prompts.md` (default: 80%, domain: 100%) |
| **Line Limit** | Functions ≤30 lines, classes ≤200 lines (via AST analysis) |
| **Secrets** | No hardcoded secrets (regex + entropy detection) |
| **TODO Scan** | No unresolved TODO/FIXME/HACK markers |
| **Prompt Rules** | Compliance with Feature 003 governance thresholds |

### Architecture-Specific Checkers

| Checker | Architecture | What It Validates |
|---------|-------------|------------------|
| **Docker Build** | Microservice | Docker image builds successfully |
| **Docker Service** | Microservice | Container starts and passes health check |
| **Contract Tests** | Microservice | Pact consumer tests pass against dependencies |
| **URL Detection** | Microservice | No hardcoded service URLs (must use service discovery) |
| **Interface Validation** | Microservice | Proto files compile, event schemas validate |
| **Boundary** | Modular-monolith | No cross-module direct DB access or boundary violations |
| **Migration Safety** | Modular-monolith | Shared migrations don't break module boundaries |

### Auto-Fix with Error Categorization

When quality checks fail, the `AutoFixEngine` generates **targeted fix prompts** based on error category — not generic "fix it" instructions. Regression detection prevents fixes from introducing new failures, with automatic `git checkout` revert when regressions are detected. After 3 failed attempts, a structured `DiagnosticReport` is generated for human review:

```
Fix Attempt Flow:
  Quality Check → FAIL → Categorize Error → Generate Targeted Fix Prompt
       → Agent Applies Fix → Re-Check
           → PASS → Commit ✓
           → REGRESSION → Revert Fix → Next Attempt
           → SAME ERROR → Next Attempt (max 3)
           → EXHAUSTED → Diagnostic Report → Halt
```

---

## 🤖 Sub-Agent Execution Engine

The sub-agent executor implements one service at a time by processing its `tasks.md` in dependency order with **strict context isolation**.

### Context Assembly

Each task gets an isolated `ExecutionContext` assembled from:

| Context Section | Source | Priority (truncation order) |
|----------------|--------|----------------------------|
| Current task description | `tasks.md` | Highest (never truncated) |
| Constitution | `constitution.md` | Highest (never truncated) |
| Service spec | `spec.md` | High |
| Governance prompts | `.specforge/prompts/` | High |
| Implementation plan | `plan.md` | Medium |
| Data model | `data-model.md` | Medium |
| Dependency contracts | `contracts/` directories | Medium |
| Architecture prompts | (microservice only) | Low |
| Edge cases | `edge-cases.md` | Lowest (truncated first) |

**Token budget**: ~100K tokens. When exceeded, lowest-priority sections are truncated first.

**Isolation enforcement**: The context builder physically cannot read paths outside the allowlist (constitution, prompts, target service features, dependency contracts).

### Execution Modes

| Mode | Behavior |
|------|----------|
| **prompt-display** (default) | Renders the implementation prompt, displays it with Rich formatting, optionally copies to clipboard. User manually runs it in their agent and confirms completion. |
| **agent-call** | Sends prompt directly to detected agent via subprocess. Retries 3 times with exponential backoff (1s, 2s, 4s), then falls back to prompt-display. |

### Per-Task Workflow

```
For each pending task (in dependency order):
  1. Update state → in-progress
  2. Build ExecutionContext (context isolation enforced)
  3. Generate ImplementPrompt from context
  4. Execute via TaskRunner (Mode A or Mode B)
  5. Run QualityChecker (build + lint + test)
  6. If PASS → git commit (conventional commit) → save state → next task
  7. If FAIL → AutoFixLoop (max 3 attempts)
     → If fix succeeds → commit combined changes → next task
     → If fix exhausted → save state → HALT
```

### Crash Recovery

The engine handles crash scenarios between git commit and state save by checking `git log --grep="<task_id>"` on resume. If the commit exists, the task is marked completed without re-execution.

---

## 🔄 Implementation Orchestrator

The orchestrator coordinates multi-service implementation through **phased execution** derived from the service dependency graph.

### Microservice Orchestration Flow

```
manifest.json → Build Dependency Graph → Detect Cycles → Compute Phases
    │
    ▼
Phase 0: SharedInfraExecutor
    → Shared contracts, Docker compose, message broker, API gateway, shared auth
    │
    ▼
Phase 1..N: PhaseExecutor (services with no unmet dependencies)
    → SubAgentExecutor per service (sequential within phase)
    → ContractEnforcer.verify() after each phase
    → If contract verification fails → HALT
    │
    ▼
Integration: IntegrationTestRunner
    → docker-compose up → health checks → request flow → event propagation
    │
    ▼
Report: IntegrationReporter
    → Markdown integration report via Jinja2
```

### Monolith Orchestration Flow

```
manifest.json → Topological Module Ordering
    │
    ▼
Phase 1..N: Sequential module implementation
    → SubAgentExecutor per module
    → Boundary verification after each phase (modular-monolith)
    │
    ▼
Integration: Single-app integration test (no Docker)
```

### Failure Policy

**Continue-then-halt**: When a service fails within a phase, remaining services in the same phase continue to completion (they have no mutual dependencies by definition). The orchestrator then halts before the next phase to prevent building on incomplete foundations.

### State Persistence

Project-level orchestration state is stored in `.specforge/orchestration-state.json`, separate from per-service execution state. Both use atomic writes (temp file + `os.replace()`) for crash safety.

---

## 📊 Project Status Dashboard

The `specforge status` command provides a comprehensive real-time view of your entire project's progress.

### Dashboard Overview

```bash
specforge status
```

Displays:
- **Project Overview** — Architecture, domain, feature count, service count, manifest path
- **Service Table** — Per-service status with color-coded indicators:

| Indicator | Meaning |
|-----------|---------|
| 🟢 | Service complete — all tasks done, quality passed |
| 🟡 | Service in progress — actively being implemented |
| 🔴 | Service failed — quality check or implementation error |
| ⚪ | Service queued — waiting for dependencies |

- **Phase Breakdown** — Which services are in which pipeline phase (spec → research → plan → checklist → tasks → datamodel → edgecase)
- **Quality Summary** — Services passing vs failing quality checks, broken down by checker category
- **Implementation Progress** — Per-service task progress (completed/total)
- **Integration Test Results** — Cross-service test status

### Per-Service Drill-Down

```bash
specforge pipeline-status ledger-service
```

Shows detailed phase completion for a specific service.

---

## 🔌 Plugin System

SpecForge uses an extensible plugin architecture for AI agents and technology stacks. Plugins are discovered at runtime from `src/specforge/plugins/`.

### Agent Plugins

25+ agent plugins with a unified `AgentPlugin` interface:

| Plugin | Agent | Description |
|--------|-------|-------------|
| `claude_plugin.py` | Claude | Anthropic Claude via API |
| `copilot_plugin.py` | GitHub Copilot | GitHub Copilot CLI |
| `gemini_plugin.py` | Gemini | Google Gemini CLI |
| `cursor_plugin.py` | Cursor | Cursor IDE integration |
| `windsurf_plugin.py` | Windsurf | Windsurf editor |
| `codex_plugin.py` | Codex | OpenAI Codex CLI |
| `generic_plugin.py` | Any | Fallback copy-paste flow for unsupported agents |

Plus 19 additional plugins for agents like Mistral, Qwen, and others.

### Stack Plugins

Stack plugins define language-specific build, lint, and test commands:

| Stack | Build | Lint | Test | Docker Base |
|-------|-------|------|------|-------------|
| **dotnet** | `dotnet build` | StyleCop | `dotnet test` | `mcr.microsoft.com/dotnet/aspnet:8` |
| **nodejs** | `npm run build` | ESLint | `npm test` | `node:20-alpine` |
| **python** | `python -m pytest` | Ruff | `pytest` | `python:3.11-slim` |

Each stack plugin also provides stack-specific coding rules (e.g., C# PascalCase conventions, Python type hint requirements) via `get_rules()`.

### Managing Plugins

```bash
# List installed agent and stack plugins
specforge plugins
```

### Extending with Custom Plugins

Implement the `AgentPlugin` or `StackPlugin` protocol:

```python
class AgentPlugin(ABC):
    @abstractmethod
    def execute_task(self, prompt: str, context: dict) -> str: ...

    @abstractmethod
    def configure(self) -> Result[str]: ...

class StackPlugin(ABC):
    @abstractmethod
    def get_build_command(self) -> str: ...

    @abstractmethod
    def get_lint_command(self) -> str: ...

    @abstractmethod
    def get_test_command(self) -> str: ...
```

---

## 🔧 Prerequisites

- **Linux / macOS / Windows**
- A [supported AI coding agent](#-supported-ai-agents) installed and accessible in PATH
- [uv](https://docs.astral.sh/uv/) — for package management and tool install
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [Docker](https://docs.docker.com/get-docker/) — required for microservice architecture (container build, health check, integration validation)
- [docker-compose](https://docs.docker.com/compose/) — required for microservice integration testing

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
3. Generate 7 governance prompt files with stack-appropriate rules and threshold constraints
4. Write `config.json` with agent, stack, and project metadata
5. Initialize a git repository and make the initial commit: `chore: init specforge scaffold`
6. Print a summary of all created files and suggested next steps

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

Run the decompose command to identify features and (optionally) map them to services:

```bash
specforge decompose "Create a webapp for PersonalFinance"
```

The system executes a 3-step pipeline:
1. **Architecture Decision Gate** — asks monolithic / microservice / modular monolith
2. **Feature Decomposition** — matches domain patterns and generates 8–15 features
3. **Service Mapping** (microservice only) — groups features into services using affinity scoring

State is saved after each step — if interrupted, re-running resumes from where you left off.

---

### STEP 3: Run the per-feature pipeline

For each feature, work through the 7-phase pipeline:

**Specify:**
```bash
specforge specify ledger-service
```
Runs the full 6-phase pipeline producing `spec.md`, `research.md`, `data-model.md`, `edge-cases.md`, `plan.md`, `checklist.md`, and `tasks.md` — all scoped to the service's features and architecture.

**Clarify (optional, recommended):**
```bash
specforge clarify ledger-service
```
Pattern-based ambiguity scanner detects vague terms, undefined concepts, missing boundaries, and cross-service entity conflicts. Interactive Q&A session records answers directly in `spec.md`.

**Research (optional):**
```bash
specforge research ledger-service
```
Generates enhanced research with structured findings. Scans for `NEEDS CLARIFICATION` markers, technology references, and architecture-specific topics.

**Edge Cases (standalone):**
```bash
specforge edge-cases ledger-service
```
Generates architecture-aware edge cases with YAML frontmatter, deterministic severity, and budget-capped analysis.

**Implement:**
```bash
specforge implement ledger-service
```
The sub-agent loads constitution + applicable prompt files + this service's spec artifacts — nothing else. It executes tasks in dependency order, runs quality checks after each task, and auto-fixes failures (max 3 iterations).

---

### STEP 4: Run all services

Once all services are specified and planned, implement them respecting the dependency graph:

```bash
# Build shared infrastructure first (microservice/modular-monolith)
specforge implement --shared-infra

# Then implement all services with phased orchestration
specforge implement --all
```

The orchestrator computes dependency phases, implements services per phase, verifies contracts between phases, and runs integration tests at the end.

---

### STEP 5: Check progress

```bash
# Project-wide status dashboard
specforge status

# Per-service pipeline status
specforge pipeline-status

# Specific service
specforge pipeline-status ledger-service

# List installed plugins
specforge plugins
```

Shows phase completion status across all services: `pending → in-progress → complete → failed`.

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

Sub-agents that generate code violating agent instruction prompts (e.g., function exceeds 30 lines, missing type hints) have their output automatically flagged. The quality validation system runs 11 checks including prompt-rule compliance. The agent is instructed to regenerate the affected section with a targeted fix prompt. After 3 failed iterations, a structured diagnostic report is generated for human review.

---

### Pipeline interrupted mid-execution

All pipeline operations are resumable. State is saved after each phase/task:

```bash
# Resume spec pipeline
specforge specify ledger-service  # auto-resumes from last completed phase

# Resume implementation
specforge implement ledger-service --resume

# Resume multi-service orchestration
specforge implement --all --resume
```

---

### Contract verification fails between phases

When inter-phase contract verification fails, the orchestrator halts and reports which service pairs have incompatible contracts. Fix the contracts in `.specforge/features/<slug>/contracts/` and re-run:

```bash
specforge implement --all --resume
```

---

### Docker health check fails during verification

Microservice post-implementation verification includes Docker image build, health check, and Pact contract tests. If the health check fails:

1. Check the service's Dockerfile and health endpoint (convention: `GET /health`)
2. Verify the service starts within the timeout (default: 30 seconds)
3. The auto-fix loop will attempt to resolve build/health issues up to 3 times

---

### Preview changes before committing

```bash
specforge init my-project --dry-run
```

---

## 💬 Support

For support, please open a [GitHub issue](https://github.com/Nandakumar333/SpecForge/issues/new). Bug reports, feature requests, and questions about spec-driven development are all welcome.

---

## 📄 License

This project is licensed under the terms of the MIT open source license. Please refer to the [LICENSE](./LICENSE) file for the full terms.

---

<div align="center">
    <em>SpecForge — Spec-First. Agent-Governed. Production-Ready.</em>
</div>
