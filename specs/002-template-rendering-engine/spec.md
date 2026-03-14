# Feature Specification: Template Rendering Engine

**Feature Branch**: `002-template-rendering-engine`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Build the template rendering engine that powers all file generation in SpecForge. This is the foundation that every other feature depends on for creating spec files, prompt files, and configuration. The template engine must: 1. Use Jinja2 as the rendering engine for all .md.j2 template files. 2. Support template inheritance (base templates with blocks for customization). 3. Provide a TemplateRegistry that discovers and manages all available templates. 4. Support template variables with validation (required fields, type checking). 5. Support conditional sections (e.g., include TDD section only if testing is enabled). 6. Generate the following template types: Constitution, 7 Agent Instruction Prompts (backend, frontend, database, security, testing, cicd, api-design) with tech-stack-specific variants, 7 Per-Feature templates (spec, research, datamodel, plan, checklist, edge-cases, tasks) with smart placeholders. 7. Support custom user-defined templates that override built-in defaults. 8. Validate rendered output (no unresolved placeholders, valid markdown structure)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Render Any Template with Variables (Priority: P1)

The SpecForge core system needs to render any template with a given set of variables and produce a valid, well-formatted markdown file. This is the foundational capability that every other feature — init, decompose, spec generation, plan generation — depends on for all file output.

**Why this priority**: Without template rendering, zero file generation is possible. This is the atomic unit of all SpecForge output. Every downstream feature calls into the rendering engine.

**Independent Test**: Can be fully tested by calling the renderer with a template name and a complete variable set, then verifying the returned markdown string has all placeholders resolved, conditional sections correctly included/excluded, and valid markdown structure.

**Acceptance Scenarios**:

1. **Given** a template name and a complete set of required variables, **When** rendering is requested, **Then** a valid markdown string is returned with all placeholders replaced by the provided values.
2. **Given** a template with a required variable missing from the provided context, **When** rendering is requested, **Then** a structured error is returned identifying the missing variable by name.
3. **Given** a template with conditional sections and a truthy condition variable, **When** rendering is requested, **Then** the conditional section is included in the rendered output.
4. **Given** a template with conditional sections and a falsy condition variable, **When** rendering is requested, **Then** the conditional section is omitted cleanly (no leftover blank lines or markers).
5. **Given** a child template that inherits from a base template, **When** rendering is requested, **Then** the base structure is preserved and the child-specific blocks are filled in.

---

### User Story 2 — Override Built-in Templates with Custom Versions (Priority: P2)

A developer customizing SpecForge for their team wants to provide their own template versions that take precedence over built-in defaults. They place their custom templates in the project's `.specforge/templates/` directory and expect SpecForge to use them automatically — no configuration changes required.

**Why this priority**: Template customization is critical for adoption across diverse teams with different documentation standards, compliance requirements, and workflow preferences. Without override support, SpecForge output is one-size-fits-all.

**Independent Test**: Can be fully tested by placing a custom template file in the project's `.specforge/templates/` directory with the same name as a built-in template, then requesting that template and verifying the custom version is rendered instead of the built-in.

**Acceptance Scenarios**:

1. **Given** a custom template exists at `.specforge/templates/` with the same relative path as a built-in template, **When** rendering is requested for that template name, **Then** the custom template is used instead of the built-in.
2. **Given** no custom template exists for a given name, **When** rendering is requested, **Then** the built-in template is used as the fallback.
3. **Given** a custom template references a variable not present in the rendering context, **When** rendering is requested, **Then** a structured error identifies the unresolved variable and the template source (custom override).
4. **Given** a custom template is an empty file, **When** rendering is requested, **Then** the engine renders it as valid empty output without error.

---

### User Story 3 — Retrieve Stack-Specific Prompt Variants (Priority: P2)

The spec pipeline needs technology-stack-specific agent prompt templates so that the instructions given to AI agents are tailored to the project's technology choices. For example, a backend prompt for a .NET project should contain .NET-specific architectural guidance, patterns, and conventions — distinctly different from a Node.js backend prompt.

**Why this priority**: Generic prompts produce generic guidance. Stack-specific prompts dramatically improve the quality and relevance of AI-generated code, plans, and reviews. This is a key differentiator for SpecForge.

**Independent Test**: Can be fully tested by requesting a prompt template with a stack qualifier (e.g., "backend" + "dotnet") and verifying the returned template contains stack-specific content, then requesting the same prompt with a different stack and verifying the content differs, then requesting with an unsupported stack and verifying graceful fallback to the generic version.

**Acceptance Scenarios**:

1. **Given** a stack-specific variant of a prompt template exists (e.g., backend prompt for .NET), **When** the template is requested with that stack qualifier, **Then** the stack-specific variant is returned.
2. **Given** no stack-specific variant exists for the requested stack, **When** the template is requested with a stack qualifier, **Then** the generic version of the prompt template is returned as fallback.
3. **Given** a new stack is added to the supported list but no stack-specific prompt templates exist for it yet, **When** prompts are requested for that stack, **Then** the system gracefully falls back to generic prompts for all prompt types.
4. **Given** a user override exists for a stack-specific prompt, **When** the template is requested, **Then** the user override takes precedence over the built-in stack-specific variant.

