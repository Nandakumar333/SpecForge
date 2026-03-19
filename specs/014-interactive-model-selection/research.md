# Research: Interactive AI Model Selection & Commands Directory

**Feature**: 014-interactive-model-selection
**Date**: 2026-03-18

## R1: Interactive Agent Selection via Rich Prompt

**Decision**: Use `rich.prompt.Prompt.ask()` with `choices` parameter for agent selection.

**Rationale**: Rich `Prompt.ask()` is already used in 2 modules (`decompose_cmd.py`, `task_runner.py`) with the exact pattern needed: `Prompt.ask("prompt", choices=[...], default="...")`. No new dependency required. The `choices` parameter provides built-in validation — user must type one of the listed values.

**Alternatives considered**:
- `questionary` library — rejected because it adds a new dependency; Rich is already available
- `click.prompt()` with `type=click.Choice()` — functional but lacks Rich's styled output
- Numbered menu with manual parsing — rejected for unnecessary complexity; Rich handles choice validation natively

**Pattern**:
```python
from rich.prompt import Prompt
agent = Prompt.ask(
    "Which AI agent do you want to use?",
    choices=[...sorted_agent_names..., "generic"],
    default="generic",
)
```

## R2: TTY Detection for Non-Interactive Fallback

**Decision**: Use `sys.stdin.isatty()` to detect interactive terminals. When False, skip prompt and use existing auto-detect via `detect_agent()`.

**Rationale**: `sys.stdin.isatty()` is the standard Python approach. No existing TTY detection in the codebase — this is the first usage. Click does not provide a built-in TTY check.

**Alternatives considered**:
- `os.isatty(0)` — equivalent but less readable
- `click.get_text_stream('stdin').isatty()` — unnecessary indirection
- Environment variable check (e.g., `CI=true`) — fragile, not standard

## R3: Per-Agent Commands Directory Mapping

**Decision**: Each agent plugin defines a `commands_dir` property. Mapping follows Spec-Kit's `AGENT_CONFIGS` convention for the 3 major agents; other agents use their existing `_dir_path` + `/commands` (or fallback to `.specforge/commands/`).

**Rationale**: Claude, Gemini, and Copilot have well-known native command directories. Other agents either follow the `{config_dir}/commands/` pattern or fall back to the generic location.

| Agent | `commands_dir` | Format | Extension | Args Placeholder |
|-------|---------------|--------|-----------|-----------------|
| claude | `.claude/commands` | markdown | `.md` | `$ARGUMENTS` |
| copilot | `.github/prompts` | markdown | `.prompt.md` | `$ARGUMENTS` |
| gemini | `.gemini/commands` | toml | `.toml` | `$ARGUMENTS` |
| cursor | `.cursor/commands` | markdown | `.md` | `$ARGUMENTS` |
| windsurf | `.windsurf/commands` | markdown | `.md` | `$ARGUMENTS` |
| codex | `.codex/commands` | markdown | `.md` | `$ARGUMENTS` |
| kiro | `.kiro/commands` | markdown | `.md` | `$ARGUMENTS` |
| roocode | `.roo/commands` | markdown | `.md` | `$ARGUMENTS` |
| amp | `.amp/commands` | markdown | `.md` | `$ARGUMENTS` |
| antigravity | `.agy/commands` | markdown | `.md` | `$ARGUMENTS` |
| bob | `.bob/commands` | markdown | `.md` | `$ARGUMENTS` |
| kilocode | `.kilocode/commands` | markdown | `.md` | `$ARGUMENTS` |
| trae | `.trae/commands` | markdown | `.md` | `$ARGUMENTS` |
| *[other single-file agents]* | `.specforge/commands` | markdown | `.md` | `$ARGUMENTS` |
| generic | user-chosen (default: `commands/`) | markdown | `.md` | `$ARGUMENTS` |

**Note**: For agents with no known native commands directory (e.g., auggie, jules, etc. that use a root-level single file), the `commands_dir` falls back to `.specforge/commands/`. The generic fallback for Copilot is `.prompt.md` extension (not `.md`) since Copilot discovers commands via the `.prompt.md` suffix.

