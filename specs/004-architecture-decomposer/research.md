# Research: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Feature**: 004-architecture-decomposer
**Date**: 2026-03-15
**Status**: Complete

## Research Task 1: Interactive Prompts with Rich + Click

**Context**: The decompose flow needs interactive architecture selection (3 choices) and an interactive review/edit loop for service mappings. The project uses both Click 8.x (CLI framework) and Rich 13.x (terminal output).

### Decision: Use Rich for display, Click for command-level prompts

**Rationale**: Click handles command-level options (`--arch`, `--remap`, `--no-warn`) and argument parsing. Rich handles in-flow interactive prompts and display formatting. This avoids fighting Click's prompt system for multi-step flows that aren't tied to command arguments.

### Alternatives Considered

1. **Click prompts only** (`click.prompt(type=click.Choice(...))`): Simple but no rich formatting. Can't display descriptions alongside choices. Rejected because the architecture gate needs one-line descriptions per option (FR-003).
2. **Rich Prompt only** (`rich.prompt.Prompt.ask()`): Supports `choices` parameter for validation. Can be paired with `rich.panel.Panel` for formatted option display. This is the chosen approach for the architecture gate.
3. **Questionary/InquirerPy**: Third-party interactive prompt libraries. Rejected because they add a new dependency (constraint: zero new external deps).

### Implementation Pattern

**Architecture Gate** (3-choice selection):
```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# Display options with descriptions
console.print(Panel(
    "[bold]1.[/bold] Monolithic — Single deployable unit, features as modules\n"
    "[bold]2.[/bold] Microservice — Independent services per bounded context\n"
    "[bold]3.[/bold] Modular Monolith — Single deployable, strict module boundaries",
    title="Architecture Selection",
))

choice = Prompt.ask(
    "Select architecture",
    choices=["1", "2", "3"],
    default="1",
)
```

**Interactive Review/Edit Loop** (text commands):
```python
while True:
    _display_mapping_table(console, services)  # Rich Table
    cmd = Prompt.ask(
        "Edit mapping (combine/split/rename/add/remove/done)",
        default="done",
    )
    if cmd == "done":
        break
    result = _parse_and_apply_edit(cmd, services)
    if not result.ok:
        console.print(f"[red]{result.error}[/red]")
```

**Feature List Display**: Use `rich.table.Table` with columns for ID, Name, Description, Priority, Category.

**Service Mapping Display**: Use `rich.table.Table` with columns for Service, Features, Rationale.

**Dependency Graph**: Use `rich.tree.Tree` for hierarchical display of implementation phases.

---

## Research Task 2: Manifest JSON Generation — Jinja2 vs json.dumps

**Context**: The constitution mandates "All file generation MUST use Jinja2 templates — string concatenation for output files is prohibited." Feature 004 generates `manifest.json` with a complex nested schema (features, services, communication links, events).

### Decision: Use `manifest.json.j2` template with `{{ manifest | tojson(indent=2) }}` via `render_raw()`

**Rationale**: The constitution (Principle II) mandates "All file generation MUST use Jinja2 templates." `manifest.json` is a user-facing output file, so the mandate applies. Jinja2's built-in `tojson` filter delegates to `json.dumps` internally, providing correct JSON escaping (quotes, backslashes, HTML-special chars) while remaining constitution-compliant.

### Implementation

1. Create `src/specforge/templates/base/features/manifest.json.j2` with content:
   ```jinja
   {{ manifest | tojson(indent=2) }}
   ```

2. In `ManifestWriter`, render via `render_raw()` (no registry changes needed):
   ```python
   result = self._renderer.render_raw(
       "base/features/manifest.json.j2",
       {"manifest": manifest_dict},
   )
   ```

3. The `_PackageLoader` in `template_renderer.py` loads any path under `specforge.templates` — it does not filter by extension — so `.json.j2` works without registry modifications.

### Alternatives Considered

1. **Raw `json.dumps()` without template**: Constitution-violating. While `json.dumps` is serialization (not string concatenation), the mandate covers "all file generation" and `manifest.json` is a decompose output artifact. The existing `config.json` in `prompt_manager.py` uses raw `json.dumps`, but that's an internal config sidecar — not a precedent for feature output files.

2. **Hand-rolled `.json.j2` with field interpolation**: Writing `"name": "{{ service.name }}"` directly in the template. Rejected: any user input containing quotes (e.g., `Say "Hello"`) produces invalid JSON (`"name": "Say "Hello""`). Every field requires `| tojson`, making the template fragile and verbose.

3. **Extend `TemplateRegistry` with `TemplateType.manifest`**: Unnecessary. `manifest.json.j2` is always rendered by `ManifestWriter` directly via `render_raw()`, never discovered dynamically.

### Key Details

