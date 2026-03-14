# Research: Template Rendering Engine

**Feature**: `002-template-rendering-engine`
**Date**: 2026-03-14
**Status**: Complete

## R-01: Jinja2 Extends/Block Inheritance Pattern

**Decision**: Use Jinja2's native `{% extends %}` / `{% block %}` for template inheritance.

**Rationale**: Jinja2's built-in inheritance is battle-tested, well-documented, and requires zero custom code. Child templates declare `{% extends "parent.md.j2" %}` and override named blocks. Blocks not overridden retain the parent's default content. This directly maps to the spec's FR-002 requirement.

**Alternatives considered**:
- **File-level overlay** (replace entire file): Too coarse-grained. Users wanting to change one section would need to duplicate the entire template. Rejected.
- **Custom merge system** (section-level diffing): Over-engineered for markdown templates. Fragile with complex content. Rejected.

**Implementation notes**:
- Base prompt template: `_base_prompt.md.j2` defines blocks for `role`, `instructions`, `context`, `constraints`
- Stack variants extend the generic prompt: `backend.dotnet.md.j2` → `{% extends "prompts/backend.md.j2" %}`
- The `_` prefix convention marks templates as abstract/base (not directly renderable)

## R-02: Template Discovery and Resolution Strategy

**Decision**: TemplateRegistry uses a chain-of-responsibility loader that checks three sources in order: (1) user project `.specforge/templates/`, (2) built-in `base/` package templates.

**Rationale**: Jinja2's `ChoiceLoader` natively supports this pattern — wrap a `FileSystemLoader` (user overrides) and a `PackageLoader` (built-in) in a `ChoiceLoader`. First match wins.

**Alternatives considered**:
- **Single loader with path merging**: Requires manual path manipulation. Error-prone with Windows/Unix path differences. Rejected.
- **Custom loader class**: Unnecessary since Jinja2 provides `ChoiceLoader` out of the box. Rejected.

**Implementation notes**:
- `FileSystemLoader` pointed at `<project_root>/.specforge/templates/` for user overrides
- `PackageLoader` using `importlib.resources` for built-in templates under `base/`
- Stack variant resolution: Registry checks `prompts/backend.dotnet.md.j2` first, falls back to `prompts/backend.md.j2`
- Resolution order for `get("backend", stack="dotnet")`:
  1. User: `.specforge/templates/prompts/backend.dotnet.md.j2`
  2. User: `.specforge/templates/prompts/backend.md.j2`
  3. Built-in: `base/prompts/backend.dotnet.md.j2`
  4. Built-in: `base/prompts/backend.md.j2`

## R-03: Stack Variant Naming Convention

**Decision**: Use dot-notation naming (`backend.dotnet.md.j2`) with all variants in the same directory as the generic template.

**Rationale**: Flat directory structure is simpler to discover and maintain. The dot-notation pattern `{name}.{stack}.md.j2` is unambiguous and parseable. The registry splits on the first dot to extract `(template_name, stack_qualifier)`.

**Spec deviation note**: The clarification session initially decided on subdirectories (`prompts/backend/dotnet.md.j2`). The user's planning input revised this to dot-notation (`backend.dotnet.md.j2`). Dot-notation was adopted because: (1) simpler discovery — one directory scan, no recursion; (2) user overrides mirror the same flat structure; (3) Jinja2's `extends` references are simpler without subdirectories.

**Implementation notes**:
- Pattern: `{name}.md.j2` (generic), `{name}.{stack}.md.j2` (variant)
- Registry parses: `backend.dotnet.md.j2` → name=`backend`, stack=`dotnet`
- Base templates prefixed with `_`: `_base_prompt.md.j2` (excluded from direct catalog)

## R-04: Custom Jinja2 Filters

**Decision**: Add custom filters: `|snake_case`, `|uppercase`, `|pluralize`, `|kebab_case`.

**Rationale**: Templates need to transform project names and identifiers for different contexts (e.g., `project_name|snake_case` for Python module names, `project_name|kebab_case` for CLI commands). Jinja2's filter system is the idiomatic way to add these.

**Alternatives considered**:
- **Pre-compute all variants in context**: Bloats the context dict with `project_name_snake`, `project_name_kebab`, etc. Doesn't scale. Rejected.
- **Template-level string manipulation**: Jinja2's built-in string ops are limited (no snake_case). Rejected.

**Implementation notes**:
- Filters registered on the Jinja2 `Environment` instance
- Pure functions with no side effects — easy to unit test
- `snake_case`: "MyProject" → "my_project"
- `uppercase`: "myapp" → "MYAPP"
- `pluralize`: "entity" → "entities" (simple English rules)
- `kebab_case`: "MyProject" → "my-project"

