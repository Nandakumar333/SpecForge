# Feature Specification: Architecture Decision Gate & Smart Feature-to-Service Mapper

**Feature Branch**: `004-architecture-decomposer`
**Created**: 2026-03-15
**Status**: Draft
**Input**: User description: "Build the Architecture Decision Gate and Smart Feature-to-Service Mapper for SpecForge's specforge decompose command"

## User Scenarios & Testing

### User Story 1 — Architecture Decision Gate (Priority: P1)

As a developer running `specforge decompose`, I want the system to ask me which architecture pattern I prefer before decomposing features, so the output matches my project intent.

**Why this priority**: Every downstream artifact (feature directories, service mappings, manifest, dependency graphs) depends on the architecture choice. Without this gate, the system cannot produce correct output. This is the entry point for the entire decompose flow.

**Independent Test**: Run `specforge decompose "Create a personal finance webapp"` and verify the CLI immediately presents the architecture prompt. Selecting each option produces the correct downstream behavior without errors.

**Acceptance Scenarios**:

1. **Given** a user runs `specforge decompose "Create PersonalFinance webapp"`, **When** the CLI starts the decompose flow, **Then** it presents three architecture options: Monolithic, Microservice, Modular Monolith — and does NOT proceed until the user answers.
2. **Given** the user selects "Monolithic", **When** decomposition completes, **Then** all features are organized as modules within a single application, no service-level mapping is performed, and each module still gets its own spec/plan/tasks pipeline.
3. **Given** the user selects "Microservice", **When** decomposition completes, **Then** the system proceeds to feature decomposition followed by the feature-to-service mapping step.
4. **Given** the user selects "Modular Monolith", **When** decomposition completes, **Then** features are organized as strict modules with enforced boundaries, similar to microservice modules but targeting a single deployable unit.

---

### User Story 2 — Feature Decomposition from App Description (Priority: P1)

As a developer, I want the system to analyze my one-line application description and produce a prioritized list of 8–15 features using domain knowledge patterns, so I have a comprehensive feature breakdown without manual effort.

**Why this priority**: Feature decomposition is the core value proposition of the `decompose` command. Without it, there is nothing to map to services or modules. Equal priority with US1 because both are required for the minimum viable flow.

**Independent Test**: Run `specforge decompose "Create a personal finance webapp"`, select any architecture, and verify the system produces a numbered list of 8–15 domain-appropriate features with names and short descriptions.

**Acceptance Scenarios**:

1. **Given** the user provides a clear domain description ("Create a personal finance webapp"), **When** the decomposer analyzes it, **Then** it produces 8–15 features with sequential IDs (001, 002, ...), descriptive names, and one-line descriptions.
2. **Given** the user provides a vague description ("Build an app"), **When** the decomposer cannot determine a clear domain, **Then** it enters clarification mode and asks 3–5 targeted questions before proceeding.
3. **Given** the user provides a description for a simple application ("Build a TODO list"), **When** fewer than 5 features are identified, **Then** the system produces the small feature set without padding, and proceeds normally.
4. **Given** the description yields more than 15 features, **When** decomposition completes, **Then** the system warns about complexity and suggests consolidating related features, displaying the full list for user review.

---

### User Story 3 — Smart Feature-to-Service Mapping (Priority: P2)

As a developer choosing microservices, I want features intelligently grouped into services using domain-driven design principles, so I don't end up with one service per feature.

**Why this priority**: Service mapping is only relevant for microservice and modular monolith architectures (not monolithic). It adds significant value but depends on US1 and US2 being complete first.

**Independent Test**: After feature decomposition with "Microservice" selected, verify the mapper produces 40–70% fewer services than features, with each service containing a WHY COMBINED or WHY SEPARATE rationale.

**Acceptance Scenarios**:

1. **Given** the user chose "Microservice" and 12 features were identified, **When** the feature-to-service mapper runs, **Then** it produces 7–9 services with clear rationale (WHY COMBINED or WHY SEPARATE) for each grouping.
2. **Given** the mapping is produced, **When** the user reviews it, **Then** they can approve, or modify the mapping (combine services, split services, rename services, add services, remove services) interactively.
3. **Given** the user approves or edits the mapping, **When** confirmation is received, **Then** the final mapping is persisted to `manifest.json` with architecture type, service definitions, and feature assignments.
4. **Given** the user chose "Microservice" for a simple 3-feature app, **When** the mapper runs, **Then** it warns "This project has 3 features. Microservices may be over-engineering. Consider Modular Monolith." and asks whether to proceed or switch architecture, respecting the user's final decision.

