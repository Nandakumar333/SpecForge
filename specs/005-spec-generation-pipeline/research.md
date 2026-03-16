# Research — Spec Generation Pipeline

**Feature**: 005-spec-generation-pipeline
**Created**: 2026-03-16

## Research Questions

1. How should cross-platform file locking work for pipeline concurrency control?
2. How should the ArchitectureAdapter pattern integrate with Jinja2 templates?
3. How should phase 3 parallelism be implemented (threading vs asyncio)?
4. How should existing feature templates be extended for architecture-conditional content?
5. How should ServiceContext load and resolve service data from manifest.json?
6. How should the pipeline handle the `fcntl` unavailability on Windows?

## Findings

### R-01: Cross-Platform File Locking

**Question**: The user's architecture proposal uses `fcntl.flock()` for concurrent pipeline safety, but `fcntl` is Unix-only (confirmed: `ModuleNotFoundError` on Windows).

**Options Evaluated**:

| Option | Pros | Cons |
|--------|------|------|
| `fcntl` (Unix) + `msvcrt` (Windows) | stdlib, no deps | Platform-conditional code, different semantics |
| `filelock` (PyPI) | Cross-platform, well-tested, clean API | New external dependency |
| Lock file with PID + timestamp (no OS lock) | Zero deps, cross-platform | Race window between check-and-create |
| Lock file with atomic `os.open(O_CREAT \| O_EXCL)` | Zero deps, cross-platform, atomic | Need manual cleanup on crash; no blocking wait |

**Decision**: Use lock file with `os.open(O_CREAT | O_EXCL)` for atomic creation. This is the same atomic-write pattern already used throughout the codebase (decomposition_state.py, manifest_writer.py). The O_EXCL flag guarantees atomicity — if two processes race, exactly one succeeds and the other gets `FileExistsError`. Stale lock detection (30-min threshold from spec FR-018) handles crash recovery. No new dependencies needed, consistent with Clean Architecture principle (zero external deps in core).

**Lock file format**: JSON with `{"pid": <int>, "timestamp": "<ISO-8601>", "service": "<slug>"}`. Stale detection compares timestamp age. Cleanup in `finally` block.

**Alternatives considered**: `filelock` adds a PyPI dependency to core, violating Clean Architecture. `fcntl`/`msvcrt` dual path adds complexity. Simple file existence check has TOCTOU race.

### R-02: ArchitectureAdapter Integration with Jinja2 Templates

**Question**: Should adapters modify template output post-render, or inject additional context variables pre-render?

**Options Evaluated**:

| Option | Pros | Cons |
|--------|------|------|
| Post-render string injection | Adapters work independently of templates | Fragile string manipulation, hard to test |
| Pre-render context enrichment | Clean separation, templates handle rendering | Templates need `{% if %}` blocks |
| Separate template per architecture | Maximum flexibility per arch | Template duplication, maintenance burden |

**Decision**: Pre-render context enrichment. Each adapter provides a `get_context()` method returning a dict of architecture-specific variables. Templates use `{% if architecture == 'microservice' %}` blocks (already the pattern in spec.md.j2). The adapter also provides `get_extra_sections()` returning a list of section dicts that templates can iterate.

This keeps templates as the single source of output formatting (Constitution Principle II: "All file generation MUST use Jinja2 templates") while letting adapters control what data flows in.

**Adapter interface**:
- `get_context(service_context) -> dict` — base context vars (architecture, service deps, communication patterns)
- `get_plan_sections() -> list[dict]` — extra plan sections (Docker, health checks, etc.)
- `get_task_extras() -> list[dict]` — extra tasks (container build, service registration, etc.)
- `get_edge_case_extras() -> list[dict]` — extra edge cases (network partition, eventual consistency, etc.)
- `get_checklist_extras() -> list[dict]` — extra checklist items (boundary checks, etc.)

### R-03: Phase 3 Parallelism

**Question**: Should phases 3a and 3b use threading or asyncio for parallel execution?

**Options Evaluated**:

| Option | Pros | Cons |
|--------|------|------|
| `concurrent.futures.ThreadPoolExecutor` | Simple API, stdlib, works with sync code | GIL for CPU-bound (not an issue here — I/O bound) |
| `asyncio` | Modern, efficient I/O | Requires async throughout call chain, viral |
| Sequential with early-exit | Simplest, no concurrency bugs | Slower (spec says parallel) |

**Decision**: `concurrent.futures.ThreadPoolExecutor` with `max_workers=2`. Both phases are I/O-bound (template rendering + file writes), so the GIL is not a bottleneck. The futures API is simple: submit both, wait for both, collect results. Error handling: if one future raises, the other's result is still captured. This matches FR-005 (parallel execution) without making the entire codebase async.

