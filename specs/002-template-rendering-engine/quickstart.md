# Quickstart: Template Rendering Engine

**Feature**: `002-template-rendering-engine`
**Date**: 2026-03-14

## Prerequisites

- Python 3.11+
- `uv` package manager
- SpecForge installed: `uv tool install specforge`

## Development Setup

```bash
# Clone and enter
git clone <repo-url> && cd SpecForge
git checkout 002-template-rendering-engine

# Install dev dependencies
uv sync --dev

# Run existing tests (should all pass before changes)
uv run pytest

# Lint
uv run ruff check src/ tests/
```

## Key Files to Understand First

1. **`src/specforge/core/template_loader.py`** — Current rendering engine (being replaced)
2. **`src/specforge/core/scaffold_builder.py`** — Current template assembly (being modified)
3. **`src/specforge/core/config.py`** — Constants and type definitions
4. **`src/specforge/templates/`** — All Jinja2 template files
5. **`tests/snapshots/test_template_rendering.py`** — Snapshot tests for template output

## Implementation Order

### Phase 1: Core Modules (no breaking changes)

Build new modules alongside existing code:

```bash
# 1. StackAdapter (zero dependencies on existing code)
src/specforge/core/stack_adapter.py
tests/unit/test_stack_adapter.py

# 2. TemplateValidator (zero dependencies on existing code)
src/specforge/core/template_validator.py
tests/unit/test_template_validator.py

# 3. TemplateRegistry (depends on config.py only)
src/specforge/core/template_registry.py
tests/unit/test_template_registry.py

# 4. TemplateRenderer (depends on registry + validator)
src/specforge/core/template_renderer.py
tests/unit/test_template_renderer.py
```

### Phase 2: Templates

```bash
# Create new directory structure
src/specforge/templates/base/
src/specforge/templates/base/partials/
src/specforge/templates/base/prompts/
src/specforge/templates/base/features/

# Create base prompt template + stack variants
# Create new feature templates (checklist, edge-cases)
# Migrate existing templates to base/ subdirectory
```

### Phase 3: Integration

```bash
# Wire scaffold_builder to use registry
# Wire scaffold_writer to use renderer + validator
# Update config.py constants
# Deprecate template_loader.py
```

### Phase 4: Cleanup

```bash
# Remove old template locations
# Update all snapshot tests
# Remove template_loader.py
```

## Running Tests

```bash
# All tests
uv run pytest

# Specific module tests
uv run pytest tests/unit/test_template_registry.py -v
uv run pytest tests/unit/test_template_renderer.py -v

# Snapshot tests (update after template changes)
uv run pytest tests/snapshots/ --snapshot-update

# Coverage
uv run pytest --cov=specforge --cov-report=term-missing
```

## Common Tasks

### Adding a new stack variant

1. Create `src/specforge/templates/base/prompts/{prompt}.{stack}.md.j2`
2. Add `{% extends "base/prompts/{prompt}.md.j2" %}` at top
3. Override desired blocks
4. Add stack context in `stack_adapter.py`
5. Run `uv run pytest --snapshot-update`

### Adding a user-override template

1. Place `.specforge/templates/prompts/backend.md.j2` in the project
2. TemplateRegistry auto-discovers it on next render
3. No configuration changes needed

### Adding a new custom filter

1. Add filter function in `template_renderer.py`
2. Register on the Jinja2 Environment: `env.filters["filter_name"] = fn`
3. Add unit test in `test_template_renderer.py`
