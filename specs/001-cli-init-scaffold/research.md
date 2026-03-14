# Research: SpecForge CLI Init & Scaffold

**Feature**: `001-cli-init-scaffold`
**Researched**: 2026-03-14
**Domain**: Python CLI tooling — Click, Jinja2, GitPython, Rich, importlib.resources, syrupy, uv/hatchling
**Overall Confidence**: HIGH (all primary findings verified against official documentation)

---

## Summary

This document resolves all eight technical unknowns for the `specforge init` command and its supporting infrastructure. The stack is Python 3.11+, Click 8.x, Jinja2 3.x, Rich 13.x+, GitPython 3.x, hatchling build backend, and uv as the package manager and tool installer.

Every decision below is prescriptive. Alternatives were evaluated and either rejected or flagged for limited use cases. The two highest-impact decisions are: (1) using a hand-rolled `Result[T]` dataclass rather than a third-party library, and (2) using `importlib.resources.files()` for template loading rather than any path-based approach — the latter breaks inside installed wheels.

**Primary recommendation**: Keep the `Result[T]` module to ~35 lines, use `importlib.resources.files()` for all template access, test all CLI commands with `CliRunner` + `isolated_filesystem(temp_dir=tmp_path)`, and publish the package with hatchling + `[project.scripts]`.

---

## 1. Result[T] Pattern in Python

**Decision**: Hand-roll a minimal `Result[T]` generic using Python 3.11+ `dataclasses` + `typing.Generic`. Do NOT use a third-party library.

**Rationale**:
- The most popular option, `rustedpy/result`, is explicitly marked "NOT MAINTAINED" on its own GitHub repository. A personal fork exists but is described as experimental.
- The `returns` library (0.26.0) is actively maintained but is a full functional-programming toolkit (Railway-Oriented Programming, dry-monads, `IO` containers, `Future`, `@safe` decorators). It is far more surface area than a CLI scaffold tool requires and conflicts with the constitution's "zero unnecessary dependencies in core" rule.
- Python 3.11 `dataclasses` with `Generic[T, E]` gives full static type-checker support (mypy, pyright) in under 40 lines with no external dependencies.
- The Click boundary translation is trivial: check `.ok` in the command handler, then `raise click.ClickException(result.error)` or `raise SystemExit(1)`.

**Alternatives Considered**:
- `returns` (dry-python/returns 0.26.0) — rejected: too heavyweight, introduces monadic chains and `@safe` decorators into a simple CLI.
- `rustedpy/result` — rejected: not maintained.
- `rusty-results`, `resulty`, `safe-result` — rejected: all niche, low-maintenance, not worth a dependency for ~35 lines of code.
- Bare exceptions everywhere — rejected: the spec constitution explicitly requires `Result[T]` for recoverable errors; exceptions must not be used for control flow.
- `typing.Union[T, Exception]` — rejected: no `.ok` property, no structural distinction between success and error variants, poor IDE ergonomics.

**Key Pattern**:

```python
# src/specforge/result.py  (~35 lines — entire module)
from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    @property
    def ok(self) -> bool:
        return True

    def map(self, fn: Callable[[T], U]) -> "Ok[U]":
        return Ok(fn(self.value))

    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)

    def unwrap_or(self, default: T) -> T:
        return self.value


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    @property
    def ok(self) -> bool:
        return False

    def map(self, fn: Callable) -> "Err[E]":
        return self

    def bind(self, fn: Callable) -> "Err[E]":
        return self

    def unwrap_or(self, default: T) -> T:
        return default


# Type alias: imported everywhere as "Result"
# Python 3.10+ union syntax works at runtime; for 3.11 use typing.Union if needed
# type Result[T, E] = Ok[T] | Err[E]   # 3.12+ new-style
Result = Ok[T] | Err[E]  # 3.10+ compatible via __future__.annotations
```

**Click boundary translation** (all command handlers follow this pattern):

```python
# src/specforge/cli/init_cmd.py
import click
from specforge.core.scaffold import scaffold_project

@click.command("init")
@click.argument("project_name", required=False)
@click.option("--here", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
def init(project_name: str | None, here: bool, dry_run: bool, force: bool) -> None:
    result = scaffold_project(project_name, here=here, dry_run=dry_run, force=force)
    if not result.ok:
        raise click.ClickException(result.error)
    # success path handled inside scaffold_project (rich output)
```

