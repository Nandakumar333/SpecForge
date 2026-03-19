# Parallel Execution Engine Checklist: 016-parallel-execution-engine

**Purpose**: Validate requirements completeness, clarity, and consistency for parallel spec generation and implementation across all architecture modes
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

## Decompose --auto --parallel Flow Completeness

- [ ] CHK001 - Are requirements for how `--auto` selects architecture type specified (LLM-chosen vs default fallback)? [Completeness, Spec §FR-002]
- [ ] CHK002 - Is the interaction between `--auto` and `--arch` defined (explicit arch + auto = skip selection, or conflict)? [Clarity, Gap]
- [ ] CHK003 - Are requirements for which interactive prompts `--auto` suppresses enumerated exhaustively? [Completeness, Spec §FR-002]
- [ ] CHK004 - Is the ordering between decomposition (AI discovery) and parallel pipeline launch specified (sequential then parallel, or overlapping)? [Clarity, Spec §US1-AS1]
- [ ] CHK005 - Are requirements defined for what happens when the AI provider returns zero services/features during `--auto` discovery? [Edge Case, Gap]
- [ ] CHK006 - Is the behavior specified when `--parallel` is used but only 1 service is discovered (degenerate case)? [Edge Case, Gap]
- [ ] CHK007 - Are requirements for `--auto` without `--parallel` (auto discovery, sequential pipeline) documented as a valid combination? [Completeness, Spec §Edge Cases]

## Dependency Graph & Service Grouping

- [ ] CHK008 - Are requirements for how the dependency graph is extracted from `manifest.json` specified (which fields define dependencies)? [Clarity, Spec §FR-004]
- [ ] CHK009 - Is the behavior defined when `manifest.json` has services with no `communication[]` entries (all independent → single wave)? [Completeness, Gap]
- [ ] CHK010 - Are requirements for transitive dependency handling specified (A→B→C: does C wait for both A and B)? [Clarity, Spec §FR-004]
- [ ] CHK011 - Is the wave assignment algorithm specified with enough precision to be deterministic (e.g., alphabetical tiebreaking within a wave)? [Clarity, Gap]
- [ ] CHK012 - Are requirements defined for how self-referencing dependencies (service depends on itself) are handled? [Edge Case, Gap]
- [ ] CHK013 - Is the maximum number of waves bounded or specified for scale scenarios (20 services in a chain = 20 waves)? [Completeness, Spec §SC-008]

## Implement --all --parallel & Wave Execution

- [ ] CHK014 - Are requirements for shared infrastructure phase ordering relative to wave execution explicitly specified (infra completes before wave 1)? [Completeness, Spec §Edge Cases]
- [ ] CHK015 - Is the behavior defined when `--parallel` is used without `--all` on the implement command? [Clarity, Gap]
- [ ] CHK016 - Are requirements for contract verification between waves specified (after wave N, verify contracts before wave N+1)? [Completeness, Gap]
- [ ] CHK017 - Is "blocked" status propagation defined for transitive dependents (if A fails, and B depends on A, and C depends on B — is C also blocked)? [Clarity, Spec §FR-007]
- [ ] CHK018 - Are requirements for partial wave completion defined (3 of 4 services in a wave succeed — does the wave status become "partial")? [Completeness, Spec §US2-AS6]
- [ ] CHK019 - Is the sub-agent isolation model specified (separate process per service, shared process with thread isolation, etc.)? [Clarity, Spec §FR-005]

## Dashboard & Progress Reporting

- [ ] CHK020 - Are requirements for the inline progress output format specified with enough precision to be parseable (structured prefix, separators)? [Clarity, Spec §FR-017]
- [ ] CHK021 - Is the dashboard state file format documented (schema for `.specforge/parallel-state.json`)? [Completeness, Spec §FR-009]
- [ ] CHK022 - Are requirements defined for how the dashboard distinguishes between parallel and sequential runs? [Coverage, Gap]
- [ ] CHK023 - Is the refresh interval for dashboard-readable state updates specified (every phase completion, every N seconds, or both)? [Clarity, Spec §SC-004]
- [ ] CHK024 - Are requirements for the completion summary format specified (which fields: per-service timing, phase counts, error messages)? [Completeness, Spec §FR-014]
- [ ] CHK025 - Is the behavior defined when `specforge status --watch` is running and a parallel operation has not yet started any services (empty state)? [Edge Case, Gap]

## Concurrency Safety & File Locking