- `tojson` sorts keys alphabetically — JSON consumers are order-agnostic, and FR-053 validation accesses fields by key name. No impact.
- `tojson` HTML-escapes `<`, `>`, `&` (`\u003c`, `\u0026`) — correct for JSON, no downstream impact.
- The template is 1 line, eliminating the "unreadable template" concern for complex nested structures.
- Post-write validation (FR-053) via `json.loads()` passes cleanly on `tojson` output.

---

## Research Task 3: Atomic File Writes on Windows + Unix

**Context**: FR-028 requires atomic writes for crash safety: "write to `{filename}.tmp`, then `os.replace()` to the final path." The project uses `pathlib.Path` exclusively.

### Decision: Use `tempfile.NamedTemporaryFile` in same directory + `os.replace()`

**Rationale**: `os.replace()` is atomic on POSIX (single filesystem) and on Windows NTFS. Using a temp file in the same directory guarantees same-filesystem operation, avoiding cross-device rename failures.

### Implementation Pattern

```python
import os
import tempfile
from pathlib import Path

from specforge.core.result import Err, Ok, Result


def atomic_write(path: Path, content: bytes) -> Result:
    """Write content to path atomically: temp file + fsync + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    fd: int | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)
        try:
            os.write(fd, content)
            os.fsync(fd)  # flush to disk before rename
        finally:
            os.close(fd)
            fd = None
        tmp_path.replace(path)  # atomic same-volume rename
        tmp_path = None  # rename succeeded
    except PermissionError:
        return Err(f"Permission denied writing to '{path}'")
    except OSError as exc:
        return Err(f"Failed to write '{path}': {exc}")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    return Ok(path)
```