`click.ClickException` prints `"Error: <message>"` to stderr and exits with code 1, satisfying FR-014.

---

## 2. Click Best Practices for Command Groups

**Decision**: Define a `@click.group()` in `cli/main.py`. Each subcommand lives in its own module (`cli/init_cmd.py`, `cli/check_cmd.py`, `cli/decompose_cmd.py`) and is registered with `cli.add_command()`. Shared state (dry_run, verbose) is stored in a typed `AppContext` dataclass on `ctx.obj` using `@click.pass_context` on the group and `@click.make_pass_decorator(AppContext)` on subcommands.

**Rationale**:
- Click's official "Complex Applications" guide prescribes this exact pattern: the group instantiates `ctx.obj`, subcommands receive it via a `pass_decorator` without importing each other.
- `make_pass_decorator(AppContext, ensure=True)` creates a reusable `@pass_app_ctx` decorator that is cleaner than calling `@click.pass_obj` in every command.
- Registering with `cli.add_command()` in `main.py` (rather than importing `cli` into each submodule) eliminates circular import risk.
- Each subcommand module is independently testable with `CliRunner` without booting the full group.

**Alternatives Considered**:
- `@cli.command()` inside submodules (requiring `from specforge.cli.main import cli`) — rejected: circular import between main.py and command modules.
- `ctx.ensure_object(dict)` with a plain dict — rejected: no type hints, no IDE autocomplete, violates "no magic strings" constitution rule.
- Typer — rejected: spec prescribes Click directly; Typer is a wrapper that adds runtime magic conflicting with the explicit `Result[T]` pattern.
- Single monolithic `main.py` — rejected: grows unmaintainable as commands are added in later phases.

**Key Patterns**:

Module layout:
```
src/specforge/
├── cli/
│   ├── __init__.py
│   ├── main.py          # @click.group(), registers subcommands
│   ├── init_cmd.py      # @click.command("init")
│   ├── check_cmd.py     # @click.command("check")
│   └── decompose_cmd.py # @click.command("decompose")
├── core/
│   └── scaffold.py      # pure domain logic — no click imports allowed
└── result.py
```

Shared context setup:
```python
# src/specforge/cli/main.py
from __future__ import annotations
import click
from dataclasses import dataclass
from specforge.cli import init_cmd, check_cmd, decompose_cmd


@dataclass
class AppContext:
    verbose: bool = False
    dry_run: bool = False


pass_app_ctx = click.make_pass_decorator(AppContext, ensure=True)


@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.version_option()
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    ctx.ensure_object(AppContext)
    ctx.obj.verbose = verbose


cli.add_command(init_cmd.init)
cli.add_command(check_cmd.check)
cli.add_command(decompose_cmd.decompose)
```

Subcommand receiving shared context:
```python
# src/specforge/cli/init_cmd.py
import click
from specforge.cli.main import pass_app_ctx, AppContext
from specforge.core.scaffold import scaffold_project


@click.command("init")
@click.argument("project_name", required=False)
@click.option("--here", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--no-git", is_flag=True)
@click.option("--agent", type=click.Choice(["claude","copilot","gemini","cursor","windsurf","codex"]))
@click.option("--stack", type=click.Choice(["dotnet","nodejs","python","go","java"]))
@pass_app_ctx
def init(
    app: AppContext, project_name: str | None,
    here: bool, dry_run: bool, force: bool,
    no_git: bool, agent: str | None, stack: str | None,
) -> None:
    ...
```

Testing pattern with `CliRunner` + `tmp_path`:
```python
# tests/cli/test_init_cmd.py
from click.testing import CliRunner
from specforge.cli.main import cli


def test_init_creates_specforge_directory(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "myapp"], catch_exceptions=False)
        assert result.exit_code == 0
        assert (tmp_path / "myapp" / ".specforge").is_dir()


def test_init_no_name_exits_nonzero(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code != 0
        assert "Error" in result.output


def test_dry_run_writes_no_files(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "myapp", "--dry-run"])
        assert result.exit_code == 0
        assert not (tmp_path / "myapp").exists()
```

