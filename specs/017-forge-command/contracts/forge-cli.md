# CLI Contract: specforge forge

## Command Signature

```
specforge forge <DESCRIPTION> [OPTIONS]
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| DESCRIPTION | string | Yes | Natural language project description |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--arch` | Choice: monolithic, microservice, modular-monolith | monolithic | Architecture type |
| `--stack` | Choice: dotnet, nodejs, python, go, java | auto-detect | Technology stack |
| `--max-parallel` | int | 4 | Maximum concurrent workers |
| `--model` | string | claude-sonnet-4-20250514 | LLM model override (HttpApiProvider only) |
| `--dry-run` | flag | false | Preview prompts without LLM calls |
| `--resume` | flag | false | Resume from interrupted run |
| `--skip-init` | flag | false | Skip auto-initialization |
| `--force` | flag | false | Overwrite existing forge state |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All services completed successfully |
| 1 | One or more services failed (partial success) |
| 2 | Fatal error (no services completed) |

## Output Files

### Always Generated
- `.specforge/forge-state.json` — Forge progress state (FR-011)
- `.specforge/reports/forge-report.md` — Completion report (FR-014)

### Per-Service (on success)
- `.specforge/features/<slug>/spec.md`
- `.specforge/features/<slug>/research.md`
- `.specforge/features/<slug>/data-model.md`
- `.specforge/features/<slug>/edge-cases.md`
- `.specforge/features/<slug>/plan.md`
- `.specforge/features/<slug>/checklist.md`
- `.specforge/features/<slug>/tasks.md`

### Dry-Run Only
- `.specforge/features/<slug>/.prompt.md` — Per-phase prompt previews (FR-015)

## Behavioral Contract

1. **Auto-init**: If `.specforge/` does not exist and `--skip-init` is not set, automatically initialize the project (FR-003).
2. **Existing state**: If `forge-state.json` exists and neither `--resume` nor `--force` is set, prompt: "Previous forge run detected. Overwrite / Resume / Abort?" (FR-020).
3. **Provider selection**: If `ANTHROPIC_API_KEY` is set and agent is "claude", use HttpApiProvider. Otherwise use SubprocessProvider (FR-008).
4. **Architecture enforcement**: Default to "monolithic" if `--arch` is not specified. If `--arch` is specified, enforce it in post-parse validation of LLM decompose output (FR-005).
5. **Ctrl+C handling**: Save in-progress work as `.draft.md`, update forge-state.json, exit with resume instructions (FR-016).

## Example Usage

```bash
# Basic monolithic project
specforge forge "Build a TODO app with user auth and task management"

# Microservice architecture with model override
specforge forge "E-commerce platform with payments, inventory, and shipping" \
  --arch microservice --model claude-opus-4-20250514

# Resume after interruption
specforge forge --resume

# Preview prompts without calling LLM
specforge forge "My App" --arch microservice --dry-run

# Force overwrite previous run
specforge forge "My App" --force
```