**Key details**:
- `tempfile.mkstemp(dir=path.parent)` creates the temp file in the same directory as the target, ensuring same-filesystem `os.replace()`. This is critical on Windows where cross-volume `MoveFileEx` silently falls back to non-atomic copy+delete.
- `os.fsync(fd)` before close ensures data is flushed to disk before the rename. Without this, a power loss between `close()` and `replace()` could leave the temp file empty.
- `tmp_path.replace(path)` uses `pathlib.Path.replace()` which wraps `os.replace()` — atomic on both POSIX and Windows NTFS for same-volume renames.
- The `finally` block cleans up the temp file on any error path. After successful rename, `tmp_path = None` prevents cleanup of the (now moved) file.
- `mkstemp` generates a random suffix, avoiding name collisions from concurrent writers (vs the spec's fixed `{filename}.tmp` approach).

### Alternatives Considered

1. **Manual `.tmp` suffix** (`path.with_suffix(".tmp")`): Simpler but risks name collision if multiple processes write simultaneously. Rejected for robustness.
2. **`pathlib.Path.rename()`**: Does NOT overwrite on Windows (raises `FileExistsError`). Must use `os.replace()` for cross-platform atomic overwrite.
3. **`shutil.move()`**: Not atomic — may copy+delete on cross-filesystem moves. Rejected.

### Windows-Specific Considerations

- `os.replace()` on Windows NTFS is atomic for the metadata update but may not be atomic if the file is open by another process. Since SpecForge is a single-threaded CLI tool, this is not a concern.
- Temp file naming with `mkstemp` avoids Windows file locking issues that `NamedTemporaryFile(delete=True)` can cause (the file can't be renamed while open on Windows).

---

## Research Task 4: Affinity Scoring Algorithm Design

**Context**: FR-050 specifies a multi-step service mapping algorithm. The spec is prescriptive but some implementation details need resolution.

### Decision: Implement as specified in FR-050 with helper function decomposition

**Algorithm steps** (from FR-050):
1. Apply `always_separate` — features with `always_separate=True` become singleton services
2. Compute pairwise affinity scores for remaining features
3. Greedy merge: highest affinity pair first, merge if score ≥ 3
4. Features with no merge partner become singleton services
5. Validate: no service exceeds 4 features; split if exceeded
6. Generate rationale for each service

### Score Factors (from FR-050)

| Factor | Score | Condition |
|--------|-------|-----------|
| Same `category` | +3 | Both features have identical `category` field |
| Shared data keywords | +2 | Features reference overlapping `data_keywords` (set intersection ≥ 1) |
| Different scaling profile | -2 | Features have different scaling characteristics |
| Different failure mode | -2 | Features have different failure domains |

### Implementation Notes

- **Shared data keywords**: Domain patterns define features with `data_keywords` field. Two features sharing ≥1 keyword get +2. This is a set intersection check.
- **Scaling profile**: Derived from the feature's `category`. Hard-coded mapping: `{"foundation": "low", "core": "medium", "supporting": "medium", "integration": "high-variance", "admin": "low"}`.
- **Failure mode**: Derived from the feature's `category`. Hard-coded mapping: `{"foundation": "infrastructure", "core": "business-logic", "supporting": "business-logic", "integration": "external-dependency", "admin": "operational"}`. Features with different failure modes get −2 because failures in one domain should not cascade to another.
- **Greedy merge**: Sort all pairs by score descending. Process in order. Skip pairs where either feature is already merged. This is O(n²) where n ≤ 15 — negligible.
- **Rationale generation**: Template strings keyed by dominant factor:
  - WHY COMBINED templates:
    - Same category: `"Combined: shared '{category}' bounded context — {feature_a} and {feature_b} operate in the same domain."`
    - Shared data: `"Combined: shared data model — {feature_a} and {feature_b} access the same entities ({keywords})."`
  - WHY SEPARATE templates:
    - Always-separate rule: `"Separate: {feature} is always isolated — {reason} (e.g., auth requires independent scaling and security boundary)."`
    - Different scaling: `"Separate: {feature_a} and {feature_b} have different scaling profiles — independent deployment needed."`
    - Different failure mode: `"Separate: {feature_a} and {feature_b} have different failure domains — isolation prevents cascading failures."`
    - Singleton (no merge partner): `"Separate: {feature} has low affinity with all other features (max score: {score}) — standalone service."`
- **Circular dependency detection**: Use DFS-based cycle detection on the service dependency graph. For each service, perform a depth-first traversal of its `communication` targets. Track visited nodes in the current path; if a node is revisited, a cycle exists. Report the full cycle path (e.g., `A → B → C → A`). This is O(V+E) where V = services, E = communication links. Kahn's algorithm (topological sort) is an alternative but DFS provides the cycle path directly for error reporting.

### Derived Mappings

**Scaling profile** (category → scaling):
```python
SCALING_PROFILE = {"foundation": "low", "core": "medium", "supporting": "medium", "integration": "high-variance", "admin": "low"}
```

**Failure mode** (category → failure domain):
```python
FAILURE_MODE = {"foundation": "infrastructure", "core": "business-logic", "supporting": "business-logic", "integration": "external-dependency", "admin": "operational"}
```

Features with different scaling profiles or different failure modes get −2 each.

### Function Decomposition (≤30 lines per function)

```
compute_pairwise_scores(features) -> dict[(str,str), int]
apply_always_separate(features) -> tuple[list[Service], list[Feature]]
greedy_merge(features, scores) -> list[Service]
enforce_max_features(services, max=4) -> list[Service]
generate_rationale(service, scores) -> str
map_features_to_services(features, arch_type) -> list[Service]  # orchestrator
```

---

## Research Task 5: Decomposition State Persistence

**Context**: FR-037 requires saving state after each step for crash-safe resumption. The state file lives at `.specforge/decompose-state.json`.

### Decision: JSON state file with step enum, atomic writes, resume-or-fresh prompt

**State Schema** (from spec):
```json
{
  "step": "architecture | decomposition | mapping | review | complete",
  "architecture": "monolithic | microservice | modular-monolith | null",
  "project_description": "string",
  "domain": "string | null",
  "features": [],
  "services": [],
  "timestamp": "ISO-8601 UTC"
}
```

### Implementation Pattern

- **Save**: After each step completes, serialize current state and write atomically (reuse `atomic_write_json` from Research Task 3).
- **Load**: On `specforge decompose` startup, check for `.specforge/decompose-state.json`. If exists and step ≠ "complete", offer to resume.
- **Delete**: On successful completion (manifest written + validated), delete the state file.
- **Resume logic**: Each step checks if state already has data for that step. If yes, skip to next incomplete step.

### Step Transitions

```
(start) → architecture → decomposition → mapping → review → complete → (delete state)
                                           ↑                    |
                                           └── (monolith skips) ┘
```

For monolithic architecture, the flow skips `mapping` and `review` (no service mapping needed), going directly from `decomposition` to `complete`.

---

## Research Task 6: Integration with Existing TemplateRegistry

**Context**: Feature 004 adds one new Jinja2 template (`communication-map.md.j2`) to `templates/base/features/`. The existing `TemplateRegistry` discovers `.md.j2` files in the `features/` subdirectory.

### Decision: No registry modifications needed

**Rationale**: The `communication-map.md.j2` template is a standard `.md.j2` file in the `features/` directory. The existing `TemplateRegistry._scan_directory()` will discover it automatically with `logical_name="communication-map"` and `template_type=TemplateType.feature`.

To render it, use `TemplateRenderer.render()` with `template_name="communication-map"` and `template_type=TemplateType.feature`. A new variable schema function `get_communication_map_vars()` may be needed in `config.py`, or the template can be rendered via `render_raw()` to bypass schema validation (simpler, since the communication map context is constructed internally, not from user input).

### Template Variables for `communication-map.md.j2`

```python
{
    "app_name": str,           # Project name
    "architecture": str,       # Architecture type
    "services": list[dict],    # Service definitions with communication links
    "events": list[dict],      # Async event definitions
    "mermaid_diagram": str,    # Pre-generated Mermaid graph string
}
```

The Mermaid diagram string is generated by `CommunicationPlanner` in Python (string building for graph syntax is appropriate) and passed as a template variable. The template wraps it in Markdown code fences and adds documentation sections.