Key notes on CliRunner:
- `isolated_filesystem(temp_dir=tmp_path)` passes pytest's managed directory; Click does NOT delete it, so pytest handles cleanup. This is the correct integration pattern (verified against Click 8.3.x testing docs).
- `catch_exceptions=False` surfaces Python exceptions as test failures rather than masking them as exit code 1.
- CliRunner is not thread-safe — do not share runner instances across parallel tests.
- Always assert `result.exit_code` first; then assert on `result.output`; in failure cases also check `result.exception`.

---

## 3. Jinja2 Template Loading from Package Data

**Decision**: Use `importlib.resources.files("specforge.templates")` (Python 3.11 stdlib) to load `.md.j2` templates. Declare template inclusion in `pyproject.toml` via Hatchling's `[tool.hatch.build.targets.wheel]` include glob.

**Rationale**:
- `pkg_resources` (setuptools) is deprecated since setuptools 67+ and adds significant import overhead on every CLI startup.
- Direct `__file__`-based `pathlib.Path` construction (`Path(__file__).parent / "templates"`) breaks when the package is installed from a zip wheel (PEP 302) or run from a frozen executable. This is the most common packaging bug in Python CLI tools.
- `importlib.resources.files()` (stable since Python 3.9, API refined in 3.11) returns a `Traversable` object that works regardless of distribution format — filesystem install, zip wheel, or editable install.
- Jinja2's `PackageLoader` also uses `importlib.resources` internally as of Jinja2 3.x, making it a viable alternative, but the raw `files()` API gives finer-grained control and is more explicit in tests.

**Alternatives Considered**:
- `pkg_resources.resource_filename()` — rejected: deprecated in setuptools 67+, heavy startup cost.
- `Path(__file__).parent / "templates"` — rejected: breaks in zip wheels and frozen executables.
- `jinja2.PackageLoader("specforge", "templates")` — viable and simpler, but delegates resource discovery to Jinja2 internally. Using `files()` directly is preferred for testability and explicitness. Either can be used; the pattern below shows both.

**Directory structure** (every template subdirectory needs `__init__.py`):
```
src/specforge/
└── templates/
    ├── __init__.py              # required — makes this a sub-package for files()
    ├── constitution.md.j2
    ├── prompts/
    │   ├── __init__.py          # required
    │   ├── architecture.prompts.md.j2
    │   ├── backend.prompts.md.j2
    │   ├── frontend.prompts.md.j2
    │   ├── database.prompts.md.j2
    │   ├── security.prompts.md.j2
    │   ├── testing.prompts.md.j2
    │   ├── cicd.prompts.md.j2
    │   └── api-design.prompts.md.j2
    └── features/
        ├── __init__.py          # required
        ├── spec-template.md.j2
        ├── plan-template.md.j2
        ├── research-template.md.j2
        ├── datamodel-template.md.j2
        ├── checklist-template.md.j2
        ├── tasks-template.md.j2
        └── edge-cases-template.md.j2
```

The `__init__.py` files in every template subdirectory are mandatory — `importlib.resources.files()` requires the anchor to be a Python package (a directory with `__init__.py`), not a plain directory.

**pyproject.toml inclusion** (Hatchling):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/specforge"]
include = [
    "src/specforge/templates/**/*.j2",
    "src/specforge/templates/**/__init__.py",
]
```

Hatchling uses VCS tracking by default; explicit globs guarantee inclusion even during development when templates might not yet be committed.

**Key Pattern** (using `files()` directly):
```python
# src/specforge/core/template_loader.py
from __future__ import annotations
from importlib.resources import files
import jinja2


def render_template(template_path: str, context: dict[str, object]) -> str:
    """
    Load and render a Jinja2 template from the specforge.templates package.

    template_path: relative path from specforge/templates/, e.g. "constitution.md.j2"
    Uses importlib.resources.files() — safe in wheels and zip imports.
    """
    # Navigate subdirectories with joinpath chaining
    traversable = files("specforge.templates").joinpath(template_path)
    source = traversable.read_text(encoding="utf-8")
    return jinja2.Template(source, keep_trailing_newline=True).render(**context)
```

For subdirectory access:
```python
# Prompts subdirectory
source = files("specforge.templates.prompts").joinpath("backend.prompts.md.j2").read_text(encoding="utf-8")
```

**Alternative using PackageLoader** (simpler, also correct):
```python
def _build_jinja_env() -> jinja2.Environment:
    # PackageLoader internally uses importlib.resources in Jinja2 3.x
    loader = jinja2.PackageLoader("specforge", "templates")
    return jinja2.Environment(loader=loader, autoescape=False, keep_trailing_newline=True)
