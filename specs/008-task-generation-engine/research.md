# Research — Task Generation Engine

**Feature**: 008-task-generation-engine  
**Date**: 2026-03-17  
**Status**: Complete

---

## R-001: Topological Sort Algorithm Selection

**Decision**: Kahn's algorithm (BFS-based) with stable secondary sort by (phase, order).

**Rationale**: Kahn's algorithm naturally detects cycles (queue empties before all nodes processed), provides a deterministic ordering when combined with a priority queue, and is well-suited for DAGs with known in-degrees. DFS-based topological sort would also work but requires separate cycle detection logic (gray-edge detection), adding complexity without benefit.

**Alternatives considered**:
- DFS-based topological sort with post-order reversal (rejected: requires separate cycle detection pass, less intuitive for DAG construction)
- Tarjan's SCC algorithm (rejected: over-engineered for task-level DAGs with <50 nodes; designed for strongly connected components, not simple ordering)

---

## R-002: Parallel Task Detection Strategy

**Decision**: File-path disjointness at the same dependency depth level.

**Rationale**: Two tasks at the same topological depth can execute in parallel if and only if they touch disjoint file paths. This is a conservative but safe heuristic — it avoids race conditions without requiring semantic analysis of file contents. The depth-level grouping ensures parallelism only applies to tasks whose prerequisites are already satisfied.

**Alternatives considered**:
- Full dependency cone analysis (rejected: computationally expensive for marginal benefit at <50 tasks)
- Manual `[P]` annotation by the user (rejected: defeats the purpose of automated generation)
- Category-based parallelism rules (rejected: too coarse — two tasks in the same category may still conflict if they share files)

---

## R-003: Task Grouping Strategy for High Feature Counts

**Decision**: Group by technical layer, then sub-group by feature within each layer. When task count exceeds 50, collapse individual feature tasks into composite layer tasks.

**Rationale**: Grouping by layer (all models → all repositories → all services) matches the natural build dependency order and avoids redundant scaffolding. When a service has many features, individual tasks per feature per layer would produce an unmanageable list. Collapsing to "Create all domain models for features: auth, billing, reporting" keeps the list under the 50-task cap while remaining actionable.

**Alternatives considered**:
- Group by feature, then by layer within each feature (rejected: breaks dependency ordering, requires redundant scaffolding per feature)
- No grouping — flat list (rejected: unusable for services with 10+ features)

---

## R-004: Cross-Service Task ID Namespace

**Decision**: Cross-service tasks use `X-T` prefix (e.g., `X-T001`). Per-service tasks use `T` prefix. External references use `[XDEP: cross-service-infra/X-T001]` notation.

**Rationale**: Distinct prefixes prevent ID collisions between per-service and cross-service task files. The `XDEP` notation is machine-parseable (regex: `\[XDEP:\s*[\w-]+/X-T\d+\]`) and human-readable. The cross-service-infra namespace acts as a virtual service that other service task files can depend on.

**Alternatives considered**:
- Global sequential IDs across all files (rejected: requires coordination, breaks independent per-service generation)
- UUID-based task IDs (rejected: not human-readable, breaks the `T001` convention from existing template)

---

## R-005: Governance Rule Matching Heuristic

**Decision**: Match governance rules to task layers via the `scope` field in `PromptRule`. Complete mapping:

| Governance Scope | Matched Build Steps (by order) | Rationale |
|---|---|---|
| `scope: "class"` | domain_models (2) | Class-level rules apply to entity/DTO definitions |
| `scope: "function"` | repository (4), service_layer (5), communication_clients (6), controllers (7) | Function-level rules apply to method implementations |
| `scope: "module"` | scaffolding (1), container_optimization (13), gateway_config (14) | Module-level rules apply to project structure/config |
| `scope: "file"` | database (3), event_handlers (8), health_checks (9) | File-level rules apply to config-heavy/infrastructure code |
| `scope: "test"` | contract_tests (10), unit_tests (11), integration_tests (12) | Test-scoped rules apply to all test categories |
| *(unmapped)* | Steps with no matching scope | Returns empty tuple — no Prompt-rules line in output |

**Rationale**: The existing `PromptRule.scope` field already categorizes rules by the code construct they apply to. Reusing this field for task-to-rule matching avoids introducing new metadata. The mapping is approximate but good enough — a task for "Create Account entity class" correctly surfaces `scope: "class"` rules without needing exact file-level rule matching. Steps with no applicable governance scope gracefully return empty tuples.

Rule ID prefixes follow Feature 003 namespace: `ARCH-` (architecture), `BACK-` (backend), `SEC-` (security), `DB-` (database), `TEST-` (testing), `FRONT-` (frontend), `CICD-` (cicd).

**Alternatives considered**:
- Keyword matching on rule descriptions (rejected: fragile, depends on natural language)
- Explicit rule-to-layer mapping in config (rejected: requires manual maintenance, duplicates information already in rule scope)

---

## R-006: Backup Strategy for Regeneration

**Decision**: Rename existing `tasks.md` to `tasks.md.bak` before generating. Only keep one backup (overwrite previous `.bak`).

**Rationale**: Single backup is sufficient — the previous version is recoverable if the new generation has issues, and git history provides deeper history. Multiple backups (`.bak1`, `.bak2`) add clutter without value since task files are generated artifacts, not hand-edited.

**Alternatives considered**:
- Timestamped backups (`tasks.md.20260317.bak`) (rejected: clutters feature directory, git provides history)
- No backup, just overwrite (rejected: user might lose context from manual annotations added to previous tasks.md)
- Git stash before regeneration (rejected: couples task generation to git state, breaks `--no-git` workflows)