---

### User Story 4 — Interactive Mapping Review and Edit (Priority: P2)

As a developer, I want to review and interactively edit the proposed service mapping before it is finalized, so I maintain full control over architectural decisions.

**Why this priority**: Without review capability, developers must accept automated decisions blindly. This is critical for trust but depends on the mapping being generated first (US3).

**Independent Test**: After mapping is generated, verify the interactive review presents the full mapping and accepts edit commands (combine, split, rename, add, remove) that correctly mutate the mapping.

**Acceptance Scenarios**:

1. **Given** the mapper produced 8 services, **When** the user sees the proposed mapping, **Then** each service shows its name, contained features, and rationale.
2. **Given** the user wants to combine two services, **When** they issue a combine command, **Then** the two services merge into one, features are reassigned, and the rationale is updated.
3. **Given** the user wants to split a service, **When** they issue a split command, **Then** they select which features move to the new service, and both services get updated rationale.
4. **Given** the user wants to rename a service, **When** they issue a rename command, **Then** the service name changes while preserving all feature assignments and rationale.
5. **Given** a feature appears in two services after editing, **When** validation runs, **Then** the system reports an error — each feature MUST map to exactly one service.

---

### User Story 5 — Service Communication Map (Priority: P3)

As a developer, I want to see how services will communicate after mapping is complete, so I understand the integration complexity before committing.

**Why this priority**: Communication patterns are a planning aid, not strictly required for decomposition to be useful. They depend on the finalized mapping (US3/US4).

**Independent Test**: After approving a microservice mapping, verify the output includes a communication map showing which services call which, with the pattern type labeled for each connection.

**Acceptance Scenarios**:

1. **Given** the microservice mapping is finalized, **When** the communication map is generated, **Then** it shows directed connections between services labeled with the communication pattern (sync REST, sync gRPC, or async event).
2. **Given** the communication map is generated, **When** the user reviews it, **Then** it is also persisted as a dependency graph in the manifest and as a visual diagram.

---

### User Story 6 — Architecture Re-mapping (Priority: P3)

As a developer who previously decomposed with one architecture, I want to re-map to a different architecture without losing my feature definitions, so I can change my mind without starting over.

**Why this priority**: Re-mapping is a recovery/iteration feature. It's valuable for workflow flexibility but not required for the initial decompose flow.

**Independent Test**: Run `specforge decompose --remap microservice` on a project that was previously decomposed as monolithic, and verify features are preserved but re-mapped to service boundaries, with no existing spec files deleted.

**Acceptance Scenarios**:

1. **Given** the user previously decomposed with "Monolithic" architecture, **When** they run `specforge decompose --remap microservice`, **Then** existing features are preserved and re-mapped to service boundaries.
2. **Given** existing spec files exist in feature directories, **When** re-mapping occurs, **Then** those files are NOT deleted — only the manifest and directory structure are updated.
3. **Given** the user re-maps from microservice to monolithic, **When** re-mapping completes, **Then** service boundaries are removed and features become modules, preserving all feature content.

---

### User Story 7 — Persistence and Resumption (Priority: P2)

As a developer, I want each step of the decompose flow to be saved to disk immediately, so I can resume if the CLI is interrupted or if I close my terminal.

**Why this priority**: The decompose flow is multi-step and interactive. Losing progress on a long session is a poor experience. Critical for reliability.

**Independent Test**: Start a decompose flow, select architecture, complete feature decomposition, then kill the CLI. Re-run `specforge decompose` and verify it offers to resume from where it left off.

**Acceptance Scenarios**:

1. **Given** the user completes the architecture selection step, **When** the CLI is terminated before feature decomposition, **Then** re-running `specforge decompose` detects the saved state and offers to resume from the next step.
2. **Given** the user completes feature decomposition and service mapping, **When** they re-run `specforge decompose`, **Then** the system detects the existing manifest and asks whether to start fresh or modify the existing decomposition.
3. **Given** state is persisted after each step, **When** the entire flow completes, **Then** the final `manifest.json` is valid and contains the full architecture type, feature list, service mapping (if applicable), and communication patterns.

---

### Edge Cases