```

---

## 4. GitPython Init + First Commit Pattern

**Decision**: Use `git.Repo.init(str(path))` to initialize, `repo.index.add(["."])` to stage all files, and `repo.index.commit("chore: init specforge scaffold")` to commit. Detect an existing parent repo by catching `git.exc.InvalidGitRepositoryError` from `git.Repo(str(target), search_parent_directories=True)`.

**Rationale**:
- GitPython 3.x provides a cross-platform Python-native API. It abstracts Windows/Unix path differences internally.
- `repo.index.add(["."])` stages all files in the working tree without enumerating them individually.
- `search_parent_directories=True` is the canonical way to detect whether a directory is already inside a git repo — it mimics `git rev-parse --show-toplevel`. When this succeeds without `InvalidGitRepositoryError`, the target is inside an existing repo.
- Per the spec edge case list, the correct behavior when inside an existing repo is to skip `Repo.init()` but still stage and commit the new `.specforge/` contents.

**Alternatives Considered**:
- `subprocess.run(["git", "init"])` — rejected: requires `git` in PATH at import time, returns raw process output instead of Python objects, harder to test, no cross-platform path safety guarantees.
- `dulwich` — rejected: pure-Python git alternative but less mature API, less community documentation, not worth the migration from GitPython.
- `pygit2` — rejected: requires `libgit2` native shared library, binary wheel dependency, heavier install.

**Key Pattern**:
```python
# src/specforge/core/git_ops.py
from __future__ import annotations
from pathlib import Path
import git
from specforge.result import Ok, Err, Result


COMMIT_MESSAGE = "chore: init specforge scaffold"


def is_inside_existing_repo(path: Path) -> bool:
    """Returns True if path is already inside a git repository."""
    try:
        git.Repo(str(path), search_parent_directories=True)
        return True
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
        return False


def init_repo(project_dir: Path) -> Result[str, str]:
    """
    Initialize git repo, stage all files, make initial commit.
    If already inside a git repo: skip init, still commit.
    """
    try:
        if is_inside_existing_repo(project_dir):
            repo = git.Repo(str(project_dir), search_parent_directories=True)
        else:
            repo = git.Repo.init(str(project_dir))
        repo.index.add(["."])
        repo.index.commit(COMMIT_MESSAGE)
        return Ok(COMMIT_MESSAGE)
    except git.exc.GitCommandError as exc:
        return Err(f"git operation failed: {exc}")
```

**Cross-platform note**: Always pass `str(path)` (not raw `pathlib.Path` objects) to GitPython methods. GitPython does not universally accept `Path` objects across all 3.x versions and on Windows this can cause silent path encoding issues.

**Known issue (2025)**: `git.Repo()` without an explicit path fails in Git worktree environments when `GIT_DIR` is set. Always pass `str(project_dir)` explicitly. (Source: GitPython issue #2022)

---

## 5. Agent Detection via PATH Scanning

**Decision**: Use `shutil.which(name)` for all agent detection. Iterate the priority list in order and return the first non-`None` result. No subprocess spawning.

**Rationale**:
- `shutil.which()` is stdlib, cross-platform, and handles `PATHEXT` on Windows automatically (finds `claude.cmd`, `claude.exe`, etc. without extra logic).
- Spawning a subprocess (`subprocess.run(["claude", "--version"])`) is heavier, may trigger agent network calls on startup, and is unnecessary for a pure existence check.
- The spec explicitly constrains detection to PATH-only (CT-003), which is exactly what `shutil.which()` does.

**Verified executable names** (researched March 2026):

| Priority | Agent | Executable | Installation | Confidence |
|---|---|---|---|---|
| 1 | `claude` | `claude` | `npm install -g @anthropic-ai/claude-code` → adds `claude` to PATH | HIGH — official Claude Code CLI docs |
| 2 | `copilot` | `copilot` | GitHub Copilot CLI GA (Feb 2026) standalone binary | HIGH — official GitHub changelog |
| 3 | `gemini` | `gemini` | `npm install -g @google/gemini-cli` → adds `gemini` to PATH | HIGH — google-gemini/gemini-cli official repo |
| 4 | `cursor` | `cursor` | "Install 'cursor' command in PATH" via Command Palette | HIGH — cursor.com/docs/cli/installation |
| 5 | `windsurf` | `windsurf` | Optional PATH install; `windsurf .` usage documented | MEDIUM — docs.windsurf.com examples |
| 6 | `codex` | `codex` | Downloaded binary renamed to `codex` after extract | MEDIUM — openai/codex GitHub README |

**Notes**:
- `copilot` replaced the deprecated `gh copilot` extension in February 2026 when the standalone GitHub Copilot CLI reached GA. The old `gh copilot` sub-extension is retired.
- Windsurf and Codex require manual PATH setup by the user and may not be present even when the tool is installed. Detection failure should produce a warning, not an error.

**Key Pattern**:
```python
# src/specforge/core/agent_detect.py
from __future__ import annotations
import shutil
from typing import Literal

