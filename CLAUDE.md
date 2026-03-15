# SpecForge Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-14

## Active Technologies
- Python 3.11+ + Jinja2 3.x (rendering engine), Click 8.x (existing CLI), Rich 13.x (existing output) (002-template-rendering-engine)
- File system — `.md.j2` template files in package + user project directory (002-template-rendering-engine)

- **Language**: Python 3.11+
- **CLI Framework**: Click 8.x — command groups, `@click.pass_context`, `CliRunner` for tests
- **Template Engine**: Jinja2 3.x — all file output via `.md.j2` templates; no string concat for file generation
- **Terminal Output**: Rich 13.x — `rich.tree.Tree` for dry-run preview, `rich.table.Table` for check output, `rich.console.Console` for all prints
- **Git Operations**: GitPython 3.x — `Repo.init()`, `repo.index.add()`, `repo.index.commit()`
- **Path Operations**: `pathlib.Path` exclusively — no `os.path`
- **Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)
- **Packaging**: `pyproject.toml` + `uv`; entry point `specforge = "specforge.cli.main:cli"`

## Project Structure

```text
src/specforge/
├── __init__.py
├── __main__.py
├── cli/
│   ├── main.py                # Click group root
│   ├── init_cmd.py            # specforge init
│   ├── check_cmd.py           # specforge check
│   ├── decompose_cmd.py       # specforge decompose
│   └── validate_prompts_cmd.py # specforge validate-prompts (Feature 003)
├── core/
│   ├── config.py              # All constants — GOVERNANCE_DOMAINS, PRECEDENCE_ORDER, EQUAL_PRIORITY_DOMAINS
│   ├── result.py              # Result[T, E] = Ok[T] | Err[E]
│   ├── project.py             # ProjectConfig + ScaffoldPlan
│   ├── scaffold_builder.py    # Plan builder + governance file generation
│   ├── scaffold_writer.py     # File writer for scaffold plans
│   ├── agent_detector.py      # shutil.which() PATH scanner
│   ├── stack_detector.py      # StackDetector — marker-based stack auto-detection
│   ├── prompt_models.py       # Frozen dataclasses: PromptRule, PromptFile, PromptSet, ConflictReport, etc.
│   ├── prompt_manager.py      # PromptFileManager — generate/CRUD governance files
│   ├── prompt_loader.py       # PromptLoader — load all 7 governance files into PromptSet
│   ├── prompt_validator.py    # PromptValidator — cross-file threshold conflict detection
│   ├── prompt_context.py      # PromptContextBuilder — build agent context string
│   ├── template_models.py     # TemplateType, TemplateInfo, TemplateVarSchema
│   ├── template_registry.py   # TemplateRegistry — discovers built-in + user templates
│   ├── template_renderer.py   # Jinja2 rendering engine
│   └── template_loader.py     # Low-level Jinja2 loader
├── templates/
│   ├── base/
│   │   ├── constitution.md.j2
│   │   ├── governance/        # Governance prompt templates (backend.dotnet.md.j2, etc.)
│   │   ├── prompts/           # Agent-operation prompt templates (app-analyzer, etc.)
│   │   ├── features/          # 7 per-feature templates
│   │   └── partials/          # Shared template fragments
│   └── ...
└── plugins/
    └── agents/           # One module per agent (claude, copilot, gemini, cursor, windsurf, codex)

tests/
├── unit/                 # Core logic — no filesystem I/O
├── integration/          # CLI commands with tmp_path + CliRunner
└── snapshots/            # syrupy snapshot tests for template rendering
```

## Commands

```bash
# Install
uv tool install specforge --from git+https://github.com/<org>/specforge

# Run tests
uv run pytest
uv run pytest --cov=specforge --cov-report=term-missing

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Update snapshots
uv run pytest --snapshot-update
```

## Code Style

- Strict type hints on every function signature — no `Any` without explicit comment
- Functions ≤ 30 lines; classes ≤ 200 lines (enforced by constitution)
- `Result[T, E]` for all recoverable errors in `core/` — no `raise` for control flow
- All constants and paths in `core/config.py` — no magic strings anywhere
- Constructor injection for all dependencies — no global state
- Dependency flow: `cli` → `core` → stdlib only; `plugins` → `core`; never reverse

## Recent Changes
- 003-agent-prompt-governance: Governance prompt file system — `PromptFileManager`, `PromptLoader`, `PromptValidator`, `PromptContextBuilder`; `specforge validate-prompts` CLI command; `TemplateType.governance`; `.specforge/config.json`; SHA-256 checksum-based customization detection; structured Markdown parsing via `re` (zero new external deps)

- 002-template-rendering-engine: Added Python 3.11+ + Jinja2 3.x (rendering engine), Click 8.x (existing CLI), Rich 13.x (existing output)

- **001-cli-init-scaffold** (2026-03-14): Core CLI scaffold — `init`, `check`, `decompose` commands; `Result[T]` pattern; agent auto-detection; Jinja2 template system; GitPython init + commit; `--dry-run` support

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
