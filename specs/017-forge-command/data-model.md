# Data Model: Forge Command — Zero-Interaction Full Spec Generation

**Feature**: 017-forge-command
**Date**: 2026-03-19

## Entity Diagram

```text
┌──────────────────────┐       ┌──────────────────────┐
│  ForgeOrchestrator   │──────▶│     ForgeState        │
│                      │       │                       │
│  - project_root      │       │  - schema_version     │
│  - provider          │       │  - stage              │
│  - assembler         │       │  - description        │
│  - runner            │       │  - architecture       │
│  - progress          │       │  - services{}         │
│  - state             │       │  - status             │
└────────┬─────────────┘       └──────────┬────────────┘
         │                                │
         │ uses                           │ contains
         │                                ▼
         │                       ┌──────────────────────┐
         │                       │ ServiceForgeStatus   │
         │                       │                       │
         │                       │  - slug               │
         │                       │  - last_completed_phase│
         │                       │  - status              │
         │                       │  - retry_count         │
         │                       │  - error               │
         │                       │  - last_update         │
         │                       └──────────────────────┘
         ▼
┌──────────────────────┐       ┌──────────────────────┐
│  LLMProvider         │       │  ArtifactExtractor   │
│  (Protocol)          │       │                       │
│                      │       │  - extract_spec()      │
│  + call()            │       │  - extract_research()  │
│  + is_available()    │       │  - extract_datamodel() │
└──────────────────────┘       │  - extract_edgecases() │
                               │  - extract_plan()      │
┌──────────────────────┐       │  - format_for_prompt() │
│ EnrichedPromptBuilder│       └──────────────────────┘
│                      │
│  - template_dir      │       ┌──────────────────────┐
│  - jinja_env         │       │  ForgeProgress       │
│                      │       │                       │
│  + build()           │       │  - live (Rich.Live)   │
│                      │       │  - table (Rich.Table) │
└──────────────────────┘       │  - update_queue       │
                               │                       │
┌──────────────────────┐       │  + on_phase_start()   │
│    ForgeReport       │       │  + on_service_complete │
│                      │       │  + set_stage()        │
│  - services[]        │       │  + finish()           │
│  - failures[]        │       └──────────────────────┘
│  - timing{}          │
│  - total_elapsed     │
│                      │
│  + render()          │
└──────────────────────┘
```

## Entities

### ForgeOrchestrator

Top-level coordinator that sequences all forge stages.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| _project_root | Path | required | Project root directory |
| _provider | LLMProvider | required | LLM provider instance (SubprocessProvider) |
| _assembler | PromptAssembler | required | Prompt assembly with artifact extraction |
| _runner | ParallelPipelineRunner | required | Parallel spec generation engine (Feature 016) |
| _progress | ForgeProgress | required | Live dashboard display |
| _state | ForgeState | mutable | Current forge run state |
| _max_retries | int | default=3 | Max retries per service before permanent failure |
| _dry_run | bool | default=False | Preview mode — no LLM calls |

**Methods**:
- `forge(description, arch, stack, options) -> Result[ForgeReport, str]` — Main entry point
- `_auto_init(stack) -> Result[None, str]` — Auto-initialize `.specforge/` if missing
- `_llm_decompose(description, arch) -> Result[None, str]` — LLM-based decomposition
- `_fallback_decompose(description, arch) -> Result[None, str]` — Rule-based fallback
- `_run_parallel_specs(services, max_parallel) -> Result[None, str]` — Parallel spec gen
- `_validate_and_report() -> ForgeReport` — Validate artifacts and generate report
- `_load_or_create_state(description, arch) -> ForgeState` — State management
- `_save_state(state) -> None` — Persist state to forge-state.json

**State Transitions**: idle → init → decompose → spec_generation → validation → complete/failed

### ForgeState

Persisted state for a forge run, enabling resume after interruption.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| schema_version | str | "1.0" | Schema version for forward compatibility |
| stage | str | one of FORGE_STAGES | Current forge stage |
| description | str | required | Original project description |
| architecture | str | required, one of VALID_ARCHITECTURES | Architecture type |
| services | dict[str, ServiceForgeStatus] | default={} | Per-service status map |
| started_at | str | ISO 8601 | Forge run start timestamp |
| last_update | str | ISO 8601 | Last state update timestamp |
| status | str | "idle" or "running" | Current run status for lock detection |
| pid | int \| None | optional | Process ID of running forge (for lock) |
| lock_timestamp | str \| None | optional | When lock was acquired (for stale detection) |

**Serialization**: JSON to `.specforge/forge-state.json` via `json.dumps()` / `json.loads()` with `os.replace()` atomic write.

**Validation Rules**:
- `schema_version` must be "1.0"
- `architecture` must be in `VALID_ARCHITECTURES`
- `started_at` must be valid ISO 8601
- `services` keys must match service slugs from manifest.json

### ServiceForgeStatus

Per-service tracking within a forge run.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| slug | str | required, matches manifest | Service slug identifier |
| last_completed_phase | int | 0–7 (0=not started) | Last successfully completed phase index |
| status | str | pending/in_progress/complete/failed/permanently_failed | Current service status |
| retry_count | int | 0 ≤ n ≤ max_retries | Number of full-service retries |
| error | str \| None | optional | Last error message if failed |
| last_update | str | ISO 8601 | Last update timestamp |

