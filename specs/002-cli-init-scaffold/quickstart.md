# Quickstart: SpecForge CLI Init & Scaffold

**Feature**: `002-cli-init-scaffold` | **Date**: 2026-03-14

This document describes how to install SpecForge, scaffold a new project, and verify your setup. It is the reference for the "zero to working project" path described in SC-001 and SC-002.

---

## Prerequisites

| Tool | Min Version | Install |
|------|-------------|---------|
| Python | 3.11+ | https://python.org/downloads |
| uv | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.x+ | https://git-scm.com/downloads |
| An AI agent CLI | any | See agent table below |

**Supported AI agents** (at least one required for agent-specific config):

| Agent | CLI binary | Install |
|-------|-----------|---------|
| Claude | `claude` | https://claude.ai/download |
| GitHub Copilot | `gh-copilot` | `gh extension install github/gh-copilot` |
| Gemini | `gemini` | https://ai.google.dev/gemini-api/docs/downloads |
| Cursor | `cursor` | https://cursor.com |
| Windsurf | `windsurf` | https://windsurf.com |
| Codex | `codex` | https://github.com/openai/codex |

---

## Installation

```bash
uv tool install specforge --from git+https://github.com/<org>/specforge
```

Verify:
```bash
specforge --version
# specforge 0.1.0
```

---

## Scaffold a New Project

```bash
specforge init myapp
```

This creates:
```
myapp/
└── .specforge/
    ├── constitution.md          # Project principles and governance
    ├── memory/
    │   ├── constitution.md      # Populated from template
    │   └── decisions.md         # Decision log (starts empty)
    ├── features/                # One subdirectory per feature spec
    ├── prompts/                 # 7 AI agent instruction files
    │   ├── app-analyzer.md
    │   ├── feature-specifier.md
    │   ├── implementation-planner.md
    │   ├── task-decomposer.md
    │   ├── code-reviewer.md
    │   ├── test-writer.md
    │   └── debugger.md
    └── templates/
        └── features/            # 7 per-feature document templates
```

Plus: `.gitignore` and initial commit `"chore: init specforge scaffold"`.

---

## Common Workflows

### Scaffold with explicit agent and stack
```bash
specforge init myapp --agent claude --stack python
```

### Adopt SpecForge in an existing project
```bash
cd /path/to/existing-project
specforge init --here
```

### Add to existing project that already has `.specforge/` (add missing files only)
```bash
specforge init --here --force
```

### Preview what would be created (no writes)
```bash
specforge init myapp --dry-run
```

### Skip git setup (e.g., CI environment)
```bash
specforge init myapp --no-git
```

---

## Verify Your Environment

```bash
specforge check
```

Check a specific agent:
```bash
specforge check --agent claude
```

---

## Start Speccing a Feature

```bash
cd myapp
specforge decompose "A task management app with team collaboration"
# → lists detected features

specforge specify "User authentication"
# → creates specs/001-user-authentication/spec.md
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: Directory 'myapp' already exists.` | Target dir present | Add `--force` |
| `Error: .specforge/ already exists.` | Re-running `--here` | Add `--force` |
| Agent shows as `agnostic` | No supported agent CLI in PATH | Run `specforge check` to see what's missing |
| `git` operations fail | git not installed or not in PATH | Install git; or use `--no-git` |
| `specforge: command not found` | uv tool not in PATH | Run `uv tool update-shell` or add `~/.local/bin` to PATH |
