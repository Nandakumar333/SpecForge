# Data Model: SpecForge CLI Init & Scaffold

**Feature**: `002-cli-init-scaffold` | **Date**: 2026-03-14

---

## Overview

All domain types live in `src/specforge/core/`. No type in `core/` imports from `cli/` or `plugins/`. Serialization is not required — these are in-process Python dataclasses.

---

## Enumerations & Literals

### `AgentName`
```python
# src/specforge/core/config.py
AgentName = Literal["claude", "copilot", "gemini", "cursor", "windsurf", "codex", "agnostic"]

AGENT_PRIORITY: list[AgentName] = [
    "claude", "copilot", "gemini", "cursor", "windsurf", "codex"
]

# Executable names to probe via shutil.which()
AGENT_EXECUTABLES: dict[AgentName, list[str]] = {
    "claude":   ["claude"],
    "copilot":  ["gh-copilot", "copilot"],
    "gemini":   ["gemini"],
    "cursor":   ["cursor"],
    "windsurf": ["windsurf"],
    "codex":    ["codex"],
}
```

**Note on agent executables**: `claude` maps to `claude` (Anthropic CLI); `copilot` probes `gh-copilot` first then `copilot`; others map directly. Confirm actual binary names in research.md §AgentDetection before implementation.

### `StackName`
```python
StackName = Literal["dotnet", "nodejs", "python", "go", "java", "agnostic"]

SUPPORTED_STACKS: list[StackName] = ["dotnet", "nodejs", "python", "go", "java"]
# "agnostic" is the default when --stack is omitted
```

---

## Core Domain Types

### `ProjectConfig`
```python
@dataclass(frozen=True)
class ProjectConfig:
    name: str                    # Validated: [a-zA-Z0-9_-]+
    target_dir: Path             # Resolved absolute path
    agent: AgentName             # Explicit or auto-detected
    stack: StackName             # Explicit or "agnostic"
    no_git: bool                 # Skip git init/commit
    force: bool                  # Allow existing dir / .specforge/
    dry_run: bool                # Preview only — no writes
    here: bool                   # Scaffold into CWD, no subdirectory
```

**Validation rules**:
- `name` matches `^[a-zA-Z0-9_-]+$` (FR-015); error on mismatch
- `name` is required unless `here=True`; mutually exclusive with `here`
- `target_dir` is always absolute (resolved from CWD at CLI layer)

### `ScaffoldFile`
```python
@dataclass(frozen=True)
class ScaffoldFile:
    relative_path: Path          # e.g., Path(".specforge/constitution.md")
    template_name: str           # e.g., "constitution.md.j2"
    context: dict[str, Any]      # Variables passed to Jinja2 render
```

**Note**: `relative_path` is always relative to `target_dir`. The scaffold writer resolves `target_dir / file.relative_path` before writing.

### `ScaffoldPlan`
```python
@dataclass(frozen=True)
class ScaffoldPlan:
    config: ProjectConfig
    files: list[ScaffoldFile]    # Ordered deterministically — directories before files
    directories: list[Path]      # Relative paths for mkdir (created before files)
```

**Directory creation order** (always created in this order):
```
.specforge/
.specforge/memory/
.specforge/features/
.specforge/prompts/
.specforge/scripts/
.specforge/templates/features/
```

**File ordering**: All directories first, then all files sorted by `relative_path`.

### `ScaffoldResult`
```python
@dataclass
class ScaffoldResult:
    plan: ScaffoldPlan
    written: list[Path]          # Absolute paths actually written
    skipped: list[Path]          # Absolute paths skipped (existed + force=True)
    git_committed: bool          # Whether initial commit was created
    agent_source: Literal["explicit", "auto-detected", "agnostic"]
```

### `DetectionResult`
```python
@dataclass(frozen=True)
class DetectionResult:
    agent: AgentName
    source: Literal["explicit", "auto-detected", "agnostic"]
    executable: str | None       # The binary name that was found, if auto-detected
```