**State Transitions per phase**: pending → in-progress → complete | failed
**Service-level**: pending → in-progress → complete | permanently_failed (after max_retries)

### ArtifactExtractor

Extracts structured information from markdown artifacts for prompt assembly.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| (stateless) | — | — | All methods are pure functions |

**Methods**:
- `extract_spec(text) -> dict` — Extract user stories, FR-IDs, NFRs, edge case refs
- `extract_research(text) -> dict` — Extract decisions as key-value pairs
- `extract_datamodel(text) -> dict` — Extract entities, fields, relationships
- `extract_edgecases(text) -> dict` — Extract edge case IDs, severity, categories
- `extract_plan(text) -> dict` — Extract phases, file structure, tech context
- `format_for_prompt(phase, extractions) -> str` — Render extractions as clean markdown

**Extraction Output Schema**:
```python
# extract_spec returns:
{
    "user_stories": [{"title": str, "priority": str, "scenario_count": int}],
    "functional_requirements": [{"id": str, "text": str}],
    "nonfunctional_requirements": [str],
    "edge_cases_from_spec": [str],
    "success_criteria": [{"id": str, "text": str}],
}

# extract_research returns:
{
    "decisions": [{"topic": str, "decision": str, "rationale": str}],
}

# extract_datamodel returns:
{
    "entities": [{"name": str, "field_count": int, "relationships": [str]}],
}

# extract_edgecases returns:
{
    "edge_cases": [{"id": str, "title": str, "severity": str, "category": str}],
}
```

### EnrichedPromptBuilder

Renders Jinja2 enrichment templates for detailed phase system instructions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| _template_dir | Path | required | Path to enrichment templates directory |
| _env | jinja2.Environment | lazy init | Jinja2 environment with FileSystemLoader |

**Methods**:
- `build(phase, service_ctx, adapter, governance) -> str` — Render enrichment template for a phase
- `_get_thresholds() -> dict` — Load quality thresholds from config constants

**Template Variables** (available in all enrichment templates):
- `service` — ServiceContext dataclass
- `architecture` — Architecture type string
- `governance_rules` — Rendered governance prompt text
- `quality_thresholds` — Dict of code quality limits (function_lines, class_lines, etc.)
- `phase_name` — Current phase name
- `features` — List of FeatureInfo for the service

### ForgeProgress

Rich Live dashboard for real-time forge progress display.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| _console | Console | required | Rich Console instance |
| _live | Live | created on enter | Rich Live context manager |
| _table | Table | created on init | Rich Table for per-service status |
| _services | tuple[str, ...] | required | Service slugs being forged |
| _stage | str | mutable | Current overall stage name |
| _start_time | float | set on start | time.monotonic() at forge start |
| _update_queue | Queue | thread-safe | Queue for thread-safe updates |

**Methods** (implements ProgressTracker protocol):
- `on_phase_start(slug, phase) -> None` — Update service row to show active phase
- `on_service_complete(slug) -> None` — Mark service row as complete
- `on_service_failed(slug, error) -> None` — Mark service row as failed
- `set_stage(stage_name) -> None` — Update overall stage display
- `finish(report) -> None` — Display final summary
- `drain_updates() -> None` — Process queued updates (called from render thread)

### ForgeReport

Completion report data model rendered to forge-report.md.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| services | list[ServiceReportEntry] | required | Per-service artifact inventory |
| failures | list[FailureEntry] | may be empty | Failed services with diagnostics |
| timing | dict[str, float] | required | Per-stage elapsed seconds |
| total_elapsed | float | required | Total forge duration in seconds |
| total_artifacts | int | computed | Count of all generated artifacts |
| total_services | int | computed | Count of all services |

**Nested Types**:

```python
@dataclass(frozen=True)
class ServiceReportEntry:
    slug: str
    artifacts: tuple[str, ...]  # filenames of generated artifacts
    missing: tuple[str, ...]    # expected but missing artifacts

@dataclass(frozen=True)
class FailureEntry:
    slug: str
    phase: str          # phase where failure occurred
    error: str          # error message
    retry_count: int    # number of retries attempted
```

## Relationships

| Source | Target | Relationship | Description |
|--------|--------|-------------|-------------|
| ForgeOrchestrator | ForgeState | owns (1:1) | Orchestrator manages forge state lifecycle |
| ForgeOrchestrator | ForgeProgress | owns (1:1) | Orchestrator owns the live dashboard |
| ForgeOrchestrator | LLMProvider | uses (1:1) | Orchestrator delegates LLM calls |
| ForgeOrchestrator | ParallelPipelineRunner | uses (1:1) | Orchestrator delegates parallel execution |
| ForgeOrchestrator | ForgeReport | produces (1:1) | Orchestrator generates completion report |
| ForgeState | ServiceForgeStatus | contains (1:N) | State tracks per-service status |
| SubprocessProvider | LLMProvider | implements | Existing CLI provider (unchanged) |
| PromptAssembler | ArtifactExtractor | uses (1:1) | Assembler uses extractor for structured context |
| PromptAssembler | EnrichedPromptBuilder | uses (1:1) | Assembler uses builder for enriched instructions |
| ForgeProgress | ProgressTracker | implements | Dashboard satisfies tracker protocol |
| ForgeReport | ServiceReportEntry | contains (1:N) | Report lists per-service results |
| ForgeReport | FailureEntry | contains (0:N) | Report lists failure diagnostics |