---

### User Story 4 — Discover and Catalog All Available Templates (Priority: P3)

SpecForge needs a central registry that automatically discovers all available templates — built-in package templates, stack-specific variants, and user-defined overrides — so any part of the system can query what's available, check for completeness, and resolve the correct template by logical name.

**Why this priority**: As SpecForge grows with more template types, stacks, and user customizations, a registry provides the single source of truth for template availability. Without it, template resolution logic would be scattered and inconsistent.

**Independent Test**: Can be fully tested by initializing the registry in a project with built-in templates, stack variants, and user overrides, then querying it for the full catalog and verifying all templates are discovered with correct type classification, source attribution, and precedence ordering.

**Acceptance Scenarios**:

1. **Given** the registry is initialized in a standard SpecForge project, **When** listing all templates, **Then** all built-in templates are cataloged with their type (constitution, prompt, feature) and source (built-in).
2. **Given** user-override templates exist in `.specforge/templates/`, **When** listing all templates, **Then** overrides are shown alongside their built-in counterparts with source marked as "override."
3. **Given** a specific template is requested by logical name and optional stack qualifier, **When** querying the registry, **Then** the highest-precedence match is returned following the order: user override → stack-specific variant → generic built-in.
4. **Given** the registry is initialized, **When** querying for all prompt templates, **Then** all 7 prompt template types are listed with their available stack variants.

---

### User Story 5 — Validate Rendered Output (Priority: P3)

SpecForge needs to validate that every rendered template produces well-formed output with no unresolved placeholders and valid markdown structure, ensuring all generated files are complete and immediately usable without manual cleanup.

**Why this priority**: Unresolved placeholders (e.g., `{{ project_name }}` appearing literally in output) create confusion, break downstream tools, and erode trust. Catching these at generation time prevents defective files from reaching disk.

**Independent Test**: Can be fully tested by rendering a template with intentionally incomplete variables, running validation on the output, and verifying the validator detects and reports each unresolved placeholder with its location.

**Acceptance Scenarios**:

1. **Given** a successfully rendered template with all variables resolved, **When** output validation is run, **Then** it confirms no unresolved placeholder markers remain in the content.
2. **Given** a rendered template that still contains unresolved placeholder markers, **When** output validation is run, **Then** each unresolved placeholder is identified with its line number and the placeholder name.
3. **Given** a rendered template with broken markdown structure (e.g., unclosed code block, malformed heading), **When** output validation is run, **Then** structural issues are reported with their location and nature.
4. **Given** validation is run on a valid, complete rendered template, **When** the result is checked, **Then** it indicates the output is ready to write to disk.

---

### Edge Cases

- What happens when a template file contains syntax errors (e.g., unclosed tags)?
  → The engine MUST return a structured error identifying the template name, the line number, and a description of the syntax issue — without crashing or producing partial output.
- What happens when a user-override template references blocks or parent templates that don't exist?
  → The engine MUST return an error explaining the missing parent/block reference and suggesting the correct name.
- What happens when circular template inheritance is detected (template A extends B, B extends A)?
  → The engine MUST detect the cycle and return an error identifying the templates involved — without entering an infinite loop.
- What happens when the project's `.specforge/templates/` directory is missing or inaccessible?
  → Built-in templates MUST remain fully available. Only user-override discovery is affected, and a warning is logged noting that custom templates could not be loaded.