AgentName = Literal["claude", "copilot", "gemini", "cursor", "windsurf", "codex", "agnostic"]

AGENT_PRIORITY: list[str] = ["claude", "copilot", "gemini", "cursor", "windsurf", "codex"]


def detect_agent() -> AgentName:
    """
    Return first agent CLI found in PATH in priority order.
    Returns "agnostic" if none found.
    shutil.which() handles PATHEXT on Windows automatically.
    """
    for name in AGENT_PRIORITY:
        if shutil.which(name) is not None:
            return name  # type: ignore[return-value]
    return "agnostic"


def agent_is_available(name: str) -> bool:
    """Check whether a specific agent CLI is present in PATH."""
    return shutil.which(name) is not None
```

Test pattern (monkeypatch — no subprocess):
```python
def test_detects_claude_when_only_claude_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude" if name == "claude" else None)
    assert detect_agent() == "claude"

def test_returns_agnostic_when_none_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert detect_agent() == "agnostic"
```

---

## 6. Snapshot Testing with pytest

**Decision**: Use `syrupy` (`syrupy-project/syrupy` package on PyPI) for snapshot testing of Jinja2-rendered Markdown output.

**Rationale**:
- Syrupy is the de-facto pytest snapshot standard as of 2025: actively maintained by the `syrupy-project` GitHub organization, clean PyPI package, widely used (Simon Willison's TIL, AWS CDK Python community, Top Hat Engineering).
- The assertion syntax `assert rendered == snapshot` is idiomatic and integrates with pytest's standard assertion rewriting.
- Syrupy **fails if a snapshot does not exist** (unlike some tools that silently create on first run). This forces explicit `--snapshot-update` on intentional changes, preventing false-positive tests.
- Snapshots are stored as human-readable Amber (`.ambr`) files in `__snapshots__/` directories alongside test files — diff-friendly in git.
- Update command is a single flag: `pytest --snapshot-update`.

**Alternatives Considered**:
- `snapshottest` (`syrusakbary/snapshottest`) — rejected: less actively maintained, API conflicts with syrupy if both installed, migration path from snapshottest → syrupy is well documented (one-way).
- `pytest-snapshot` — rejected: smaller community, fewer serializers, less active.
- Custom golden-file comparison (`assert rendered == (golden_file.read_text())`) — rejected: re-inventing syrupy with more maintenance burden and no automatic snapshot discovery.

**Key Pattern**:
```python
# tests/core/test_template_loader.py
from specforge.core.template_loader import render_template


def test_constitution_template_renders(snapshot):
    rendered = render_template(
        "constitution.md.j2",
        {"project_name": "MyApp", "agent": "claude", "stack": "python"},
    )
    assert rendered == snapshot
    # Snapshot stored in: tests/core/__snapshots__/test_template_loader.ambr


def test_prompts_architecture_template_renders(snapshot):
    rendered = render_template("prompts/architecture.prompts.md.j2", {"stack": "dotnet"})
    assert rendered == snapshot