- **Vague description**: User provides "Build an app" with no domain context → system enters clarification mode with 3–5 targeted questions (e.g., "What domain?", "Who are the users?", "What's the core action?").
- **Microservice for simple app**: User picks microservice for a 3-feature TODO app → system warns about over-engineering and suggests modular monolith, but respects user's final decision.
- **Unrecognized domain**: Description doesn't match known domain patterns → falls back to generic feature patterns (Authentication, CRUD, Admin, Reporting, Notifications).
- **Excessive features**: More than 15 features generated → warn about complexity, suggest consolidation, display full list for user review.
- **Feature in two services**: Interactive editing causes a feature to appear in two services → validation error, user must resolve before confirming.
- **Circular service dependencies**: Service A depends on B depends on C depends on A → detect and report the cycle, suggest breaking it with shared contracts or async events.
- **Gibberish input**: Description is nonsensical ("asdf qwer zxcv") → helpful error message with example prompts.
- **Custom service names**: User wants to rename "Ledger Service" to "Accounting Service" → allow renaming while preserving feature mapping.
- **Re-map after specs exist**: User re-maps architecture after specs have been written in feature directories → preserve all spec files, only update manifest and directory structure.
- **Interrupted flow**: CLI killed mid-flow → state is persisted at each step, resumable on next run.

## Requirements

### Functional Requirements

#### Architecture Decision Gate

- **FR-001**: System MUST present an architecture selection prompt with three options (Monolithic, Microservice, Modular Monolith) before any feature decomposition occurs — unless the `--arch` flag is provided, in which case the flag value is used directly without prompting.
- **FR-002**: System MUST NOT proceed to feature decomposition until the user has made an architecture selection (interactively or via `--arch` flag).
- **FR-003**: Each architecture option MUST include a one-line description explaining its meaning and tradeoffs.
- **FR-035**: The `--arch [monolithic|microservice|modular-monolith]` flag MUST bypass the interactive architecture prompt and use the specified value directly. This enables CI/CD and scripted usage.
- **FR-036**: On first run (no existing `manifest.json`), the architecture prompt MUST be shown (unless `--arch` is given). On subsequent runs with an existing manifest, the system MUST ask whether to resume, modify, or start fresh — it MUST NOT re-ask the architecture question.
- **FR-037**: If the user interrupts the flow (Ctrl+C) at any step, the system MUST save whatever state has been completed so far. The next run MUST detect saved partial state and offer to resume from the last completed step.
- **FR-047**: If `--arch` receives an invalid value (not one of `monolithic`, `microservice`, `modular-monolith`), the system MUST exit with code 1 and display: "Invalid architecture '{value}'. Valid options: monolithic, microservice, modular-monolith".
- **FR-048**: If both `--arch` and `--remap` are provided in the same invocation, the system MUST exit with code 1 and display: "Cannot use --arch and --remap together. Use --arch for new projects or --remap to change existing architecture."

#### Feature Decomposition

- **FR-004**: System MUST analyze the user-provided application description and produce a list of 8–15 features for recognized domains.
- **FR-005**: Each generated feature MUST have a sequential numeric ID (001, 002, ...), a descriptive name, a one-line description, and an assigned priority level (P0=foundation, P1=core, P2=important, P3=nice-to-have). Priority is determined by dependency depth: features that other features depend on get higher priority.
- **FR-006**: When the description is too vague to determine a domain, the system MUST enter a clarification mode. "Too vague" is defined as: zero domain patterns match with a keyword score ≥ 2 (i.e., fewer than 2 keywords from any single domain pattern appear in the description). The system then asks 3–5 targeted questions.
- **FR-007**: When the description matches no known domain pattern, the system MUST fall back to generic feature patterns (Authentication, CRUD operations, Admin panel, Reporting, Notifications) and then present the list for user editing (add/remove/rename).
- **FR-008**: When more than 15 features are identified, the system MUST warn the user about complexity and suggest consolidation before proceeding.
- **FR-009**: When fewer than 5 features are identified, the system MUST proceed normally without padding artificial features.
- **FR-010**: When the user provides gibberish or empty-semantic input, the system MUST display a helpful error with 2–3 example prompts.
- **FR-058**: The clarification mode (FR-006) MUST use 5 generic question templates stored in `domain_patterns.py`: (1) "What domain or industry is this application for?", (2) "Who are the primary users?", (3) "What is the core action users perform?", (4) "What scale do you expect (personal, team, enterprise)?", (5) "Are there any external integrations (payments, APIs, social login)?". User answers are concatenated with the original description and re-scored against domain patterns.
- **FR-038**: The system MUST ship with 6 built-in domain knowledge patterns in v1: finance, e-commerce, SaaS, social, healthcare, and education. Each pattern is a Python dictionary in `core/domain_patterns.py`.
- **FR-039**: Domain patterns are NOT combinable in v1. When the description matches multiple domains, the system MUST pick the single best match based on keyword scoring. Domain combination is deferred to a future version. Keyword scoring algorithm: each domain pattern defines a list of weighted keywords (weight 1–3). The description is tokenized into lowercase words. For each domain, sum the weights of all matching keywords. The domain with the highest total score wins. Ties are broken by domain list order in `DOMAIN_PATTERNS`.
- **FR-040**: Mapping combining/separation rules and rationale templates MUST be hard-coded in Python (not configurable YAML/JSON). Rationale text is generated from rule-based string templates (e.g., "Combined: shared bounded context — {feature_a} and {feature_b} access the same data"). No LLM dependency.
- **FR-049**: Each domain pattern dictionary MUST have this structure: `{ "name": str, "keywords": list[tuple[str, int]], "features": list[dict] }` where each feature entry has `{ "name": str, "description": str, "category": str, "priority": str, "always_separate": bool, "data_keywords": list[str] }`. The `keywords` field contains `(keyword, weight)` tuples with weight 1–3. The `category` field is one of: "foundation", "core", "supporting", "integration", "admin". The `data_keywords` field lists entity/data keywords used for affinity scoring (FR-050).

