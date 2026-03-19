# Contract: config.json Schema Extension

**Feature**: 014-interactive-model-selection
**Type**: File schema (JSON)

## Current Schema (v1.0)

```json
{
  "project_name": "string",
  "stack": "string",
  "version": "1.0",
  "created_at": "YYYY-MM-DD"
}
```

## Extended Schema (v1.1)

```json
{
  "project_name": "string",
  "stack": "string",
  "agent": "string",
  "commands_dir": "string",
  "version": "1.0",
  "created_at": "YYYY-MM-DD"
}
```

## New Fields

| Field | Type | Required | Default | Validation |
|-------|------|----------|---------|------------|
| `agent` | `string` | Yes | `"generic"` | Must be a registered agent plugin name or `"generic"` |
| `commands_dir` | `string` | Yes | `"commands"` | Relative path, no `..` traversal, no absolute paths |

## Backward Compatibility

- Existing `config.json` files without `agent`/`commands_dir` fields are valid
- `prompt_loader.py` reads `agent` with fallback to `"generic"` if missing
- `prompt_loader.py` reads `commands_dir` with fallback to `"commands"` if missing
- The `version` field remains `"1.0"` (additive fields are not a breaking change)

## Write Locations

- `_write_config_json()` in `prompt_manager.py` — modified to accept `agent` and `commands_dir` params
- `scaffold_builder.py` `generate_governance_files()` — calls `_write_config_json()` with new fields