```

**Snapshot update workflow** (for intentional template changes):
1. Modify a `.md.j2` template.
2. Run `uv run pytest --snapshot-update` — syrupy rewrites the `.ambr` file.
3. Review the diff in git; the diff shows exactly what changed in the rendered output.
4. Commit both the template change and the updated `.ambr` file together.
5. CI runs without `--snapshot-update` — any unreviewed change fails the suite.

**Installation**:
```bash
uv add --dev syrupy
```

---

## 7. pyproject.toml + uv Tool Install

**Decision**: Use `hatchling` as the build backend. Declare the CLI entry point under `[project.scripts]`. Include templates with `[tool.hatch.build.targets.wheel]` include globs. No uv-specific metadata is required.

**Rationale**:
- `hatchling` is the default build backend for `uv init`-created projects and is the recommended backend in the Python Packaging User Guide for new projects in 2025.
- `uv tool install` is the idiomatic uv distribution mechanism equivalent to `pipx install`. It requires a valid PEP 517/518 package with console entry points declared in `[project.scripts]`. No uv-specific metadata (`[tool.uv]`) is required for basic tool install.
- Hatchling includes all VCS-tracked files by default; explicit `include` globs are added to guarantee templates are bundled even if not yet committed.
- `[tool.uv.scripts]` (uv dev-only shortcuts) are NOT entry points — they create `uv run` aliases only and do not produce installable binaries.

**Alternatives Considered**:
- `setuptools` as build backend — rejected: more verbose configuration, legacy ecosystem; hatchling is simpler for a new src-layout project.
- `flit` — rejected: does not support `src/` layout without manual path configuration; less flexible for non-Python data files.
- `[tool.uv.scripts]` for the entry point — rejected: these are dev-only shortcuts, not installed binaries.
- `uv_build` backend — viable but less community documentation than hatchling; hatchling is the more established choice.

**Complete minimal pyproject.toml**:
```toml
[project]
name = "specforge"
version = "0.1.0"
description = "Scaffold spec-driven development projects with AI agent support"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
    "jinja2>=3.1.0",
    "rich>=13.0.0",
    "gitpython>=3.1.40",
]

[project.scripts]
specforge = "specforge.cli.main:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/specforge"]
include = [
    "src/specforge/templates/**/*.j2",
    "src/specforge/templates/**/__init__.py",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "syrupy>=4.0.0",
    "ruff>=0.4.0",
]
```

**Entry point mechanics**: `"specforge.cli.main:cli"` resolves to `from specforge.cli.main import cli; sys.exit(cli())`. Click group objects are directly callable, so no wrapper function is needed.

**Install commands**:
```bash
# Development (editable, entry point available immediately):
uv pip install -e .

# End-user: install from PyPI (after publishing):
uv tool install specforge

# End-user: install from local wheel build:
uv build
uv tool install dist/specforge-0.1.0-py3-none-any.whl

# End-user: install from git before PyPI publish:
uv tool install git+https://github.com/<org>/specforge
```

---

## 8. Cross-Platform File Tree Preview (--dry-run)

**Decision**: Collect all planned writes as a flat `list[tuple[str, str]]` (relative_path, kind) first — no filesystem writes. If `--dry-run`, pass this list to `build_rich_tree()` which creates a `rich.tree.Tree` by splitting paths on separators and nesting branches. Print and return without touching the filesystem or git.

**Rationale**:
- Building a "plan" list before executing separates concerns cleanly: dry-run becomes a single `if dry_run: print_tree(planned); return` gate with zero special-case logic in the scaffolding code.
- The same planned-files list drives both the dry-run preview and the actual writes — there is no duplication.
- `rich.tree.Tree.add()` returns the newly created branch as a `Tree` object, enabling recursive nesting of arbitrary depth without a stack.
- Rich handles cross-platform terminal width, color codes, Unicode box-drawing characters, and Windows console output automatically.

**Alternatives Considered**:
- Write files then delete them for dry-run — rejected: filesystem side effects are visible (e.g., git picks them up, other processes see them); fundamentally wrong semantics.
- `directory-tree` PyPI package — rejected: walks the real filesystem, not a planned file list; wrong for dry-run.
- Custom ANSI tree printing (`print("├── file.txt")`) — rejected: fragile cross-platform, Rich already handles this correctly.

**Key Pattern**:
```python
# src/specforge/core/scaffold.py

from __future__ import annotations
from pathlib import PurePosixPath
from rich.tree import Tree
from rich.console import Console

# (relative_path_from_project_root, "dir" | "file")
PlannedItem = tuple[str, str]