## R4: Agent-Specific Output Formats

**Decision**: Markdown is the default format for all agents. Gemini uses TOML format with `prompt = """..."""` blocks.

**Rationale**: Spec-Kit's `CommandRegistrar` writes TOML for Gemini and Markdown for all others. Gemini's `.gemini/commands/` directory expects `.toml` files.

**TOML format** (Gemini):
```toml
description = "Decompose application into features"

# Source: specforge

prompt = """
[command content here]
"""
```

**Markdown format** (all others):
```markdown
---
description: "Decompose application into features"
---

<!-- Source: specforge -->

[command content here]
```

**Alternatives considered**:
- Single Markdown format for all — rejected because Gemini ignores Markdown files in `.gemini/commands/`
- YAML format option — not used by any known agent

## R5: Copilot Companion `.prompt.md` Stubs

**Decision**: For Copilot, generate companion `.prompt.md` files in `.github/prompts/` with YAML frontmatter referencing the agent mode.

**Rationale**: Copilot discovers slash commands via `.prompt.md` files in `.github/prompts/`. The YAML frontmatter `agent:` field links the prompt to a Copilot agent mode.

**Format**:
```markdown
---
agent: specforge.decompose
---
```

This is the exact pattern from Spec-Kit's `write_copilot_prompt()` method.

## R6: Config.json Extension

**Decision**: Add `agent` and `commands_dir` fields to the existing config.json schema. Modify `_write_config_json()` to accept these new fields.

**Rationale**: `config.json` already stores `project_name`, `stack`, `version`, `created_at`. Adding `agent` and `commands_dir` is a backward-compatible extension — existing readers ignore unknown keys.

**Extended schema**:
```json
{
  "project_name": "my-app",
  "stack": "python",
  "agent": "claude",
  "commands_dir": ".claude/commands",
  "version": "1.0",
  "created_at": "2026-03-18"
}
```

## R7: "Agnostic" → "Generic" Migration Scope

**Decision**: Replace all 15+ occurrences of "agnostic" in Python source files where it refers to the agent fallback. The `StackName` literal type's "agnostic" value for stacks is a SEPARATE concept and MUST be preserved — only the agent-context "agnostic" changes to "generic".

**Rationale**: The spec requires unified terminology for the agent fallback. However, "agnostic" as a stack name (meaning "language-agnostic") is semantically correct and unrelated to agent selection.

**Files requiring agent-related changes**:
- `config.py` — `AgentName` literal: `"agnostic"` → `"generic"`
- `agent_detector.py` — fallback return: `"agnostic"` → `"generic"`
- `project.py` — `ProjectConfig.agent` default + `create()` default + `ScaffoldResult.agent_source` literal
- `prompt_manager.py` — config default dict

**Files NOT changed** (stack-related "agnostic"):
- `config.py` — `StackName` literal keeps "agnostic"
- `config.py` — `STACK_HINTS["agnostic"]` stays
- `config.py` — `AGNOSTIC_GOVERNANCE_DOMAINS` stays
- `config.py` — `GOVERNANCE_AGNOSTIC_FILE_PATTERN` stays
- `prompt_loader.py` — stack comparison `== "agnostic"` stays

## R8: Command Template Content Strategy

**Decision**: Create 8 Jinja2 templates in `src/specforge/templates/base/commands/` — one per pipeline stage. Each template uses `{{ arguments }}` as a universal placeholder token that the `CommandRegistrar` replaces with the agent-native placeholder during rendering.

**Rationale**: A universal token in templates avoids duplicating templates per agent. The registrar performs a simple string replacement after Jinja2 rendering — same approach as Spec-Kit's `convert_placeholder()`.

**Template context variables** (extending `_build_context()`):
- All existing: `project_name`, `agent`, `stack`, `date`, `stack_hint`
- New: `arguments` (set to agent's `args_placeholder` value)
- New: `architecture` (from `config.architecture`)