#### Feature-to-Service Mapping (Microservice / Modular Monolith)

- **FR-011**: For Microservice and Modular Monolith architectures, the system MUST group features into services using domain-driven design principles, producing fewer services than features.
- **FR-012**: Each service grouping MUST include a rationale statement (WHY COMBINED or WHY SEPARATE) explaining the design decision.
- **FR-013**: The mapping MUST apply these combining rules: features that share a bounded context, access the same data frequently, would require distributed transactions if split, or change together.
- **FR-014**: The mapping MUST apply these separation rules: features with independent scaling needs, different failure modes, different external dependencies, independent deployment frequencies.
- **FR-015**: Identity/Auth, Notification, External Integration, and Frontend MUST always be separate services regardless of other rules.
- **FR-050**: The service mapping algorithm MUST execute in this order: (1) Apply `always_separate` rules from FR-015 — these features become singleton services immediately. (2) For remaining features, compute pairwise affinity scores using: same `category` = +3, shared `data_keywords` = +2, different scaling profile = −2, different failure mode = −2. Scaling profile is derived from category: `{"foundation": "low", "core": "medium", "supporting": "medium", "integration": "high-variance", "admin": "low"}`. Failure mode is derived from category: `{"foundation": "infrastructure", "core": "business-logic", "supporting": "business-logic", "integration": "external-dependency", "admin": "operational"}`. (3) Greedily merge feature pairs with affinity score ≥ 3 into the same service, highest score first. (4) Features with no merge partner (affinity < 3 with all others) become singleton services. (5) Validate: no service exceeds 4 features; if exceeded, split the lowest-affinity feature into its own service. (6) Generate WHY COMBINED / WHY SEPARATE rationale for each service using the dominant affinity/separation factor.
- **FR-016**: For Microservice architecture with 5 or fewer features, the system MUST warn the user that microservices may be over-engineering and suggest Modular Monolith, while still respecting the user's final decision.

#### Interactive Review and Editing

