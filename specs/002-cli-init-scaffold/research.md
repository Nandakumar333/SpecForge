# Research: SpecForge CLI Init & Scaffold

**Feature**: `002-cli-init-scaffold` | **Date**: 2026-03-14

All unknowns from the Technical Context have been resolved. No NEEDS CLARIFICATION items remain.

---

## Result[T] Pattern in Python

**Decision**: Custom generic dataclass — `Ok[T]` / `Err[E]` — no third-party library.

**Rationale**: The constitution explicitly prohibits unnecessary dependencies in `core/`. A third-party `Result` library (e.g., `returns`, `result`) would introduce an external dependency into the zero-dependency core. Python 3.11+ dataclasses with `Generic[T]` and `TypeVar` provide everything needed. The custom implementation is ~30 lines and fully typed.

**Alternatives Considered**:
- `returns` library: well-designed but adds a dependency; overkill for this use case
- `result` library (Rust-inspired): same concern
- `raise` exceptions: prohibited by constitution for recoverable errors in core

**Key Pattern**:
```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    def map(self, fn: Callable[[T], U]) -> "Ok[U]":
        return Ok(fn(self.value))
    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)
    def unwrap_or(self, default: T) -> T:
        return self.value
    @property
    def ok(self) -> bool:
        return True

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    def map(self, fn: Callable) -> "Err[E]":
        return self
    def bind(self, fn: Callable) -> "Err[E]":
        return self
    def unwrap_or(self, default: T) -> T:
        return default
    @property
    def ok(self) -> bool:
        return False

Result = Ok[T] | Err[E]
```

CLI integration pattern:
```python
# cli/init_cmd.py
result = scaffold_project(config)
if not result.ok:
    console.print(f"[red]Error:[/red] {result.error}", err=True)
    raise SystemExit(1)
```

---

## Click Command Group Structure

**Decision**: Subcommand modules each define a `@click.command()` function; `main.py` imports and registers them via `cli.add_command()`. Shared state (dry_run, verbose) passed via `@click.pass_context` with a `CliContext` dataclass stored on `ctx.obj`.

**Rationale**: Avoids circular imports. Each command module is independently testable with `CliRunner`. The `ctx.obj` pattern is idiomatic Click for shared state rather than global variables (which would violate the constitution).

**Alternatives Considered**:
- Single monolithic `main.py`: grows unwieldy; harder to test individual commands in isolation
- Decorating with `@cli.command()` in submodules: requires importing `cli` group into submodules, creating circular import risk

**Key Pattern**:
```python
# cli/main.py
import click
from specforge.cli.init_cmd import init
from specforge.cli.check_cmd import check
from specforge.cli.decompose_cmd import decompose

@click.group()
@click.version_option()
@click.pass_context
def cli(ctx: click.Context) -> None:
    ctx.ensure_object(dict)

cli.add_command(init)
cli.add_command(check)
cli.add_command(decompose)
```

Testing pattern:
```python
# tests/integration/test_init_cmd.py
from click.testing import CliRunner
from specforge.cli.main import cli

def test_init_creates_directory(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "myapp"], catch_exceptions=False,
                           env={"HOME": str(tmp_path)})
    assert result.exit_code == 0
    assert (tmp_path / "myapp" / ".specforge").is_dir()
```

---

## Jinja2 Template Loading from Package Data

**Decision**: `importlib.resources.files("specforge.templates")` — Python 3.11+ native API. Templates declared in `pyproject.toml` under `[tool.setuptools.package-data]`.

**Rationale**: `importlib.resources.files()` is the stable, forward-compatible API introduced in Python 3.9 and improved in 3.11. It works correctly whether the package is installed as a wheel, editable install, or run from source. `pkg_resources` is deprecated. Direct `__file__`-based path resolution breaks in zipimport scenarios.

**Alternatives Considered**:
- `pkg_resources.resource_filename`: deprecated; replaced by importlib.resources
- `Path(__file__).parent / "templates"`: works for source layout but fragile with wheels

**Key Pattern**:
```python
# core/project.py
from importlib.resources import files
import jinja2

def _build_jinja_env() -> jinja2.Environment:
    template_root = files("specforge.templates")
    loader = jinja2.PackageLoader("specforge", "templates")
    return jinja2.Environment(loader=loader, autoescape=False, keep_trailing_newline=True)
```

pyproject.toml declaration:
```toml
[tool.setuptools.package-data]
"specforge.templates" = ["**/*.j2"]
"specforge.templates.prompts" = ["**/*.j2"]
"specforge.templates.features" = ["**/*.j2"]
```

---

## GitPython Init + First Commit

**Decision**: `Repo.init(path)` → `repo.index.add(["."])` → `repo.index.commit("chore: init specforge scaffold")`. Handle existing git repo by checking `Repo(path, search_parent_directories=True)` before init.

**Rationale**: GitPython is already in the dependency list. The pattern is straightforward and cross-platform. The "existing git repo" edge case (spec §Edge Cases) is handled by attempting `Repo(path, search_parent_directories=True)` — if it succeeds, we're already in a git repo and skip `init` but still commit.