## R-05: Post-Render Validation Scope

**Decision**: Validate (1) unresolved placeholder markers, (2) unclosed code blocks, (3) orphaned list markers, (4) heading hierarchy. No full markdown linting.

**Rationale**: The goal is to catch rendering errors, not enforce style. A lightweight validator that runs in < 10ms per file keeps the pipeline fast. Full linting tools like markdownlint exist for style enforcement.

**Alternatives considered**:
- **Full markdown AST parsing**: Heavy dependency (e.g., markdown-it, mistune). Overkill for detecting rendering artifacts. Rejected.
- **No validation**: Spec requires FR-013/FR-014. Not an option. Rejected.

**Implementation notes**:
- Unresolved placeholders: regex scan for `{{ ... }}`, `{% ... %}`, `{# ... #}` patterns
- Unclosed code blocks: count `` ``` `` markers — must be even
- Heading hierarchy: `##` must not appear before `#`; no level skips (e.g., `#` → `###`)
- Return `Result[ValidationReport, str]` with line numbers for each issue

## R-06: Generation Header Strategy

**Decision**: Prepend `<!-- Generated by SpecForge — do not edit manually -->` as the first line of every rendered file.

**Rationale**: HTML comments are invisible in rendered markdown but visible in editors. Helps users identify auto-generated files without cluttering the document.

**Implementation notes**:
- Header is injected by the renderer after template rendering, not via a template block
- This ensures consistency even if a user-override template forgets to include it
- The validator checks for the header's presence as a soft warning (not a hard error)

## R-07: Variable Validation Schema Design

**Decision**: Define variable schemas per template type using frozen dataclasses. Each schema declares required fields with types and optional fields with defaults.

**Rationale**: Dataclasses provide type safety, IDE autocompletion, and clear documentation. The schema is checked before rendering begins, providing fail-fast behavior with clear error messages.

**Alternatives considered**:
- **Dict-based schemas**: No type safety, easy to mistype keys. Rejected.
- **JSON Schema**: External dependency, overkill for ~5 variables per template type. Rejected.
- **Pydantic**: Heavy dependency for simple validation. Rejected.

**Implementation notes**:
- `TemplateVarSchema` dataclass: `required: dict[str, type]`, `optional: dict[str, tuple[type, Any]]`
- Three schemas: `CONSTITUTION_VARS`, `PROMPT_VARS`, `FEATURE_VARS`
- Validation returns `Result[dict, list[str]]` — Ok with validated context or Err with list of issues

## R-08: StackAdapter Design

**Decision**: StackAdapter is a pure mapping class that takes a stack name and returns a dict of stack-specific template variables (stack_hint, stack-specific conventions, recommended patterns).

**Rationale**: Centralizes all stack knowledge in one module. Templates consume variables without knowing how they were derived. New stacks added by extending the mapping — no template changes needed.

**Implementation notes**:
- `StackAdapter.get_context(stack: str) -> dict[str, Any]`
- Returns: `stack_hint`, `conventions`, `patterns`, `testing_framework_hint`, etc.
- Falls back to agnostic defaults for unknown stacks
- Constants defined in `config.py`, adapter assembles them

## R-09: Migration Strategy from Feature 001 Templates

**Decision**: Phased migration — new templates created under `base/`, old templates kept temporarily for backward compatibility, scaffold_builder updated to use registry, old templates removed in final cleanup task.

**Rationale**: Breaking the existing scaffold pipeline during development would block other features. A phased approach lets existing tests pass while new functionality is built alongside.

**Implementation notes**:
- Phase 1: Create all new templates under `templates/base/`
- Phase 2: Build registry + renderer + validator as independent modules
- Phase 3: Wire scaffold_builder to use registry (update imports + constants)
- Phase 4: Remove old templates + old template_loader.py
- Phase 5: Update all snapshot tests
- Existing `render_template()` function stays as a thin wrapper during migration

## R-10: Partials Strategy

**Decision**: Partials live in `base/partials/` and are included via Jinja2's `{% include "partials/out-of-scope.md.j2" %}`.

**Rationale**: Jinja2's native `{% include %}` directive handles this with zero custom code. Partials have access to the same context as the including template.

**Implementation notes**:
- Initial partials: `generation-header.md.j2`, `out-of-scope.md.j2`
- Partials are excluded from the registry catalog (not directly renderable)
- User can override partials via `.specforge/templates/partials/`