**Pattern**:
```python
with ThreadPoolExecutor(max_workers=2) as pool:
    future_dm = pool.submit(run_phase, datamodel_phase)
    future_ec = pool.submit(run_phase, edgecase_phase)
    results = [future_dm.result(), future_ec.result()]
```

### R-04: Extending Feature Templates for Architecture-Conditional Content

**Question**: The existing 7 feature templates (spec.md.j2, etc.) are generic placeholders. How should they be extended for architecture-conditional content?

**Decision**: The existing templates are scaffolding templates (used by `specforge init` to create empty starter files). For Feature 005, these same template files will be enhanced with Jinja2 conditionals and loops that the pipeline populates with real ServiceContext data. The templates already accept `project_name`, `feature_name`, `date` variables — Feature 005 adds `architecture`, `service`, `features`, `dependencies`, `communication_patterns`, and `adapter_sections` to the context.

Key template enhancements (all templates use three-way architecture conditionals where behavior differs):
- `spec.md.j2`: Add `{% for capability in capabilities %}` loop for domain-grouped user stories, `{% if architecture == 'microservice' %}` for Service Dependencies section, `{% if architecture == 'modular-monolith' %}` for Module Interface Contract section
- `research.md.j2`: Add `{% for question in adapter_research_extras %}` loop for architecture-specific research questions
- `plan.md.j2`: Add `{% for section in adapter_sections %}` loop, `{% if architecture == 'microservice' %}` for deployment concerns, `{% if architecture == 'modular-monolith' %}` for module boundary enforcement rules
- `datamodel.md.j2`: Add `{% for entity in entities %}` loop, `{% if architecture == 'microservice' %}` for API contract references, `{% if architecture == 'modular-monolith' %}` for strict module boundary constraints and no cross-module DB warning, `{% if architecture in ['monolithic', 'modular-monolith'] %}` for shared_entities.md references
- `edge-cases.md.j2`: Add `{% for ec in edge_cases %}` loop, `{% for ec in adapter_edge_cases %}` for architecture extras, `{% if architecture == 'modular-monolith' %}` for interface contract violation scenarios (distinct from monolith boundary violations)
- `tasks.md.j2`: Add `{% for task in tasks %}` loop, `{% for task in adapter_tasks %}` for architecture extras
- `checklist.md.j2`: Add `{% for item in checklist_items %}` loop, `{% for item in adapter_checklist %}` for architecture extras, `{% if architecture == 'modular-monolith' %}` for cross-module DB access verification

These templates are already in `_EXCLUDED_FILES`... wait, they are NOT excluded — only `manifest.json.j2` and `communication-map.md.j2` are excluded. The feature templates are discoverable via TemplateRegistry. They will continue to be resolved via `registry.get("spec", TemplateType.feature)` and rendered via `renderer.render()`.

### R-05: ServiceContext Loading from manifest.json

**Question**: How should ServiceContext resolve service data from the manifest produced by Feature 004?

**Decision**: ServiceContext is a frozen dataclass loaded by reading manifest.json and filtering to the target service. The manifest structure (from Feature 004's manifest_writer.py) is:

```json
{
  "schema_version": "1.0",
  "architecture": "microservice",
  "project_description": "...",
  "domain": "finance",
  "features": [{"id": "001", "name": "auth", "service": "identity-service", ...}],
  "services": [{"name": "Identity Service", "slug": "identity-service", "features": ["001"], "communication": [...]}],
  "events": [{"name": "...", "producer": "...", "consumers": [...]}]
}
```

ServiceContext loads by:
1. Read and parse manifest.json
2. Find target service by slug (or resolve feature number → service slug)
3. Filter features to those belonging to the service
4. Extract dependent services from communication links
5. Build frozen dataclass with all resolved data

Feature number resolution (FR-055): scan `features` array for `id` matching the number pattern, then look up its `service` field.

### R-06: Template Registry Integration

**Question**: Should pipeline artifact templates be registered in TemplateRegistry or rendered via render_raw?

**Decision**: Use `render()` (registry-resolved) for all 7 pipeline artifact templates since they are already in `base/features/` and discoverable as `TemplateType.feature`. This allows user overrides via `.specforge/templates/features/` (FR-062) through the existing 4-step resolution chain. The templates use `project_name`, `feature_name`, `date` as base context — Feature 005 extends this with service-specific context variables that templates can optionally use.

## References

- `src/specforge/core/decomposition_state.py` — Existing atomic write + frozen dataclass pattern
- `src/specforge/core/manifest_writer.py` — Manifest structure and validation
- `src/specforge/core/template_renderer.py` — render() vs render_raw() methods
- `src/specforge/core/config.py` — FEATURE_TEMPLATE_NAMES, MANIFEST_PATH, FEATURES_DIR constants
- Python docs: `os.open()` with `O_CREAT | O_EXCL` for atomic file creation
- Python docs: `concurrent.futures.ThreadPoolExecutor` for parallel phase execution
