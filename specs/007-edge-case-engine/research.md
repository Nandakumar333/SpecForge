# Research: Edge Case Analysis Engine

**Feature**: 007-edge-case-engine
**Date**: 2026-03-17

## R-001: YAML Pattern File Loading Strategy

**Decision**: Use `importlib.resources` (Python 3.11+) to load YAML pattern files bundled within the `specforge` package.

**Rationale**: Pattern files are static, shipped with the package, and should not require user filesystem paths. `importlib.resources` handles both installed packages and development mode correctly. PyYAML is already a transitive dependency.

**Alternatives considered**:
- `pkg_resources` (deprecated since Python 3.12)
- `Path(__file__).parent` relative paths (fragile in installed packages)
- Inline Python dicts instead of YAML (rejected: user extensibility harder, patterns less readable)

## R-002: YAML Frontmatter Format for Machine Parseability

**Decision**: Use fenced YAML code blocks (` ```yaml ... ``` `) per edge case, embedded immediately after the edge case heading.

**Rationale**: Fenced blocks are visible to human readers, parseable by any YAML library with simple regex extraction (`re.findall(r'```yaml\n(.*?)\n```', text, re.DOTALL)`), and don't conflict with document-level YAML frontmatter conventions. The Feature 009 sub-agent can iterate over blocks without a full markdown parser.

**Alternatives considered**:
- Document-level `---` frontmatter with all cases as an array (breaks markdown preview, single point of failure)
- HTML comments with YAML inside (invisible to humans, poor developer experience)
- JSON blocks (less human-readable than YAML, more verbose)

## R-003: BoundaryAnalyzer Reuse for Data Ownership Detection

**Decision**: Reuse `BoundaryAnalyzer._extract_keywords()` and `analyze()` from Feature 006 to detect shared entities. The edge case analyzer calls `BoundaryAnalyzer(manifest).analyze(slug)` to get `AmbiguityMatch` tuples with `category="service_boundary"`, then converts each into a `data_ownership` edge case.

**Rationale**: BoundaryAnalyzer already performs keyword extraction, stemming, and ubiquity filtering. Reimplementing this logic would violate DRY and risk inconsistency between clarification and edge case outputs.

**Alternatives considered**:
- Independent entity extraction in edge_case_analyzer.py (duplicates BoundaryAnalyzer logic)
- Extending BoundaryAnalyzer with edge-case-specific methods (violates single responsibility — BA is for clarification)

## R-004: Template Enhancement Strategy

**Decision**: Enhance `edge-cases.md.j2` to conditionally render enriched edge cases when `edge_cases` context key is present. Fall back to existing `adapter_edge_cases` behavior when absent.

**Rationale**: Backward compatibility is critical — existing pipeline tests assert on template output. The enhanced template checks `{% if edge_cases %}` first, rendering the new YAML-frontmatter format. If not present, falls back to the existing `{% for ec in adapter_edge_cases %}` loop.

**Alternatives considered**:
- New separate template `edge-cases-v2.md.j2` (duplicates template logic, registry confusion)
- Breaking change to template (breaks 33 existing snapshot tests)

## R-005: Severity Assignment at Runtime vs Pattern File

**Decision**: Severity is `null` in YAML pattern files and assigned at runtime by `SeverityMatrix` using the dependency's `required` flag and `pattern` from `communication[]`.

**Rationale**: The same category (e.g., service_unavailability) has different severity depending on whether the dependency is required or optional. Hardcoding severity in YAML would require duplicate patterns for required/optional variants.

**Alternatives considered**:
- Hardcoded severity per category (loses required/optional nuance)
- Separate pattern files for required vs optional (file explosion)

## R-006: Circular Dependency Detection

**Decision**: During analysis, track visited service slugs in a set. If a service appears twice in the dependency traversal, emit a "circular dependency" edge case and stop traversal for that path.

**Rationale**: The edge case analyzer only traverses direct dependencies from `communication[]` (depth=1), so circular dependencies at depth > 1 are not a runtime concern. However, A→B and B→A both appearing in `communication[]` is detectable and worth flagging.

**Alternatives considered**:
- Deep graph traversal with cycle detection (overcomplicated — Feature 007 only needs direct deps)
- Ignore cycles entirely (misses a real architectural concern)