### `CheckResult`
```python
@dataclass(frozen=True)
class CheckResult:
    tool: str                    # Display name (e.g., "git", "python", "uv")
    found: bool
    version: str | None          # Version string if detectable, else None
    install_hint: str            # Always populated — shown when found=False
```

**Prerequisite list** (FR-011):
```python
PREREQUISITES: list[str] = ["git", "python", "uv"]
# Agent CLI added dynamically when --agent flag is present
```

---

## Result Wrapper

```python
# src/specforge/core/result.py

from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    def map(self, fn: Callable[[T], U]) -> "Ok[U]": ...
    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]": ...
    def unwrap_or(self, default: T) -> T: return self.value
    @property
    def ok(self) -> bool: return True

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    def map(self, fn: Callable) -> "Err[E]": return self
    def bind(self, fn: Callable) -> "Err[E]": return self
    def unwrap_or(self, default: T) -> T: return default
    @property
    def ok(self) -> bool: return False

Result = Ok[T] | Err[E]
```

**Usage contract**:
- `core/` functions return `Result[T, str]` where `str` is a human-readable error message
- `cli/` layer calls `.ok` to branch; on `Err` prints via Rich and calls `sys.exit(1)`
- No `raise` for recoverable errors anywhere in `core/`

---

## State Transitions

### Init Command — Target Directory State Machine

```
[ABSENT]
    │  specforge init NAME
    ▼
[CREATED] ── git init + commit ──► [COMMITTED]

[EXISTS, no .specforge/]
    │  specforge init NAME --force
    ▼
[MERGED] ── git init + commit ──► [COMMITTED]

[EXISTS, no .specforge/] + no --force
    └──► ERROR: "Directory exists. Use --force to scaffold into it."

[EXISTS, has .specforge/] + --here + --force
    └──► [MERGED: only missing files written; existing preserved]

[EXISTS, has .specforge/] + --here + no --force
    └──► ERROR: ".specforge/ already exists. Use --force to add missing files."
```

### Agent Detection State Machine

```
--agent EXPLICIT ──► DetectionResult(agent=explicit, source="explicit")

PATH scan:
  claude in PATH?  → DetectionResult(agent="claude",   source="auto-detected")
  copilot in PATH? → DetectionResult(agent="copilot",  source="auto-detected")
  gemini in PATH?  → DetectionResult(agent="gemini",   source="auto-detected")
  cursor in PATH?  → DetectionResult(agent="cursor",   source="auto-detected")
  windsurf?        → DetectionResult(agent="windsurf", source="auto-detected")
  codex?           → DetectionResult(agent="codex",    source="auto-detected")
  none found       → DetectionResult(agent="agnostic", source="agnostic")
```

---

## Template Context Variables

Jinja2 context passed to every template render:

```python
{
    "project_name": config.name,       # str
    "agent":        config.agent,      # AgentName
    "stack":        config.stack,      # StackName
    "date":         "2026-03-14",      # ISO date string at scaffold time
    "is_agnostic":  config.agent == "agnostic",
    "stack_hints":  STACK_HINTS[config.stack],  # dict of stack-specific strings
}
```

**`STACK_HINTS`** (in `config.py`):
```python
STACK_HINTS: dict[StackName, dict[str, str]] = {
    "agnostic": {"lang": "",          "test_tool": "",       "pkg_tool": ""},
    "dotnet":   {"lang": "C#/.NET",   "test_tool": "xunit",  "pkg_tool": "dotnet"},
    "nodejs":   {"lang": "TypeScript","test_tool": "vitest", "pkg_tool": "npm"},
    "python":   {"lang": "Python",    "test_tool": "pytest", "pkg_tool": "uv"},
    "go":       {"lang": "Go",        "test_tool": "go test","pkg_tool": "go mod"},
    "java":     {"lang": "Java",      "test_tool": "JUnit",  "pkg_tool": "maven"},
}
```
