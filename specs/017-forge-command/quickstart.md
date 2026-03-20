# Quickstart: Forge Command

## Prerequisites

- Python 3.11+
- SpecForge installed (`uv tool install specforge`)
- One of:
  - `ANTHROPIC_API_KEY` environment variable set (fastest — direct HTTP API)
  - Claude CLI installed (`claude` on PATH)
  - Any supported AI agent CLI installed (copilot, gemini, codex)

## Basic Usage

```bash
# Generate specs for a monolithic app (default)
specforge forge "Build a task management app with user auth, projects, and notifications"

# Generate specs for a microservice architecture
specforge forge "E-commerce platform with product catalog, cart, payments, and shipping" \
  --arch microservice

# Preview what would be generated (no LLM calls)
specforge forge "My App" --dry-run
```

## Setting Up the HTTP API Provider

The forge command makes 56+ LLM calls for a multi-service project. The HTTP API provider is 3x faster than the subprocess provider.

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# The forge command automatically uses the HTTP provider when the key is set
specforge forge "My App" --arch microservice
```

## Resuming an Interrupted Run

```bash
# If forge is interrupted (Ctrl+C, network loss, etc.)
specforge forge --resume

# Force overwrite a previous run
specforge forge "My App" --force
```

## Output Structure

After a successful forge run:

```
.specforge/
├── manifest.json              # Service decomposition
├── forge-state.json           # Forge run state (for resume)
├── reports/
│   └── forge-report.md        # Completion report
└── features/
    ├── auth-service/
    │   ├── spec.md
    │   ├── research.md
    │   ├── data-model.md
    │   ├── edge-cases.md
    │   ├── plan.md
    │   ├── checklist.md
    │   └── tasks.md
    ├── product-service/
    │   └── ... (same 7 artifacts)
    └── payment-service/
        └── ... (same 7 artifacts)
```

## Common Options

| Option | Description |
|--------|-------------|
| `--arch microservice` | Decompose into multiple services |
| `--max-parallel 8` | Increase concurrent workers (default: 4) |
| `--model claude-opus-4-20250514` | Use a different model for higher quality |
| `--dry-run` | Preview prompts without LLM calls |
| `--resume` | Continue from an interrupted run |
| `--skip-init` | Require existing `.specforge/` directory |

## Development Setup

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/unit/test_forge_orchestrator.py -v
uv run pytest tests/unit/test_forge_state.py -v
uv run pytest tests/unit/test_artifact_extractor.py -v
uv run pytest tests/unit/test_enriched_prompts.py -v
uv run pytest tests/integration/test_forge_end_to_end.py -v

# Run all tests with coverage
uv run pytest --cov=specforge --cov-report=term-missing
```