- What happens when a variable value contains markdown-sensitive characters (e.g., `|`, `#`, `` ` ``)?
  → The engine MUST pass variable values through without escaping by default, preserving the author's intended markdown formatting.
- What happens when the same logical template exists as both a stack-specific variant and a user override?
  → User override takes precedence over stack-specific variant, following the documented precedence order.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Rendering

- **FR-001**: The engine MUST render templates by replacing all placeholder markers with values from a provided variable context, producing a complete markdown string.
- **FR-002**: The engine MUST support template inheritance, where child templates extend a base template structure and override specific named blocks within it.
- **FR-003**: The engine MUST support conditional sections that include or exclude blocks of content based on variable values (e.g., include a TDD section only when testing is enabled; include stack-specific guidance only when a non-generic stack is selected).
- **FR-004**: The engine MUST preserve markdown formatting in rendered output — headings, lists, code blocks, tables, and link references MUST remain structurally valid after rendering.

#### Template Registry

- **FR-005**: The engine MUST provide a TemplateRegistry that automatically discovers and catalogs all available templates from three sources: built-in package templates, stack-specific variant templates, and user-defined override templates.
- **FR-006**: The TemplateRegistry MUST resolve template lookups using the following precedence order: (1) user override, (2) stack-specific variant, (3) generic built-in.
- **FR-007**: The TemplateRegistry MUST support querying by template type (constitution, prompt, feature), by logical name, and by optional stack qualifier.
- **FR-008**: The TemplateRegistry MUST provide a listing capability that returns all known templates with their type, source attribution (built-in, stack-variant, or user-override), and available stack variants.

#### Variable Validation

- **FR-009**: The engine MUST validate that all required variables are present in the rendering context before rendering begins. Missing required variables MUST produce a structured error naming each missing variable.
- **FR-010**: The engine MUST validate that variable values match their expected types (e.g., string, boolean, list). Type mismatches MUST produce a structured error identifying the variable, expected type, and actual type.

#### Output Validation

- **FR-011**: The engine MUST validate rendered output for unresolved placeholder markers. Any remaining placeholders MUST be reported with their line number and placeholder name.
- **FR-012**: The engine MUST validate rendered output for basic markdown structural integrity (properly closed code blocks, valid heading hierarchy, well-formed lists).

#### Template Catalog

- **FR-013**: The engine MUST support the **Constitution** template type for project-wide governance documents.
- **FR-014**: The engine MUST support **7 Agent Instruction Prompt** templates: backend, frontend, database, security, testing, cicd, and api-design.
- **FR-015**: Each Agent Instruction Prompt template MUST support tech-stack-specific variants. At minimum, variants MUST be available for each supported stack; the generic variant serves as the fallback for stacks without a dedicated variant.
- **FR-016**: The engine MUST support **7 Per-Feature** templates: spec, research, data-model, plan, checklist, edge-cases, and tasks — each with contextually appropriate placeholder variables and conditional sections.
- **FR-017**: Per-Feature templates MUST include smart placeholders that provide contextual hints (e.g., a placeholder for "acceptance criteria" in the spec template should include guidance on how to write good acceptance criteria).

#### User Overrides

- **FR-018**: Custom templates placed in the project's `.specforge/templates/` directory MUST automatically override built-in templates with the same relative path — no configuration changes required.
- **FR-019**: When no user-defined or stack-specific template is found for a given name, the engine MUST fall back to the generic built-in template.
- **FR-020**: The engine MUST return structured errors (not crash) for all failure conditions: missing templates, template syntax errors, missing variables, type mismatches, and circular inheritance.

### Key Entities

- **Template**: A document blueprint containing static content, placeholder markers, conditional sections, and optional inheritance directives. Identified by a logical name, classified by type (constitution, prompt, or feature), and sourced from either the built-in package or a user override directory.
- **TemplateRegistry**: The central catalog of all discovered templates. Responsible for discovering templates across all sources, resolving lookups by name and stack, and enforcing the precedence order (user override → stack-specific → generic built-in).
- **Template Variable**: A named input value passed to the rendering engine. Each variable has a name, a type (string, boolean, list, dictionary), and a required/optional designation. Used to fill placeholder markers during rendering.
- **Template Context**: The complete set of variables assembled for a single rendering operation. Contains all required and optional variables needed by the target template and any templates it inherits from.
- **Stack Variant**: A specialized version of a template tailored to a specific technology stack. Identified by appending a stack qualifier to the template's logical name. Falls back to the generic version when no variant exists for the requested stack.
- **Rendered Output**: The final markdown content produced by rendering a template with a complete, validated context. Subject to output validation before being written to disk.

### Assumptions

- The template catalog defined in this feature (7 prompt types: backend, frontend, database, security, testing, cicd, api-design; 7 feature types: spec, research, data-model, plan, checklist, edge-cases, tasks) represents the target state for SpecForge. The prompt and feature template names from Feature 001 (cli-init-scaffold) were scaffolding placeholders and will be migrated to align with this catalog as part of implementation.
- Stack-specific variants apply primarily to Agent Instruction Prompt templates. Per-Feature templates use conditional sections rather than separate variant files to handle stack differences, since their structure is largely stack-independent.
- Template variable schemas (which variables are required, their types, and defaults) are defined per template type, not per individual template file. All templates of the same type share the same variable contract.
- The rendering engine does not manage file I/O (writing to disk). It produces rendered strings; the caller (e.g., scaffold writer, spec generator) handles persistence. This preserves separation of concerns from Feature 001.
- User override templates must follow the same directory structure as built-in templates (e.g., `.specforge/templates/prompts/backend.md.j2` overrides the built-in `prompts/backend.md.j2`). No mapping configuration is needed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any template renders with valid variables in under 1 second, ensuring file generation feels instantaneous to the user.
- **SC-002**: 100% of files generated through the standard pipeline contain zero unresolved placeholder markers.
- **SC-003**: A developer can override any built-in template by placing a single file in the project's `.specforge/templates/` directory — no configuration file edits, no code changes, no restarts required.
- **SC-004**: Stack-specific agent prompt templates produce demonstrably different, contextually appropriate content for each supported stack — verifiable by comparing outputs for two different stacks and confirming stack-relevant differences.
- **SC-005**: All template rendering errors include the template name, the specific issue, and a suggested resolution — zero cryptic or ambiguous error messages.
- **SC-006**: The TemplateRegistry discovers and catalogs 100% of available templates (built-in + overrides + stack variants) upon initialization, with no manual registration required.
- **SC-007**: Adding a new template type or stack variant requires adding only template files — zero code changes to the registry or rendering engine.