- **FR-017**: After mapping is generated, the system MUST present the full mapping for user review before finalizing.
- **FR-057**: The interactive review MUST display the service mapping as a numbered Rich table (columns: #, Service Name, Features, Rationale). Users interact via typed commands: `combine <service1> <service2>` to merge services by name, `split <service> <feature_id>` to move a feature to a new service, `rename <service> <new-name>`, `add <service-name>`, `remove <service>` (prompts user to reassign each feature), `override <service> <target> <pattern>` to change a communication pattern, `done` to confirm. Invalid commands display a help summary of available commands.
- **FR-018**: Users MUST be able to combine two services into one.
- **FR-019**: Users MUST be able to split a service into two, selecting which features move to the new service.
- **FR-020**: Users MUST be able to rename any service while preserving feature assignments.
- **FR-021**: Users MUST be able to add a new empty service or remove an existing service (reassigning its features).
- **FR-022**: The system MUST validate that each feature maps to exactly one service — if a feature appears in two services, it MUST report an error.
- **FR-023**: The system MUST detect circular dependencies between services and report them with a suggestion to break the cycle.
- **FR-041**: When a user edit (split/combine) creates a circular dependency, the system MUST immediately re-validate and report the cycle before allowing confirmation. The user MUST resolve all cycles before the mapping can be finalized.

#### Output and Persistence

- **FR-024**: The system MUST write a `manifest.json` file at `.specforge/manifest.json`. This is a single centralized file (NOT distributed per-service manifests). The complete schema is:

```json
{
  "schema_version": "1.0",
  "architecture": "monolithic | microservice | modular-monolith",
  "project_description": "string — original user input",
  "domain": "string — matched domain pattern name or 'generic'",
  "features": [
    {
      "id": "001",
      "name": "string",
      "description": "string",
      "priority": "P0 | P1 | P2 | P3",
      "category": "foundation | core | supporting | integration | admin",
      "service": "string — service/module slug this feature belongs to"
    }
  ],
  "services": [
    {
      "name": "string — service display name",
      "slug": "string — kebab-case directory name",
      "features": ["001", "003"],
      "rationale": "string — WHY COMBINED or WHY SEPARATE explanation",
      "communication": [
        {
          "target": "string — target service slug",
          "pattern": "sync-rest | sync-grpc | async-event",
          "required": true,
          "description": "string — purpose of this connection"
        }
      ]
    }
  ],
  "events": [
    {
      "name": "string — e.g., ledger.transaction.created",
      "producer": "string — service slug",
      "consumers": ["string — service slugs"],
      "payload_summary": "string — brief description of event data"
    }
  ]
}
```

- **FR-025**: The system MUST create one directory per service (for microservice) or per module (for monolith/modular-monolith) under `.specforge/features/`.
- **FR-056**: Feature/module directories MUST be named using the pattern `{id}-{name-slug}/` where `id` is the zero-padded feature ID and `name-slug` is the kebab-case feature name (e.g., `001-authentication/`, `002-transactions/`). This convention applies to all architecture types. For microservice, the service slug is used for the top-level grouping in the manifest, but the physical directories use feature-level naming.
- **FR-026**: The system MUST generate a dependency graph between services as a Mermaid diagram in `communication-map.md`.
- **FR-027**: For microservice architecture, the system MUST auto-assign communication patterns using these heuristic rules: (a) `always_separate` notification type → async event; (b) auth/identity service → sync REST (consumed by all other services); (c) services within the same bounded context that were split → sync gRPC (internal, low-latency); (d) services in different bounded contexts → sync REST (external-facing, standard); (e) services producing data consumed by analytics/reporting → async event. Users can override any assignment during interactive review.
- **FR-051**: Communication links MUST include a `required: bool` field. Required dependencies are rendered as solid arrows in the Mermaid diagram. Optional dependencies are rendered as dashed arrows.
- **FR-052**: Async event communication MUST be specified at the logical level only: event name, producer service, consumer service(s), and payload summary. Event names MUST follow the pattern `{producer}.{entity}.{action}` (e.g., `ledger.transaction.created`).
- **FR-028**: The system MUST persist state to disk after each completed step (architecture selection, feature decomposition, service mapping, user confirmation). All file writes MUST use atomic write-to-temp-then-rename to prevent corruption on crash: write to `{filename}.tmp`, then `os.replace()` to the final path.
- **FR-029**: When an existing `manifest.json` is detected, the system MUST ask whether to start fresh or modify the existing decomposition. Modification is a full manifest rewrite (not incremental patch) — the entire manifest is regenerated from the current in-memory state after edits.
- **FR-042**: `manifest.json` MUST include a `schema_version` field (starting at `"1.0"`) for forward compatibility. Migration logic is deferred until the schema actually changes.
- **FR-043**: Modular Monolith MUST use the same directory structure as Microservice (one directory per module under `.specforge/features/`) but the manifest MUST set `architecture: "modular-monolith"`. No separate deployment configuration is generated in v1 — the structural difference is in the manifest metadata only.
- **FR-053**: After writing `manifest.json`, the system MUST validate the written file by reading it back and checking: (a) valid JSON, (b) `schema_version` present, (c) `architecture` is one of the 3 valid values, (d) every feature has a unique ID, (e) every feature's `service` field references an existing service slug, (f) no feature appears in more than one service. Validation failure MUST be reported as an error.

#### Re-mapping

- **FR-030**: The system MUST support a `--remap <architecture>` flag that re-maps an existing feature set to a new architecture without deleting feature content.
- **FR-031**: When re-mapping, existing spec/plan/tasks files in feature directories MUST be preserved.
- **FR-032**: When re-mapping from microservice to monolith, service boundaries MUST be removed and features MUST become modules.

#### Monolithic-Specific

- **FR-033**: For Monolithic architecture, all features MUST be organized as modules within a single application — no service-level mapping is performed.
- **FR-034**: Each module in a monolithic architecture MUST still receive its own feature directory with spec/plan/tasks pipeline support.

#### Integration with Existing Features

- **FR-044**: Feature 002 (Template Engine): the system MUST add two new Jinja2 templates — `manifest.json.j2` for manifest generation and `communication-map.md.j2` for the Mermaid dependency diagram. Templates go in `src/specforge/templates/base/features/`.
- **FR-045**: Feature 003 (Agent Prompts): governance prompt file content MUST NOT change based on architecture choice in v1. Architecture-aware governance is deferred to a future version. The architecture type is recorded in `manifest.json` for downstream features to consume.
- **FR-046**: The `--no-warn` flag MUST suppress the over-engineering warning (FR-016) for scripted/CI usage. The warning threshold is 5 or fewer features.

### Key Entities

- **Manifest**: The central project descriptor containing architecture type, feature list, service definitions, feature-to-service assignments, and communication patterns. Persisted as `manifest.json`.
- **Feature**: A discrete unit of application functionality with a numeric ID, name, description, and assignment to exactly one service or module.
- **Service**: A logical deployment unit (microservice/modular monolith) containing one or more features, with a name, rationale, and communication pattern declarations.
- **Module**: A logical organizational unit (monolithic) containing one or more features with enforced boundaries within a single deployable.
- **CommunicationLink**: A directed connection between two services specifying the interaction pattern (sync REST, sync gRPC, async event) and the purpose of the connection.
- **DecompositionState**: The persistent state of the multi-step decompose flow. Persisted at `.specforge/decompose-state.json` with the following structure:

```json
{
  "step": "architecture | decomposition | mapping | review | complete",
  "architecture": "monolithic | microservice | modular-monolith | null",
  "project_description": "string — original user input",
  "domain": "string | null — matched domain or null if not yet resolved",
  "features": [],
  "services": [],
  "timestamp": "ISO-8601 UTC of last update"
}
```

Each step writes the state atomically. On re-run, the system reads the state file and offers: (a) resume from last completed step, (b) start fresh. The state file is deleted on successful completion and final manifest write.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The entire decompose flow (architecture prompt → feature decomposition → service mapping → user confirmation) completes in under 30 seconds for local mode.
- **SC-002**: Feature decomposition produces 8–15 features for recognized domain descriptions, with feature names that match domain vocabulary (e.g., a finance app gets "Transactions", not "Data Entry Module").
- **SC-003**: Feature-to-service mapping produces 40–70% fewer services than features (e.g., 12 features → 7–9 services).
- **SC-004**: Decomposition is deterministic — the same input description with the same architecture choice produces identical feature lists across runs.
- **SC-005**: The `manifest.json` output is valid, well-structured, and parseable by all downstream SpecForge features.
- **SC-006**: Interrupted flows are resumable — state persists after each step, and re-running detects and offers to continue from the last completed step.
- **SC-007**: 100% of generated service groupings include a rationale statement (WHY COMBINED or WHY SEPARATE).
- **SC-008**: Re-mapping preserves all existing feature content — zero files deleted when switching architecture type.

## Clarifications

Resolved during specification review (2026-03-15):

| # | Question | Resolution |
|---|----------|------------|
| C-01 | Should the architecture question be asked every time? | **No.** First run: always ask (unless `--arch` flag given). Subsequent runs: detect existing manifest and ask resume/modify/start-fresh. `--remap` implies the target architecture. (FR-036) |
| C-02 | Should `--arch` flag skip the interactive prompt? | **Yes.** `--arch [monolithic\|microservice\|modular-monolith]` bypasses the prompt. Enables CI/CD and scripted usage. (FR-035) |
| C-03 | How does Modular Monolith differ from Microservice structurally? | **Same directory layout** (one dir per module). The difference is metadata only: `manifest.json` records `"modular-monolith"` vs `"microservice"`. No separate deployment config in v1. (FR-043) |
| C-04 | What happens on Ctrl+C during any step? | **Save completed state.** Whatever steps finished are persisted. Next run detects partial state and offers resume. (FR-037) |
| C-05 | How are mapping rules stored? | **Hard-coded Python dicts** in `core/domain_patterns.py` and `core/service_mapper.py`. Not configurable YAML/JSON in v1. (FR-040) |
| C-06 | How are WHY COMBINED/WHY SEPARATE rationales generated? | **Rule-based string templates.** No LLM dependency. Deterministic. Example: "Combined: shared bounded context — {a} and {b} access the same data." (FR-040) |
| C-07 | Should edits trigger dependency re-validation? | **Yes, immediately.** Every edit (split/combine) re-validates. Circular dependencies must be resolved before confirmation. (FR-041) |
| C-08 | Should communication patterns be auto-assigned or asked? | **Auto-assigned via heuristic rules** (notification → async, auth → sync REST, internal data → gRPC). Users can override during interactive review. (FR-027) |
| C-09 | How many domain patterns in v1? | **6 domains**: finance, e-commerce, SaaS, social, healthcare, education. Stored as Python dicts. (FR-038) |
| C-10 | What's the fallback for unknown domains? | **Generic patterns** (Auth, CRUD, Admin, Reporting, Notifications) + present list for user editing. (FR-007) |
| C-11 | Are domain patterns combinable? | **No, not in v1.** Pick best single match via keyword scoring. Combination deferred. (FR-039) |
| C-12 | Centralized or distributed manifest? | **Single centralized `manifest.json`** with full feature→service mapping. No per-service manifests. (FR-024) |
| C-13 | How to handle optional dependencies in the graph? | Communication links include a `required: bool` field. Optional links are rendered as dashed lines in the Mermaid diagram. |
| C-14 | Should manifest.json be versioned? | **Yes.** `schema_version: "1.0"` field. Migration logic deferred until schema changes. (FR-042) |
| C-15 | What's the over-engineering warning threshold? | **≤5 features** triggers the warning. Suppressible with `--no-warn`. (FR-016, FR-046) |
| C-16 | Which Feature 002 templates to add? | `manifest.json.j2` and `communication-map.md.j2` in `templates/base/features/`. (FR-044) |
| C-17 | Should governance prompts vary by architecture? | **No, not in v1.** Architecture type is in `manifest.json` for future use. (FR-045) |
| C-18 | What naming convention for feature/module directories? | **ID + name slug** format: `001-authentication/`, `002-transactions/`. Provides sort order and readability. Same convention for all architecture types. (FR-056) |
| C-19 | What CLI mechanism for interactive mapping review/edit? | **Numbered Rich table + typed commands.** Display mapping as Rich table with row numbers. User types commands: `combine 1 2`, `split 3`, `rename 4 NewName`, `add ServiceName`, `remove 5`, `done` to confirm. Invalid commands show help. (FR-057) |
| C-20 | What clarification questions are asked for vague input? | **5 generic question templates** stored in `domain_patterns.py`: (1) "What domain/industry?" (2) "Who are the primary users?" (3) "What is the core action users perform?" (4) "Expected scale?" (5) "Any external integrations?". Answers are concatenated with original description for re-scoring. (FR-058) |

## Assumptions

- The decompose command operates locally without requiring network access or external AI APIs. Feature decomposition uses built-in domain knowledge patterns (pattern dictionaries for common app domains like finance, e-commerce, healthcare, etc.).
- The `manifest.json` schema will be the contract consumed by all downstream features (005–013). Its structure is defined by this feature and must remain backward-compatible.
- Communication pattern assignment (REST vs gRPC vs async) uses heuristic rules based on service characteristics (e.g., notification services default to async, auth services default to sync). Users can override during interactive review.
- The clarification mode (for vague descriptions) uses pre-defined question templates, not generative AI.
- Domain pattern dictionaries are extensible — new domains can be added without modifying core logic.

## Out of Scope

The following are explicitly **NOT** part of this feature:

- **LLM/AI-powered decomposition** — All feature identification and service mapping uses deterministic, rule-based logic. No external AI API calls.
- **Deployment configuration generation** — The feature produces a logical architecture map, not Dockerfiles, Kubernetes manifests, or CI/CD pipelines.
- **Code generation** — No application source code is generated. Output is limited to manifest, directory structure, and documentation.
- **Domain pattern combination** — Multi-domain matching (e.g., "social finance app") is deferred to a future version.
- **Configurable mapping rules** — Combining/separation rules are hard-coded Python in v1. YAML/JSON configuration is deferred.
- **Architecture-aware governance prompts** — Feature 003 prompts do not vary by architecture choice in v1.
- **Distributed manifest files** — No per-service `service-manifest.json`. Single centralized `manifest.json` only.
- **Remote/cloud decomposition** — The entire flow is local and offline.

## New Python Modules

This feature introduces the following new modules:

| Module | Location | Responsibility |
|--------|----------|----------------|
| `domain_analyzer.py` | `src/specforge/core/` | Domain pattern matching, keyword scoring, feature generation from domain patterns |
| `service_mapper.py` | `src/specforge/core/` | Feature-to-service mapping, affinity scoring, combining/separation rules, rationale generation |
| `manifest_writer.py` | `src/specforge/core/` | Manifest JSON generation, atomic file write, post-write validation |
| `decomposition_state.py` | `src/specforge/core/` | DecompositionState persistence — save/load/resume partial state |
| `communication_planner.py` | `src/specforge/core/` | Auto-assign communication patterns between services, generate Mermaid diagram |
| `domain_patterns.py` | `src/specforge/core/` | Hard-coded domain pattern dictionaries (finance, e-commerce, SaaS, social, healthcare, education, generic) |
| `decompose_cmd.py` | `src/specforge/cli/` | **Modified** (existing placeholder) — full implementation of the `specforge decompose` command |

### decompose_cmd.py Modifications

The existing placeholder in `src/specforge/cli/decompose_cmd.py` will be replaced with:

1. Click command with new options: `--arch [monolithic|microservice|modular-monolith]`, `--remap <architecture>`, `--no-warn`
2. Multi-step interactive flow orchestration: architecture → decompose → map → review → confirm
3. Rich console output for architecture selection, feature tables, service mapping display
4. DecompositionState save/resume logic at each step boundary
5. Integration with `DomainAnalyzer`, `ServiceMapper`, `CommunicationPlanner`, `ManifestWriter`

### Backward Compatibility

- **FR-054**: All existing CLI commands (`init`, `check`, `validate-prompts`) MUST continue to work unchanged. The `decompose` command signature changes (new options added) but retains its existing positional `description` argument.
- **FR-055**: No existing modules in `core/`, `cli/`, or `templates/` are modified except `decompose_cmd.py` and `config.py` (new constants). Feature 002's `TemplateRegistry` gains new template entries but no API changes.

## Testing Requirements

### Unit Tests

- **UT-001**: `DomainAnalyzer` — test all 6 domain patterns produce 8–15 features with correct names and categories.
- **UT-002**: `DomainAnalyzer` — test generic fallback for unrecognized domain descriptions.
- **UT-003**: `DomainAnalyzer` — test keyword scoring: vague input (score < 2) triggers clarification, recognized input (score ≥ 2) proceeds.
- **UT-004**: `ServiceMapper` — test affinity scoring: features with shared category get +3, shared data keywords +2, etc.
- **UT-005**: `ServiceMapper` — test `always_separate` rules: auth, notification, integration always become standalone.
- **UT-006**: `ServiceMapper` — test greedy merge: features with affinity ≥ 3 are combined; affinity < 3 become singletons.
- **UT-007**: `ServiceMapper` — test max 4 features per service cap: 5th feature splits out.
- **UT-008**: `ServiceMapper` — test rationale generation: every service gets WHY COMBINED or WHY SEPARATE.
- **UT-009**: `CommunicationPlanner` — test heuristic pattern assignment for all 5 rules (notification→async, auth→REST, etc.).
- **UT-010**: `ManifestWriter` — test atomic write (temp + rename).
- **UT-011**: `ManifestWriter` — test post-write validation catches: invalid JSON, missing schema_version, duplicate feature ID, cross-reference errors.
- **UT-012**: `DecompositionState` — test save/load round-trip for each step.
- **UT-013**: `DecompositionState` — test resume detection when partial state file exists.
- **UT-014**: Feature priority assignment: P0 for foundation, P1 for core, P2 for supporting, P3 for optional.

### Integration Tests

- **IT-001**: Full decompose flow end-to-end: `specforge decompose --arch microservice "finance app"` → verify manifest.json, feature directories, communication-map.md all created and valid.
- **IT-002**: Full monolithic flow: `--arch monolithic` → verify no service mapping, all features as modules.
- **IT-003**: Re-map flow: decompose as monolith, then `--remap microservice` → verify features preserved, services added.
- **IT-004**: Over-engineering warning: decompose a 3-feature app with `--arch microservice` → verify warning printed.
- **IT-005**: `--no-warn` suppresses the warning from IT-004.

### Snapshot Tests

- **ST-001**: Golden file for `manifest.json` output given "PersonalFinance" + microservice → exact JSON match.
- **ST-002**: Golden file for `communication-map.md` Mermaid diagram output.
- **ST-003**: Golden file for `manifest.json` output given monolithic architecture.

### Edge Case Tests

- **EC-001**: Gibberish input → helpful error message, not a crash.
- **EC-002**: >15 features generated → consolidation warning.
- **EC-003**: Circular dependency after user edit → detected and reported.
- **EC-004**: Same feature in two services → validation error.
- **EC-005**: Empty description string → error with example prompts.
