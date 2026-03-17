# Data Model — Task Generation Engine

**Feature**: 008-task-generation-engine  
**Date**: 2026-03-17

---

## Entities

### EffortSize

A constrained type representing T-shirt effort estimates.

| Value | Description |
|-------|-------------|
| `"S"` | Small — straightforward, single-file task (scaffolding, config) |
| `"M"` | Medium — moderate complexity, 2-3 files (models, controllers) |
| `"L"` | Large — significant effort, multiple files with logic (service layer, unit tests) |
| `"XL"` | Extra-large — complex, multi-file with external dependencies (integration tests) |

**Type**: `Literal["S", "M", "L", "XL"]`

---

### BuildStep

A single step in an architecture-specific build sequence. Immutable template used to generate concrete `TaskItem` instances.

| Field | Type | Description |
|-------|------|-------------|
| `order` | `int` | Position in build sequence (1-based) |
| `category` | `str` | Machine-readable category (e.g., `"domain_models"`, `"service_layer"`) |
| `description_template` | `str` | Human-readable template with `{service}` or `{module}` placeholder |
| `default_effort` | `EffortSize` | Architecture-specific default effort size |
| `file_path_pattern` | `str` | Path template with `{service}` or `{module}` placeholder |
| `depends_on` | `tuple[int, ...]` | Order numbers of prerequisite steps |
| `parallelizable_with` | `tuple[int, ...]` | Steps that can execute concurrently with this step |

**Immutability**: Frozen dataclass. Instances are defined as module-level constants in `build_sequence.py`.

---

### TaskItem

A single actionable work item in a generated task file.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique ID scoped to task file (e.g., `"T001"`, `"X-T001"`) |
| `description` | `str` | Human-readable task description |
| `phase` | `int` | Build sequence phase group for display |
| `layer` | `str` | Technical layer (e.g., `"domain"`, `"repository"`, `"service"`) |
| `dependencies` | `tuple[str, ...]` | Task IDs — local (`"T001"`) or external (`"cross-service-infra/X-T001"`) |
| `parallel` | `bool` | `True` if can run concurrently with sibling tasks at same level |
| `effort` | `EffortSize` | T-shirt effort estimate |
| `user_story` | `str` | Reference to spec user story (e.g., `"US1"`) |
| `file_paths` | `tuple[str, ...]` | Concrete file path hints for this task |
| `service_scope` | `str` | Service/module slug this task belongs to |
| `governance_rules` | `tuple[str, ...]` | Matched prompt rule IDs (e.g., `("ARCH-001",)`) |
| `commit_message` | `str` | Suggested conventional commit message |

**Immutability**: Frozen dataclass. Built via list comprehension, then tuple-converted at `TaskFile` construction.

---

### TaskFile

A collection of ordered tasks for a single target (service, module, or cross-service-infra).

| Field | Type | Description |
|-------|------|-------------|
| `target_name` | `str` | Service/module slug or `"cross-service-infra"` |
| `architecture` | `str` | Architecture type from manifest |
| `tasks` | `tuple[TaskItem, ...]` | Topologically ordered task list |
| `phases` | `tuple[tuple[int, tuple[TaskItem, ...]], ...]` | Tasks grouped by phase number |
| `total_count` | `int` | Total number of tasks |

**Immutability**: Frozen dataclass.

---

### DependencyGraph

Internal representation of the task dependency DAG.

| Field | Type | Description |
|-------|------|-------------|
| `adjacency` | `dict[str, tuple[str, ...]]` | Task ID → IDs of tasks it depends on |
| `in_degree` | `dict[str, int]` | Task ID → number of incoming edges |
| `tasks_by_id` | `dict[str, TaskItem]` | Task ID → TaskItem lookup |
| `depth_levels` | `dict[str, int]` | Task ID → topological depth (0 = no deps) |

**Note**: Not a frozen dataclass — mutable during graph construction, then consumed by `topological_sort()` and `mark_parallel()`.

---

### GenerationSummary

Result of full-project task generation.

| Field | Type | Description |
|-------|------|-------------|
| `generated_files` | `tuple[str, ...]` | Relative paths of all tasks.md files produced |
| `task_counts` | `dict[str, int]` | Service/module slug → task count |
| `cross_dependencies` | `tuple[str, ...]` | All `[XDEP:]` references found across files |
| `warnings` | `tuple[str, ...]` | Warnings (skipped services, missing plans) |

**Immutability**: Frozen dataclass.

---

## Relationships

```
BuildStep ──defines──> TaskItem (1:N — one step per feature produces one task)
TaskItem ──belongs to──> TaskFile (N:1 — many tasks per file)
TaskItem ──depends on──> TaskItem (N:N — via dependencies tuple)
TaskItem ──references──> TaskItem in another TaskFile (via XDEP notation)
TaskFile ──summarized by──> GenerationSummary (N:1 — many files per summary)
DependencyGraph ──indexes──> TaskItem (1:N — one graph per TaskFile)
```

## Validation Rules

- `TaskItem.id` must be unique within its `TaskFile`
- `TaskItem.dependencies` must only reference IDs that exist (local) or match `[XDEP:]` pattern (external)
- `TaskFile.total_count` must equal `len(TaskFile.tasks)` and must not exceed `MAX_TASKS_PER_SERVICE` (50)
- `BuildStep.order` must be unique within a build sequence
- `BuildStep.depends_on` must only reference existing order numbers within the same sequence
- `DependencyGraph` must be acyclic — cycle detection is a hard error
- `EffortSize` must be one of `("S", "M", "L", "XL")`
- `TaskItem.commit_message` must follow Conventional Commits format: `type(scope): description`
