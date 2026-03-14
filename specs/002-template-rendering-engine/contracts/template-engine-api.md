# Contract: Template Engine API

**Feature**: `002-template-rendering-engine`
**Date**: 2026-03-14

## Public Interface

The template engine exposes four public modules consumed by other SpecForge features (e.g., `scaffold_builder`, `scaffold_writer`, future spec generator).

### TemplateRegistry

```text
TemplateRegistry(project_root: Path | None)
  - Constructor: project_root enables user-override discovery. None = built-in only.

  .discover() -> Result[int, str]
    - Scans all template sources, populates internal catalog.
    - Returns Ok(template_count) or Err(error_message).

  .get(name: str, template_type: TemplateType, stack: str = "agnostic") -> Result[TemplateInfo, str]
    - Resolves a single template by name, type, and optional stack.
    - Precedence: user override > stack-specific variant > generic built-in.
    - Returns Ok(TemplateInfo) or Err("Template not found: {name}").

  .list(template_type: TemplateType | None = None) -> list[TemplateInfo]
    - Returns all known templates, optionally filtered by type.
    - Includes source attribution and available stack variants.

  .has(name: str, template_type: TemplateType) -> bool
    - Quick check for template existence.
```

### TemplateRenderer

```text
TemplateRenderer(registry: TemplateRegistry)
  - Constructor injection of registry.

  .render(template_name: str, template_type: TemplateType, context: dict, stack: str = "agnostic") -> Result[str, str]
    - Full pipeline: validate context → resolve template → render → inject header.
    - Returns Ok(rendered_markdown) or Err(error_description).

  .render_raw(template_path: str, context: dict) -> Result[str, str]
    - Low-level: renders a specific template path without registry resolution.
    - Used for backward compatibility during migration.
```

### TemplateValidator

```text
TemplateValidator()
  - Stateless. No constructor arguments.

  .validate(content: str, template_name: str = "") -> ValidationReport
    - Checks: unresolved placeholders, unclosed code blocks, heading hierarchy, orphaned lists.
    - Returns ValidationReport with issues list and is_valid flag.

  .validate_context(context: dict, schema: TemplateVarSchema) -> Result[dict, list[str]]
    - Pre-render: checks required variables present, types match.
    - Returns Ok(context) or Err([list of issues]).
```

### StackAdapter

```text
StackAdapter()
  - Stateless. No constructor arguments.

  .get_context(stack: str) -> StackProfile
    - Maps stack name to context variables.
    - Returns agnostic defaults for unknown stacks.

  .supported_stacks() -> list[str]
    - Returns list of all known stack identifiers.
```

## Integration Points

### Scaffold Pipeline (Feature 001 — Modified)

Current flow:
```text
scaffold_builder → template_loader.render_template() → scaffold_writer
```

New flow:
```text
scaffold_builder → TemplateRegistry.get() → TemplateRenderer.render() → TemplateValidator.validate() → scaffold_writer
```

### Backward Compatibility

During migration, `template_loader.render_template()` is preserved as a thin wrapper:
```text
render_template(name, **ctx) → TemplateRenderer.render_raw("base/" + name, ctx)
```

This ensures existing callers and tests work without modification until the full migration is complete.

## Error Contracts

All public methods return `Result[T, str]` for recoverable errors. The error string always includes:
1. The template name involved
2. The specific issue
3. A suggested resolution

Example: `"Missing required variable 'project_name' for template 'constitution' (type: constitution). Provide it in the rendering context."`
