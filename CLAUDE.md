# SpecForge Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-18

## Active Technologies
- Python 3.11+ + Jinja2 3.x (rendering engine), Click 8.x (existing CLI), Rich 13.x (existing output) (002-template-rendering-engine)
- File system — `.md.j2` template files in package + user project directory (002-template-rendering-engine)
- Python 3.11+ + Click 8.x (CLI framework), Rich 13.x (terminal output + interactive prompts), Jinja2 3.x (template rendering — communication map only) (004-architecture-decomposer)
- File system — `.specforge/manifest.json`, `.specforge/decompose-state.json`; atomic writes via `os.replace()` (004-architecture-decomposer)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering) — all existing (005-spec-generation-pipeline)
- File system — `.specforge/features/<slug>/` directories with JSON state files (005-spec-generation-pipeline)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (interactive prompts + terminal output), Jinja2 3.x (template rendering) — all existing (006-research-clarification-engine)
- File system — `.specforge/features/<slug>/` directories; spec.md (read/write), research.md (write), clarifications-report.md (write), manifest.json (read-only) (006-research-clarification-engine)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (output), Jinja2 3.x (template rendering), PyYAML (pattern file loading) — all existing (007-edge-case-engine)
- File system — `.specforge/features/<slug>/edge-cases.md`, YAML pattern files bundled in package (007-edge-case-engine)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering), PyYAML 6.x (pattern files) — all existing (008-task-generation-engine)
- File system — `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (write tasks.md) (008-task-generation-engine)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (prompt template rendering), GitPython 3.x (commit operations) — all existing (009-sub-agent-executor)
- File system — `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (read spec artifacts, write execution state), project source tree (write generated code) (009-sub-agent-executor)
- File system — `.specforge/features/<slug>/` for quality reports; `.quality-report.json` per service (010-quality-validation-system)
- Python 3.11+ (existing) + Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (report rendering), GitPython 3.x (commit ops) — all existing (011-implementation-orchestrator)
- File system — `.specforge/orchestration-state.json` (project-level), `.specforge/manifest.json` (read), `.specforge/features/<slug>/` (per-service state, read/write) (011-implementation-orchestrator)
- Python 3.11+ + Click 8.x (CLI), Rich 13.x (terminal rendering — Table, Panel, Progress, Tree), Jinja2 3.x (markdown report template) (012-project-status-dashboard)
- File system — `.specforge/manifest.json`, `.specforge/features/<slug>/` state files, `.specforge/.orchestration-state.json` (012-project-status-dashboard)

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
- 012-project-status-dashboard: Added Python 3.11+ + Click 8.x (CLI), Rich 13.x (terminal rendering — Table, Panel, Progress, Tree), Jinja2 3.x (markdown report template)
- 011-implementation-orchestrator: Added Python 3.11+ (existing) + Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (report rendering), GitPython 3.x (commit ops) — all existing
- 011-implementation-orchestrator: Added Python 3.11+ (existing) + Click 8.x (CLI), Rich 13.x (terminal output + progress), Jinja2 3.x (report rendering), GitPython 3.x (commit ops) — all existing



<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
