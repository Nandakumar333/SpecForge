# Research — Research & Clarification Engine

**Feature**: 006-research-clarification-engine
**Date**: 2026-03-16

## R1: Pattern-Based Ambiguity Detection Approach

**Decision**: Regex + keyword list heuristics with configurable pattern tuples

**Rationale**: SpecForge operates offline without LLM calls during clarification. Regex patterns provide deterministic, fast detection of vague terms and structural ambiguities. The pattern tuple is constructor-injected, allowing easy extension without modifying core logic.

**Alternatives considered**:
- NLP-based analysis (spaCy): Rejected — adds heavy dependency for marginal improvement on structured spec text
- LLM-based analysis: Rejected — spec explicitly requires no external API calls; would add latency and cost
- Static keyword list only: Rejected — too rigid; regex captures contextual patterns (e.g., "or" between options)

## R2: Spec.md Modification Strategy

**Decision**: Append-only Clarifications section with atomic write via temp file + os.replace()

**Rationale**: Matches the atomic write pattern used by ManifestWriter (Feature 004). Append-only prevents accidental data loss from previous sessions. The `## Clarifications` / `### Session YYYY-MM-DD` structure is simple to parse and idempotent to locate.

**Alternatives considered**:
- Separate clarifications.json file: Rejected — answers should live alongside the spec for visibility; JSON adds parsing overhead
- In-place marker replacement: Rejected — modifying spec sections risks corrupting user-written content; append-only is safer
- YAML frontmatter in spec.md: Rejected — spec.md is Markdown with no existing frontmatter convention

## R3: Service Boundary Detection via Manifest Analysis

**Decision**: Extract feature keywords from manifest.json feature descriptions, cross-reference across services to find shared concepts

**Rationale**: Manifest.json already contains structured feature-to-service mappings with descriptions. Keyword extraction from descriptions (splitting on spaces, filtering stop words) provides a lightweight way to detect shared concepts without needing data-model.md (which may not exist yet at clarification time).

**Alternatives considered**:
- Parse data-model.md entities: Rejected — data-model.md is generated in Phase 3, after clarification should run
- Require user-defined entity list: Rejected — adds manual step that defeats automation purpose
- Full NLP entity extraction: Rejected — over-engineered for structured manifest descriptions

## R4: Interactive CLI Pattern for Clarification

**Decision**: Rich `Prompt.ask` with numbered options, one question at a time, consistent with Feature 004 decompose flow

**Rationale**: Feature 004's decompose command already established the interactive pattern using Rich prompts. Users are familiar with this UX. One-at-a-time presentation prevents overwhelm and allows early termination.

**Alternatives considered**:
- All questions at once (batch mode): Rejected — overwhelming for 10+ questions; user can't assess context per question
- TUI with curses/textual: Rejected — over-engineered; Rich prompts are sufficient and already in the dependency tree
- Web-based questionnaire: Rejected — SpecForge is a CLI tool

## R5: Research Finding Status Model

**Decision**: 4-status enum: RESOLVED, UNVERIFIED, BLOCKED, CONFLICTING

**Rationale**: RESOLVED and BLOCKED are standard. UNVERIFIED fills the gap for findings based on embedded knowledge where external verification isn't possible (per spec requirement of no network calls). CONFLICTING is a new status (from clarification session) for when multiple reasonable answers exist.

**Alternatives considered**:
- 3-status (drop CONFLICTING): Rejected — spec clarification explicitly requires CONFLICTING status for disagreeing sources
- 5-status (add DEPRECATED): Rejected — no use case for deprecated findings in current scope
- Confidence score instead of enum: Rejected — discrete statuses are more actionable than continuous scores

## R6: Architecture Remap Detection

**Decision**: Check manifest.json for `previous_architecture` field set by `--remap` command

**Rationale**: Feature 004's `--remap` command modifies manifest.json. Adding a `previous_architecture` field to the manifest metadata during remap is the cleanest integration point — no additional state files needed. BoundaryAnalyzer checks for this field to determine if remap-specific questions should be generated.

**Alternatives considered**:
- Separate remap-history.json file: Rejected — adds another state file; manifest.json is the single source of truth for architecture decisions
- Git history analysis: Rejected — fragile; depends on commit messages and may not work in fresh clones
- User flag (`--post-remap`): Rejected — manual step that could be forgotten; automatic detection is more reliable

## R7: Clarification Question Ranking

**Decision**: Fixed priority order by category: service_boundary > domain > technical > communication

**Rationale**: Service boundary questions have the highest architectural impact (wrong answer requires service restructuring). Domain questions affect business logic correctness. Technical questions affect implementation details. Communication questions are lowest impact as patterns can be changed with less effort.

**Alternatives considered**:
- User-configurable priority: Rejected — over-engineering; fixed order covers the 80% case
- ML-based impact scoring: Rejected — no training data available; heuristic ordering is sufficient
- Random/alphabetical: Rejected — doesn't surface high-impact questions first

## R8: Integration with Existing Pipeline State

**Decision**: `specforge research` command updates `.pipeline-state.json` research phase to "complete"; `specforge clarify` does NOT update pipeline state

**Rationale**: Research.md is a pipeline artifact (Phase 2) — updating state ensures the pipeline knows research is done. Clarification modifies spec.md (Phase 1 artifact) but is not itself a pipeline phase — it's an optional pre-planning step. Updating Phase 1 state would incorrectly signal spec needs regeneration.

**Alternatives considered**:
- Both update pipeline state: Rejected — clarify is optional and shouldn't force pipeline re-runs
- Neither updates pipeline state: Rejected — research command should be a first-class alternative to the pipeline's ResearchPhase
- Add new "clarify" phase to pipeline: Rejected — clarification is interactive and shouldn't block automated pipeline execution
