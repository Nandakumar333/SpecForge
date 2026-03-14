# Data Model: Template Rendering Engine

**Feature**: `002-template-rendering-engine`
**Date**: 2026-03-14
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Entities

### TemplateType (Enum)

Classification of template purpose.

| Value | Description |
|-------|-------------|
| `constitution` | Project-wide governance document |
| `prompt` | Agent instruction template (supports stack variants) |
| `feature` | Per-feature document template |
| `partial` | Reusable fragment (not directly renderable) |

### TemplateSource (Enum)

Where a template was discovered from.

| Value | Description |
|-------|-------------|
| `built_in` | Shipped with SpecForge package (`templates/base/`) |
| `user_override` | Project-local override (`.specforge/templates/`) |

### TemplateInfo (Frozen Dataclass)

Metadata for a single discovered template.

| Field | Type | Description |
|-------|------|-------------|
| `logical_name` | `str` | Canonical name (e.g., `"backend"`, `"spec"`, `"constitution"`) |
| `template_type` | `TemplateType` | Classification |
| `source` | `TemplateSource` | Where discovered |
| `template_path` | `str` | Jinja2 loader path (e.g., `"prompts/backend.md.j2"`) |
| `stack` | `str \| None` | Stack qualifier if variant, `None` if generic |
| `is_base` | `bool` | `True` if prefixed with `_` (abstract, not directly renderable) |

**Identity**: Unique by `(logical_name, template_type, stack, source)`.

### TemplateVarSchema (Frozen Dataclass)

Variable contract for a template type.

| Field | Type | Description |
|-------|------|-------------|
| `required` | `dict[str, type]` | Variables that must be present (name → expected type) |
| `optional` | `dict[str, tuple[type, Any]]` | Variables with defaults (name → (type, default)) |

**Predefined schemas**:
- `CONSTITUTION_VARS`: `project_name: str`, `agent: str`, `stack: str`, `date: str`, `stack_hint: str`
- `PROMPT_VARS`: `project_name: str`, `agent: str`, `stack: str`, `date: str`, `stack_hint: str`, `conventions: str` (optional), `patterns: str` (optional)
- `FEATURE_VARS`: `project_name: str`, `feature_name: str` (optional), `date: str`, `stack: str` (optional), `stack_hint: str` (optional)

### ValidationIssue (Frozen Dataclass)

A single problem found during output validation.

| Field | Type | Description |
|-------|------|-------------|
| `line` | `int` | Line number where issue was found |
| `issue_type` | `str` | Category: `"unresolved_placeholder"`, `"unclosed_code_block"`, `"heading_skip"`, `"orphaned_list"` |
| `message` | `str` | Human-readable description |
| `placeholder_name` | `str \| None` | Name of unresolved variable (if applicable) |

### ValidationReport (Frozen Dataclass)

Complete validation result for a rendered template.

| Field | Type | Description |
|-------|------|-------------|
| `template_name` | `str` | Which template was validated |
| `issues` | `list[ValidationIssue]` | All problems found |
| `is_valid` | `bool` | `True` if `issues` is empty |

### StackProfile (Frozen Dataclass)

Stack-specific context variables for template rendering.

| Field | Type | Description |
|-------|------|-------------|
| `stack_name` | `str` | Stack identifier (e.g., `"dotnet"`, `"python"`) |
| `stack_hint` | `str` | Human-readable name (e.g., `"C#/.NET"`) |
| `conventions` | `str` | Stack-specific coding conventions |
| `patterns` | `str` | Recommended architectural patterns |
| `testing_hint` | `str` | Testing framework guidance |

## Relationships

```text
TemplateRegistry
  ├── discovers → TemplateInfo[]     (catalog of all templates)
  ├── uses → TemplateVarSchema[]     (per-type variable contracts)
  └── resolves → TemplateInfo        (precedence: user > stack-variant > generic)

TemplateRenderer
  ├── receives → TemplateInfo + context dict
  ├── validates input → TemplateVarSchema
  ├── renders → str (markdown content)
  └── injects → generation header

TemplateValidator
  ├── receives → rendered str
  └── produces → ValidationReport

StackAdapter
  ├── receives → stack name (str)
  └── produces → StackProfile (context variables)
```

## State Transitions

Templates are stateless — no lifecycle beyond discovery and rendering. The TemplateRegistry is initialized once per invocation (on first use) and remains immutable for the session.

```text
[Not Loaded] → discover() → [Registered in Catalog] → get() → [Resolved] → render() → [Rendered String] → validate() → [Validated Output]
```