**Alternatives Considered**:
- `subprocess.run(["git", "init"])`: works but harder to test and less portable; GitPython already in stack
- dulwich: pure-Python git but less mature API

**Key Pattern**:
```python
# core/project.py
from git import Repo, InvalidGitRepositoryError

def init_git(target_dir: Path, commit_message: str) -> Result[str, str]:
    try:
        try:
            repo = Repo(str(target_dir), search_parent_directories=False)
        except InvalidGitRepositoryError:
            repo = Repo.init(str(target_dir))
        repo.index.add(all=True)
        repo.index.commit(commit_message)
        return Ok("committed")
    except Exception as e:
        return Err(f"Git operation failed: {e}")
```

**Commit message** (from spec clarification): `"chore: init specforge scaffold"`

---

## Agent Detection via PATH Scanning

**Decision**: `shutil.which(executable)` iterated over `AGENT_EXECUTABLES` in `AGENT_PRIORITY` order. Returns `DetectionResult` with first match; returns agnostic if none found.

**Rationale**: `shutil.which()` is stdlib, cross-platform, and handles PATH correctly on Windows (checking `.exe`, `.cmd` extensions automatically). No subprocess spawning needed for detection — just existence check.

**Known executable names** (best-effort; may need updates as agents evolve):

| Agent | Executables to probe |
|-------|---------------------|
| `claude` | `["claude"]` — Anthropic Claude CLI |
| `copilot` | `["gh-copilot", "copilot"]` — GitHub Copilot CLI extension |
| `gemini` | `["gemini"]` — Google Gemini CLI |
| `cursor` | `["cursor"]` — Cursor editor CLI |
| `windsurf` | `["windsurf"]` — Windsurf editor CLI |
| `codex` | `["codex"]` — OpenAI Codex CLI |

**Key Pattern**:
```python
# core/agent_detector.py
import shutil
from specforge.core.config import AGENT_PRIORITY, AGENT_EXECUTABLES, AgentName

def detect_agent() -> DetectionResult:
    for agent in AGENT_PRIORITY:
        for executable in AGENT_EXECUTABLES[agent]:
            if shutil.which(executable) is not None:
                return DetectionResult(agent=agent, source="auto-detected", executable=executable)
    return DetectionResult(agent="agnostic", source="agnostic", executable=None)
```

Test pattern (monkeypatch):
```python
def test_detects_claude_when_only_claude_in_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude" if name == "claude" else None)
    result = detect_agent()
    assert result.agent == "claude"
    assert result.source == "auto-detected"
```

---

## Snapshot Testing with pytest

**Decision**: syrupy — best maintenance story and most active development.

**Rationale**: syrupy integrates cleanly with pytest via fixtures, auto-generates snapshot files on first run, and uses a clear `--snapshot-update` flag for intentional changes. The amber serializer produces readable inline snapshots. pytest-snapshot is less maintained. Custom solutions add unnecessary overhead.

**Alternatives Considered**:
- `pytest-snapshot`: less active; fewer serializers
- Custom file comparison: works but requires manual snapshot management

**Key Pattern**:
```python
# tests/snapshots/test_template_rendering.py
def test_constitution_template_renders(snapshot):
    env = _build_jinja_env()
    template = env.get_template("constitution.md.j2")
    rendered = template.render(project_name="myapp", agent="claude", stack="python", ...)
    assert rendered == snapshot
```

Update snapshots: `uv run pytest --snapshot-update`

---

## pyproject.toml + uv tool install

**Decision**: Standard `[project.scripts]` entry point with `uv tool install --from git+...` as primary install path.

**Rationale**: `uv tool install` is the idiomatic uv distribution mechanism equivalent to `pipx install`. It requires a valid PEP 517 package with `[project.scripts]`. No uv-specific metadata is required beyond standard `pyproject.toml`.

**Key Pattern**:
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "specforge"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "jinja2>=3.1",
    "rich>=13.0",
    "gitpython>=3.1",
]

[project.scripts]
specforge = "specforge.cli.main:cli"

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "syrupy", "ruff"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"specforge.templates" = ["**/*.j2"]
```

Install command (from spec):
```bash
uv tool install specforge --from git+https://github.com/<org>/specforge
```

---

## --dry-run File Tree Preview

**Decision**: Build `ScaffoldPlan` (list of `ScaffoldFile` tuples) first without writing; then render via `rich.tree.Tree` if `dry_run=True`, skipping all filesystem writes and git operations.

**Rationale**: Separating "plan building" from "plan execution" (the `ScaffoldPlan` dataclass) makes dry-run a trivial flag — the same plan-building logic runs for both normal and dry-run; only the execution step branches. Rich's `Tree` widget handles nested directory display natively.

**Key Pattern**:
```python
# cli/init_cmd.py (dry-run branch)
if config.dry_run:
    tree = Tree(f"[bold]{config.name}/[/bold]")
    _build_rich_tree(tree, plan.files)
    console.print(tree)
    console.print("\n[yellow]No files were written.[/yellow]")
    return

# Normal execution
result = execute_scaffold(plan)
```
