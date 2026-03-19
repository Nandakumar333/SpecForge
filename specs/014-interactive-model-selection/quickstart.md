# Quickstart: Interactive AI Model Selection & Commands Directory

**Feature**: 014-interactive-model-selection

## What Changed

Running `specforge init` now interactively asks which AI agent you want to use (when `--agent` is not provided). After selection, a commands directory is automatically created with ready-to-use slash-command prompt files for all 8 pipeline stages.

## Usage

### Interactive init (new behavior)

```bash
# In an interactive terminal — prompts for agent selection
specforge init MyApp --here

# Output:
# Which AI agent do you want to use? [amp/antigravity/auggie/bob/claude/...
#   .../windsurf/generic] (generic): claude
#
# ✓ Created .specforge/ scaffold
# ✓ Created .claude/commands/ with 8 command files
# ✓ Agent: claude (interactive)
# ✓ Commands directory: .claude/commands
```

### Explicit agent (backward-compatible)

```bash
# No prompt shown — uses copilot directly
specforge init MyApp --here --agent copilot
```

### Generic agent with custom directory

```bash
specforge init MyApp --here
# Which AI agent do you want to use? [...] (generic): generic
# Commands directory [commands/]: my-commands/
#
# ✓ Created my-commands/ with 8 command files
```

### Non-interactive (CI/pipes)

```bash
# Auto-detects agent from PATH (existing behavior)
echo "y" | specforge init MyApp --here
```

## Generated Command Files

After init, your commands directory contains:

```
.claude/commands/          # (or .github/prompts/, .gemini/commands/, commands/, etc.)
├── specforge.decompose.md
├── specforge.specify.md
├── specforge.research.md
├── specforge.plan.md
├── specforge.tasks.md
├── specforge.implement.md
├── specforge.status.md
└── specforge.check.md
```

Each file is a ready-to-use prompt. For Claude, use them as slash commands:
```
/specforge.decompose "Build a personal finance tracker with budgeting"
```

For Copilot, companion `.prompt.md` stubs in `.github/prompts/` enable:
```
/specforge.decompose
```

## Config.json

The selected agent and commands directory are persisted:

```json
{
  "project_name": "MyApp",
  "stack": "python",
  "agent": "claude",
  "commands_dir": ".claude/commands",
  "version": "1.0",
  "created_at": "2026-03-18"
}
```

## Migration from "agnostic"

The term "agnostic" has been replaced with "generic" for agent fallback. Existing projects with `"agent": "agnostic"` in config.json will continue to work — the loader treats missing `agent` field as `"generic"`.
