# CLI Contract: Feature 003 Additions

**Branch**: `003-agent-prompt-governance` | **Date**: 2026-03-15
**Extends**: `specs/002-cli-init-scaffold/contracts/cli-commands.md`

---

## New Command: `specforge validate-prompts`

### Invocation

```
specforge validate-prompts [OPTIONS]
```

### Description

Scans all governance prompt files in `.specforge/prompts/` for conflicting
threshold rules. Reports every conflict with source files, values, the winning
file per precedence, and a suggested resolution.

Must be run from a directory containing `.specforge/` (initialized project).

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--prompts-dir PATH` | Path | `.specforge/prompts/` | Override prompt file directory |
| `--format [text\|json]` | str | `text` | Output format |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No conflicts detected — all governance files are consistent |
| `1` | One or more conflicts detected |
| `2` | Error — missing files, uninitialized project, or parse failure |

### Stdout Format (text)

**No conflicts**:
```
✓ No conflicts detected across 7 governance files.
```

**Conflicts found**:
```
⚠ 2 conflict(s) detected:

  Conflict 1: threshold "max_class_lines"
  ┌─────────────────────────────────────────────────────────┐
  │  File            Rule ID        Value                   │
  │  architecture    ARCH-003       50                      │  ← wins (higher precedence)
  │  backend.dotnet  SOLID-002      200                     │  ← update to match winner
  ├─────────────────────────────────────────────────────────┤
  │  Winner: architecture (precedence 2 > backend precedence 3)
  │  Fix: Update SOLID-002 in backend.dotnet.prompts.md:    │
  │       threshold: max_class_lines=50                     │
  └─────────────────────────────────────────────────────────┘

  Conflict 2: threshold "min_coverage_pct" [AMBIGUOUS]
  ┌─────────────────────────────────────────────────────────┐
  │  File            Rule ID        Value                   │
  │  backend.dotnet  TEST-001       80                      │  ← equal priority
  │  database        DB-007         90                      │  ← equal priority
  ├─────────────────────────────────────────────────────────┤
  │  Winner: AMBIGUOUS (backend and database have equal precedence 3)
  │  Fix: Align both files to the same value manually.      │
  └─────────────────────────────────────────────────────────┘
```

**Error (uninitialized project)**:
```
Error: No .specforge/ directory found.
Run 'specforge init' to initialize a project.
```

**Error (missing files)**:
```
Error: The following governance files are missing:
  - testing.dotnet.prompts.md (expected: .specforge/prompts/testing.dotnet.prompts.md)
  - cicd.prompts.md (expected: .specforge/prompts/cicd.prompts.md)
Run 'specforge init --force' to regenerate missing files.
```

### Stdout Format (json)

```json
{
  "has_conflicts": true,
  "conflict_count": 2,
  "conflicts": [
    {
      "threshold_key": "max_class_lines",
      "rule_id_a": "ARCH-003",
      "domain_a": "architecture",
      "value_a": "50",
      "rule_id_b": "SOLID-002",
      "domain_b": "backend",
      "value_b": "200",
      "winning_domain": "architecture",
      "winning_value": "50",
      "is_ambiguous": false,
      "suggested_resolution": "Update SOLID-002 in backend.dotnet.prompts.md: threshold: max_class_lines=50"
    }
  ]
}
```

### Stderr

Only written on exit code 2 (errors). Exit codes 0 and 1 write only to stdout.

---

## Modified Command: `specforge init`

### New Behavior (additions to Feature 002 contract)

**Governance file generation** (new in Feature 003):
- After the core scaffold files are written, `PromptFileManager.generate()` is
  called to render and write all 7 governance files to `.specforge/prompts/`
- Stack is resolved per FR-016: `--stack` flag → code-scan markers → `agnostic`
- `.specforge/config.json` is written with `{project_name, stack, version, created_at}`

**`--force` with customized governance files**:
- Governance files whose SHA-256 checksum differs from the freshly rendered template
  are preserved without modification
- Only governance files whose checksum matches the freshly rendered template
  (i.e., never edited) are regenerated
- Summary output reports which files were preserved vs regenerated

**Stdout additions** (appended to existing summary):

```
Governance files:
  ✓ architecture.prompts.md    (written)
  ✓ backend.dotnet.prompts.md  (written)
  ✓ frontend.prompts.md        (written)
  ✓ database.prompts.md        (written)
  ✓ security.prompts.md        (written)
  ✓ testing.dotnet.prompts.md  (written)
  ✓ cicd.prompts.md            (written)
```

On `--force` with customizations:
```
Governance files:
  ✓ architecture.prompts.md    (written — default)
  ~ backend.dotnet.prompts.md  (preserved — customized)
  ✓ frontend.prompts.md        (written — default)
  ...
```

### Updated Exit Codes

Same as Feature 002 contract (exit 1 on any error, exit 0 on success).
Unsupported `--stack` value exits with code 1 and lists supported stacks (FR-015).

---

## Programmatic API Contract: `PromptLoader`

Not a CLI command but a public API boundary consumed by the sub-agent executor.

```python
# Module: specforge.core.prompt_loader
# Function: PromptLoader.load_for_feature

loader = PromptLoader(project_root=Path("."))
result = loader.load_for_feature("001-auth")

# Success:
# result.ok == True
# result.value is PromptSet with:
#   .files: dict[str, PromptFile] — 7 entries, one per domain
#   .precedence: list[str] — PRECEDENCE_ORDER constant
#   .feature_id: "001-auth"
# result.value.files["backend"].meta.stack == "dotnet"
# result.value.files["backend"].rules: tuple of PromptRule

# Error (missing files):
# result.ok == False
# result.error: str — human-readable message listing missing files
#   e.g., "Missing governance files:\n  backend.dotnet.prompts.md at .specforge/prompts/backend.dotnet.prompts.md\nRun 'specforge init --force' to restore."

# Timing guarantee: completes within 500 ms (FR-011)
```
