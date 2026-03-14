# CLI Command Contract: SpecForge

**Feature**: `001-cli-init-scaffold` | **Date**: 2026-03-14

This document is the authoritative contract for all CLI commands exposed in this feature. Each command's flags, arguments, exit codes, and output format are binding for both implementation and tests.

---

## Root Group

```
specforge [--version] [--help] COMMAND
```

| Flag | Type | Description |
|------|------|-------------|
| `--version` | flag | Print `specforge x.y.z` and exit 0 |
| `--help` | flag | Print usage and exit 0 |

---

## `specforge init`

```
specforge init [NAME] [OPTIONS]
```

### Arguments

| Argument | Required | Validation | Description |
|----------|----------|------------|-------------|
| `NAME` | Required unless `--here` | `^[a-zA-Z0-9_-]+$` | Project name; becomes the directory name |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--here` | flag | `False` | Scaffold into CWD instead of creating `NAME/` subdirectory. Mutually exclusive with `NAME`. |
| `--agent` | choice | (auto-detect) | `claude \| copilot \| gemini \| cursor \| windsurf \| codex` |
| `--stack` | choice | (agnostic) | `dotnet \| nodejs \| python \| go \| java` |
| `--force` | flag | `False` | Allow scaffolding into an existing directory; preserves existing files |
| `--no-git` | flag | `False` | Skip `git init`, `.gitignore` creation, and initial commit |
| `--dry-run` | flag | `False` | Print file tree preview; no files written, no git operations |

### Mutual Exclusions

| Pair | Behavior |
|------|----------|
| `NAME` + `--here` | Error: "Cannot specify both NAME and --here. Use --here to scaffold into the current directory." |

### Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Success — project scaffolded (or dry-run preview printed) |
| `1` | Runtime error — directory exists without `--force`, permission denied, git failure, invalid agent/stack value |
| `2` | Usage error — missing required argument, invalid flag combination (Click default) |

### Stdout Contract

**Success (normal)**:
```
✓ Created .specforge/ structure (17 files)
✓ Agent configured: claude (auto-detected)
✓ Stack: agnostic
✓ Git initialized with initial commit

Next steps:
  cd myapp
  specforge check
  specforge specify "your first feature"
```

**Success (--dry-run)**:
```
[DRY RUN] Would create:
myapp/
└── .specforge/
    ├── constitution.md
    ├── memory/
    │   ├── constitution.md
    │   └── decisions.md
    ├── features/
    ├── prompts/
    │   ├── app-analyzer.md
    │   └── ... (6 more)
    └── templates/
        └── features/
            └── ... (7 files)
No files were written.
```

**Error (directory exists, no --force)**:
```
Error: Directory 'myapp' already exists.
Use --force to scaffold into it: specforge init myapp --force
```

**Error (invalid name)**:
```
Error: Invalid project name 'my app'. Only alphanumeric characters, hyphens, and underscores are allowed.
```

### Stderr Contract

All error messages go to stderr. Exit code 1 for runtime errors, 2 for usage errors.

---

## `specforge check`

```
specforge check [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--agent` | choice | (none) | `claude \| copilot \| gemini \| cursor \| windsurf \| codex` — include agent CLI in prerequisite check |

### Exit Codes

| Code | Condition |
|------|-----------|
| `0` | All prerequisites present |
| `1` | One or more prerequisites missing |

### Stdout Contract

**All present**:
```
Prerequisite Check
──────────────────────────────────────────
  ✓  git        2.43.0
  ✓  python     3.11.8
  ✓  uv         0.4.1
  ✓  claude     1.0.0

All prerequisites met.
```

**One or more missing**:
```
Prerequisite Check
──────────────────────────────────────────
  ✓  git        2.43.0
  ✗  python     not found  →  Install: https://python.org/downloads
  ✓  uv         0.4.1
  ✗  claude     not found  →  Install: https://claude.ai/download

2 prerequisites missing.
```

---

## `specforge decompose`

```
specforge decompose DESCRIPTION
```

### Arguments

| Argument | Required | Validation | Description |
|----------|----------|------------|-------------|
| `DESCRIPTION` | Yes | Non-empty string | One-line application description |

### Exit Codes

| Code | Condition |
|------|-----------|
| `0` | App Analyzer invoked and feature list displayed |
| `1` | App Analyzer unavailable or returned error |
| `2` | Missing or empty DESCRIPTION argument |

### Stdout Contract

**Success**:
```
Decomposing: "A task management app with team collaboration"

Identified features:
  1. User authentication & profiles
  2. Task creation and management
  3. Team workspace & member roles
  4. Real-time collaboration (comments, mentions)
  5. Notifications & activity feed

Run `specforge specify "<feature name>"` to begin speccing a feature.
```

**Error (no description)**:
```
Error: DESCRIPTION is required.
Usage: specforge decompose "A task management app with ..."
```

---

## Error Message Standards

All error messages follow this format (FR-014, SC-005):

```
Error: <what went wrong in one sentence>.
<Actionable next step with exact command if applicable>.
```

- Always on stderr
- Always paired with a non-zero exit code
- Always include a next step — never a dead end