def build_rich_tree(project_name: str, planned: list[PlannedItem]) -> Tree:
    """
    Convert a flat list of planned relative paths into a Rich Tree.
    Directories must appear before their children in planned.
    """
    root = Tree(f"[bold blue]{project_name}/[/bold blue]")
    branches: dict[str, Tree] = {"": root}

    for rel_path, kind in planned:
        parts = PurePosixPath(rel_path).parts
        parent_key = "/".join(parts[:-1])
        parent_branch = branches.get(parent_key, root)
        label = f"[bold cyan]{parts[-1]}/[/bold cyan]" if kind == "dir" else parts[-1]
        branch = parent_branch.add(label)
        if kind == "dir":
            branches["/".join(parts)] = branch

    return root


def print_dry_run(project_name: str, planned: list[PlannedItem]) -> None:
    console = Console()
    console.print("\n[yellow bold]Dry run — no files will be written.[/yellow bold]")
    console.print(f"Would create {len([p for p in planned if p[1] == 'file'])} files:\n")
    console.print(build_rich_tree(project_name, planned))
```

Usage in the scaffold orchestrator:
```python
def scaffold_project(project_name: str, *, dry_run: bool, ...) -> Result[str, str]:
    planned = _collect_planned_files(project_name, agent, stack)  # pure, no I/O
    if dry_run:
        print_dry_run(project_name, planned)
        return Ok("dry-run complete")
    return _execute_scaffold(planned, target_dir)
```

**Rich Tree API note**: `tree.add(label)` returns a new `Tree` branch. Style parameters available on `Tree()` and `add()`: `style` (applies to branch text), `guide_style` (applies to connector lines). All standard Rich markup (`[bold]`, `[blue]`, `[red]`) is valid in labels.

---

## Sources

### Primary (HIGH confidence — verified against official docs)

- [Python 3.11 importlib.resources docs](https://docs.python.org/3.11/library/importlib.resources.html) — `files()` API, Traversable, joinpath
- [Click 8.3.x Testing docs](https://click.palletsprojects.com/en/stable/testing/) — CliRunner, `isolated_filesystem(temp_dir=)`, exit codes
- [Click 8.3.x Complex Applications](https://click.palletsprojects.com/en/stable/complex/) — AppContext, `pass_obj`, `make_pass_decorator`
- [Rich Tree docs (14.x)](https://rich.readthedocs.io/en/latest/tree.html) — `Tree.add()`, guide_style, nesting
- [Hatchling build config](https://hatch.pypa.io/latest/config/build/) — include globs, `[tool.hatch.build.targets.wheel]`
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.scripts]`, build-system
- [GitPython quickstart 3.1.46](https://gitpython.readthedocs.io/en/stable/quickstart.html) — `Repo.init`, `index.add`, `index.commit`
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) — executable name `claude`
- [Gemini CLI official repo](https://github.com/google-gemini/gemini-cli) — executable name `gemini`, `npm install -g @google/gemini-cli`
- [GitHub Copilot CLI GA changelog (Feb 2026)](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/) — executable name `copilot`, standalone binary
- [Cursor CLI installation docs](https://cursor.com/docs/cli/installation) — executable name `cursor`, "Install cursor command in PATH"
- [Syrupy GitHub (syrupy-project org)](https://github.com/syrupy-project/syrupy) — assertion syntax, `--snapshot-update`, Amber format

### Secondary (MEDIUM confidence — verified with multiple community sources)

- [GitPython issue #2022](https://github.com/gitpython-developers/gitpython/issues/2022) — confirmed explicit path workaround for Git worktrees
- [GitPython `search_parent_directories` discussion](https://github.com/gitpython-developers/GitPython/discussions/1135) — confirmed `InvalidGitRepositoryError` usage pattern
- Windsurf `windsurf` executable name — confirmed via docs.windsurf.com examples and multiple setup guides; no single authoritative PATH install page found
- OpenAI Codex `codex` executable name — confirmed via openai/codex GitHub README binary rename instructions
- [uv tool concepts docs](https://docs.astral.sh/uv/concepts/tools/) — `uv tool install` requires console entry points; no uv-specific metadata needed

### Low confidence (verify before implementation)

- The `copilot` standalone executable PATH behavior on Windows (installer adds to PATH automatically per Linux/Mac docs; Windows behavior not explicitly documented — worth a smoke test during Windows CI setup)
- Windsurf and Codex PATH availability — both require manual setup by the user; detection failure rate in the wild is unknown