- [ ] CHK026 - Are requirements for thread-safe console output specified (preventing interleaved output from concurrent workers)? [Completeness, Gap]
- [ ] CHK027 - Is the locking scope defined for `parallel-state.json` writes (per-write lock, or higher-level synchronization)? [Clarity, Spec §FR-006]
- [ ] CHK028 - Are requirements defined for what happens when two parallel runs of the same command are launched simultaneously (cross-process safety)? [Edge Case, Gap]
- [ ] CHK029 - Is the stale lock threshold for parallel execution defined (same 30-min as pipeline lock, or different)? [Clarity, Gap]
- [ ] CHK030 - Are requirements for atomic state transitions during SIGINT specified (is the state file guaranteed consistent after interruption)? [Completeness, Spec §FR-013]
- [ ] CHK031 - Is the behavior defined when a worker thread deadlocks or hangs indefinitely (timeout per service pipeline)? [Edge Case, Gap]

## Monolith Mode Requirements

- [ ] CHK032 - Are the artifacts that monolith mode must NOT generate exhaustively listed (Docker, contracts, API gateway, service mesh)? [Completeness, Spec §US4-AS3]
- [ ] CHK033 - Is the modular-monolith dependency model specified separately from microservice (which manifest fields define module boundaries)? [Clarity, Spec §FR-011]
- [ ] CHK034 - Are requirements for "shared-entity dependencies" in modular-monolith quantified (what constitutes a shared entity)? [Clarity, Spec §US4-AS2]
- [ ] CHK035 - Is the behavior defined when a monolith project has `communication[]` entries in the manifest (ignore them, or use them for ordering)? [Ambiguity, Gap]
- [ ] CHK036 - Are requirements consistent between US4-AS1 ("no inter-module dependency graph") and FR-011 ("boundary-aware sequencing" for modular-monolith)? [Consistency, Spec §FR-011 vs §US4]

## CLI Flag Requirements

- [ ] CHK037 - Is `--max-parallel` input validation specified (minimum value, non-integer handling, zero or negative values)? [Completeness, Spec §FR-016]
- [ ] CHK038 - Are requirements for `--fail-fast` without `--parallel` defined (ignored silently, warning, or error)? [Clarity, Spec §FR-015]
- [ ] CHK039 - Is the precedence between `--max-parallel` and `parallel.max_workers` in config.json unambiguously stated (CLI always wins)? [Clarity, Spec §FR-003]
- [ ] CHK040 - Are exit codes for partial success vs total failure vs cancellation specified? [Completeness, Gap]
- [ ] CHK041 - Is the behavior defined when `--parallel` is combined with `--template-mode` or `--dry-run-prompt` on decompose? [Coverage, Gap]
- [ ] CHK042 - Are requirements for `--max-parallel` with a value exceeding available services consistent with edge case documentation? [Consistency, Spec §Edge Cases vs §FR-016]

## Backward Compatibility & Regression Safety

- [ ] CHK043 - Are requirements stated that sequential mode (no `--parallel` flag) behavior MUST remain unchanged? [Completeness, Gap]
- [ ] CHK044 - Is backward compatibility for existing `.specforge/config.json` files without `parallel` key specified (graceful default)? [Completeness, Gap]
- [ ] CHK045 - Are requirements defined for existing pipeline state files compatibility (can sequential runs resume parallel state and vice versa)? [Coverage, Gap]
- [ ] CHK046 - Is the interaction with existing `--force` and `--from` flags on specify/implement defined for parallel mode? [Completeness, Gap]
- [ ] CHK047 - Are requirements for `specforge decompose` without any new flags documented as unchanged behavior? [Completeness, Gap]

## Resume & Error Recovery

- [ ] CHK048 - Is the resume detection mechanism specified (how does the system know a previous parallel run was interrupted)? [Clarity, Spec §FR-008]
- [ ] CHK049 - Are requirements defined for resuming after a `--fail-fast` cancellation (retry failed + cancelled, or only failed)? [Completeness, Gap]
- [ ] CHK050 - Is the behavior specified when resuming with a different `--max-parallel` value than the original run? [Edge Case, Gap]
- [ ] CHK051 - Are requirements for clearing/resetting parallel state defined (equivalent of `--force` for parallel state)? [Completeness, Gap]
- [ ] CHK052 - Is the double-SIGINT behavior (second Ctrl+C forces immediate exit) specified with requirements for state consistency? [Clarity, Gap]

## Notes

- Focus areas: decompose flow, dependency graph, implement waves, dashboard, concurrency safety, monolith mode, CLI flags, backward compatibility
- Depth: Standard (PR reviewer audience)
- 8 user-specified must-have areas all covered
- Items are numbered CHK001-CHK052 for cross-referencing
- [Gap] markers indicate requirements not yet documented in spec
- [Consistency] markers highlight potential conflicts between spec sections
