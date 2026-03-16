# Quickstart: Feature 004 — Architecture Decision Gate & Smart Feature-to-Service Mapper

**Branch**: `004-architecture-decomposer`

## Prerequisites

- Python 3.11+
- `uv` package manager
- Existing SpecForge codebase with Features 001–003 implemented

## Implementation Order

Modules are listed in dependency order. Implement from top to bottom. **TDD enforced**: within each phase, create test files BEFORE implementation files (Constitution Principle IV).

### Phase 1: Foundation (no inter-module deps)

1. **`src/specforge/core/config.py`** — Add `ArchitectureType` enum, new constants
   - Add: `ArchitectureType = Literal["monolithic", "microservice", "modular-monolith"]`
   - Add: `VALID_ARCHITECTURES`, `OVER_ENGINEERING_THRESHOLD = 5`
   - Add: `MANIFEST_PATH = ".specforge/manifest.json"`
   - Add: `STATE_PATH = ".specforge/decompose-state.json"`
   - Add: `FEATURE_CATEGORIES`, `FEATURE_PRIORITIES`

2. **`src/specforge/core/domain_patterns.py`** — Hard-coded domain data
   - Define 6 domain dicts + generic fallback
   - Each domain: `name`, `keywords` (weighted), `features` (with all metadata)
   - No logic — pure data declarations
   - Test: `tests/unit/test_domain_patterns.py` — validate structure, counts, required fields

### Phase 2: Domain Analysis

3. **`src/specforge/core/domain_analyzer.py`** — Domain matching + feature generation
   - `DomainAnalyzer` class with constructor injection of domain patterns
   - `analyze(description: str) -> Result[DomainMatch]` — keyword scoring
   - `decompose(description: str, domain: DomainMatch) -> Result[list[Feature]]` — feature list
   - `is_gibberish(description: str) -> bool` — empty/nonsensical input check
   - Test: `tests/unit/test_domain_analyzer.py` — UT-001 (`analyze()` domain matching), UT-002 (`analyze()` generic fallback), UT-003 (`analyze()` keyword scoring threshold), UT-014 (priority assignment)

### Phase 3: Service Mapping

4. **`src/specforge/core/service_mapper.py`** — Affinity scoring + merge algorithm
   - `ServiceMapper` class
   - `map_features(features: list[Feature], arch: str) -> Result[list[Service]]`
   - Internal helpers: `_compute_pairwise_scores`, `_apply_always_separate`, `_greedy_merge`, `_enforce_max_features`, `_generate_rationale`
   - For monolithic: single service with all features
   - Test: `tests/unit/test_service_mapper.py` — UT-004 (`_compute_pairwise_scores()`), UT-005 (`_apply_always_separate()`), UT-006 (`_greedy_merge()`), UT-007 (`_enforce_max_features()`), UT-008 (`_generate_rationale()`)

### Phase 4: Communication + Manifest

5. **`src/specforge/core/communication_planner.py`** — Pattern assignment + Mermaid
   - `CommunicationPlanner` class
   - `plan(services: list[Service]) -> tuple[list[Service], list[Event]]` — assigns patterns
   - `generate_mermaid(services: list[Service], events: list[Event]) -> str` — diagram
   - Test: `tests/unit/test_communication_planner.py` — UT-009 (`plan()` heuristic assignment + `generate_mermaid()` + `detect_cycles()`)

6. **`src/specforge/core/manifest_writer.py`** — JSON generation + atomic write + validation
   - `ManifestWriter` class
   - `write(path: Path, manifest: dict) -> Result[Path]` — atomic write
   - `validate(path: Path) -> Result[None]` — post-write validation (FR-053)
   - `build_manifest(arch, domain, features, services, events, description) -> dict`
   - Test: `tests/unit/test_manifest_writer.py` — UT-010 (`write()` atomic write), UT-011 (`validate()` post-write checks)

7. **`src/specforge/core/decomposition_state.py`** — State persistence
   - `DecompositionState` frozen dataclass
   - `save_state(path: Path, state: DecompositionState) -> Result[Path]`
   - `load_state(path: Path) -> Result[DecompositionState | None]`
   - Reuses atomic write from `manifest_writer`
   - Test: `tests/unit/test_decomposition_state.py` — UT-012 (`save_state()`/`load_state()` round-trip), UT-013 (`load_state()` resume detection)

### Phase 5: Templates

8. **`src/specforge/templates/base/features/manifest.json.j2`** — Manifest template
   - Single line: `{{ manifest | tojson(indent=2) }}`
   - Rendered via `render_raw("base/features/manifest.json.j2", {"manifest": dict})`
   - `tojson` delegates to `json.dumps` — correct escaping guaranteed

9. **`src/specforge/templates/base/features/communication-map.md.j2`** — Mermaid template
   - Receives `app_name`, `architecture`, `services`, `events`, `mermaid_diagram`
   - Wraps Mermaid in code fences, adds service communication table

### Phase 6: CLI Integration

10. **`src/specforge/cli/decompose_cmd.py`** — Full command implementation
   - Replace placeholder with multi-step interactive flow
   - Add `--arch`, `--remap`, `--no-warn` options
   - Orchestrate: gate → analyze → map → review → write
   - State save/resume at each step boundary
   - Test: `tests/integration/test_decompose_flow.py` — IT-001 through IT-005

### Phase 7: Snapshot Tests

11. **`tests/snapshots/`** — Golden files
    - ST-001: manifest for "PersonalFinance" + microservice
    - ST-002: communication-map.md for same
    - ST-003: manifest for monolithic architecture

## Key Patterns

### Creating a new core module

```python
# src/specforge/core/domain_analyzer.py
from __future__ import annotations
from dataclasses import dataclass
from specforge.core.result import Err, Ok, Result

@dataclass(frozen=True)
class Feature:
    id: str
    name: str
    # ... all fields

class DomainAnalyzer:
    def __init__(self, patterns: list[dict]) -> None:
        self._patterns = patterns

    def analyze(self, description: str) -> Result:
        # ... returns Ok(DomainMatch) or Err(str)
```

### Atomic write pattern

```python
import json, os, tempfile
from pathlib import Path

def atomic_write_json(path: Path, data: dict) -> None:
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)  # flush to disk before rename
        os.close(fd)
        os.replace(tmp, str(path))
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

### Running tests

```bash
# Run all tests
uv run pytest

# Run only Feature 004 tests
uv run pytest tests/unit/test_domain_analyzer.py tests/unit/test_service_mapper.py -v

# Run with coverage
uv run pytest --cov=specforge --cov-report=term-missing

# Update snapshots
uv run pytest --snapshot-update

# Lint
uv run ruff check src/specforge/core/domain_analyzer.py
```
