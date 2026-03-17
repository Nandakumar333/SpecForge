# Feature Specification: Research & Clarification Engine

**Feature Branch**: `006-research-clarification-engine`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "Build the research and clarification engine that resolves unknowns in service specs BEFORE planning begins."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clarify Service-Specific Ambiguities (Priority: P1)

As a developer, I want to run `specforge clarify <service>` to automatically detect ambiguities in a service's spec.md and receive structured clarification questions, so that I can resolve unknowns before planning begins and avoid building on unclear requirements.

The clarification engine scans spec.md for patterns that indicate ambiguity: vague terms ("as needed", "appropriate", "etc."), undefined domain concepts, unspecified technical choices, and missing boundary definitions. It groups detected ambiguities into categories (domain, technical, service-boundary, communication) and generates targeted questions with suggested answer options.

For multi-feature services (e.g., ledger-service covering accounts and transactions), the engine detects ambiguities across all feature areas and includes cross-feature concerns such as shared concepts that may belong to either service.

Answers are recorded in a "Clarifications" section appended to spec.md. Running clarify again on the same service detects NEW ambiguities (including any introduced by previous answers) and appends additional Q&A entries without replacing existing ones.

**Why this priority**: Clarification is the primary user-facing interaction. Without it, specs proceed to planning with unresolved ambiguities, leading to rework and incorrect implementations.

**Independent Test**: Can be fully tested by running `specforge clarify ledger-service` against a spec.md containing known ambiguities and verifying that categorized questions are generated and answers are recorded back into spec.md.

**Acceptance Scenarios**:

1. **Given** ledger-service spec.md contains "transactions should be processed appropriately", **When** I run `specforge clarify ledger-service`, **Then** a domain ambiguity question is generated asking what "processed appropriately" means (real-time vs batch, validation rules, etc.).
2. **Given** ledger-service spec.md covers accounts AND transactions features, **When** I run `specforge clarify ledger-service`, **Then** questions include both account-specific gaps (e.g., account types) and transaction-specific gaps (e.g., transaction limits).
3. **Given** ledger-service and planning-service both reference "categories", **When** I run clarify on ledger-service, **Then** a service-boundary question asks whether category management should live in ledger-service or planning-service.
4. **Given** spec.md already has a Clarifications section from a previous run, **When** I run clarify again, **Then** new questions are appended below existing entries and existing answers are preserved.
5. **Given** spec.md has no detectable ambiguities, **When** I run clarify, **Then** the system reports "No ambiguities detected" and makes no changes to spec.md.

---

### User Story 2 - Research Technical Unknowns (Priority: P1)

As a developer, I want to run `specforge research <service>` to scan spec.md and plan.md for technical unknowns and produce a research.md with findings, so that planning decisions are informed by verified technical information rather than assumptions.

The research engine scans spec.md and plan.md for markers tagged "NEEDS CLARIFICATION" as well as technical references that warrant verification (library names, protocol mentions, integration patterns). For each unknown, it generates targeted research queries and produces research.md with structured findings. Each finding includes the topic, a summary, the source of information, and a status: RESOLVED (confirmed and verified), UNVERIFIED (found but not independently confirmed), or BLOCKED (unable to determine, requires human input).

For microservice architectures, research automatically includes service communication pattern analysis, container base image recommendations, and message broker comparisons relevant to the service's declared communication patterns from manifest.json.

**Why this priority**: Research directly feeds into plan generation (Phase 4). Without verified technical findings, plans contain assumptions that may be incorrect, leading to implementation failures.

**Independent Test**: Can be fully tested by running `specforge research ledger-service` against a spec.md mentioning "gRPC for auth validation" and verifying research.md contains gRPC library information, setup steps, and compatibility notes.

**Acceptance Scenarios**:

1. **Given** spec.md for ledger-service mentions "gRPC for auth validation", **When** research.md is generated, **Then** it includes gRPC library version, setup requirements, proto file conventions, and performance characteristics, each with a status (RESOLVED/UNVERIFIED/BLOCKED).
2. **Given** spec.md contains a "NEEDS CLARIFICATION" marker about database choice, **When** research.md is generated, **Then** it includes a finding addressing that specific unknown with comparison data.
3. **Given** architecture=microservice in manifest.json, **When** research.md is generated for ledger-service, **Then** it includes findings on: communication patterns used by the service, recommended container base images, and message broker comparison if async communication is declared.
4. **Given** architecture=monolithic, **When** research.md is generated, **Then** it omits microservice-specific research (container images, service mesh, message brokers) and focuses on module-level technical unknowns.
5. **Given** research.md already exists and new unknowns are introduced via spec updates, **When** research is re-run, **Then** existing RESOLVED findings are preserved and only new or BLOCKED findings are re-researched.

---

### User Story 3 - Detect Architecture-Change Ambiguities (Priority: P2)

As a developer who has changed architecture from monolith to microservice (via `--remap`), I want the clarification engine to identify NEW ambiguities that arise specifically from the architecture change, so that I address distributed-systems concerns that were irrelevant in the original monolith.

When clarifying a service after an architecture remap, the engine compares the current architecture type against the service's feature origins. If features were originally designed for a monolith and now belong to a microservice, the engine generates additional questions about: service boundaries, communication patterns, data ownership, shared state management, and eventual consistency requirements.

**Why this priority**: Architecture changes are the highest-risk scenario for undetected ambiguities. Questions that were irrelevant in a monolith (e.g., "which service owns this data?") become critical in microservice mode. Catching these early prevents costly redesigns.

**Independent Test**: Can be tested by running `specforge decompose --remap microservice` on a monolith project and then running `specforge clarify <service>` to verify architecture-change-specific questions appear.

**Acceptance Scenarios**:

1. **Given** a project was originally monolithic and has been remapped to microservice, **When** I run clarify on any service, **Then** questions include service-boundary ownership, communication pattern choices (sync vs async), data ownership boundaries, and shared state handling.
2. **Given** a project has always been microservice architecture, **When** I run clarify, **Then** architecture-change-specific questions are NOT generated (only standard ambiguity detection applies).
3. **Given** a remap from monolith to microservice where the original monolith had a shared "categories" table, **When** I run clarify on ledger-service, **Then** a question asks about data ownership: "Should the categories table be owned by ledger-service, planning-service, or extracted into its own service?"

---

### User Story 4 - Interactive Clarification Flow (Priority: P2)

As a developer, I want the clarification engine to present questions interactively with suggested answers, so that I can quickly resolve ambiguities by selecting from options or providing custom answers rather than writing responses from scratch.

Each clarification question is presented with context (the relevant spec excerpt), the specific question, and 2-4 suggested answer options with their implications. The developer selects an option or provides a custom answer. The engine records the answer in spec.md's Clarifications section and continues to the next question. The developer can skip questions to address them later.

**Why this priority**: Interactive flow with suggestions dramatically reduces the time to resolve ambiguities. Without it, developers must research each question independently, defeating the purpose of automated detection.

**Independent Test**: Can be tested by running clarify in interactive mode, selecting suggested answers for some questions, skipping others, and verifying spec.md reflects only the answered questions.

**Acceptance Scenarios**:

1. **Given** clarify detects 5 ambiguities, **When** the interactive flow begins, **Then** each question shows the relevant spec excerpt, the question, and 2-4 suggested answers with implications.
2. **Given** I select option B for a question, **When** the answer is recorded, **Then** spec.md's Clarifications section contains the question, my selected answer, and its implications.
3. **Given** I skip a question during interactive flow, **When** the session completes, **Then** skipped questions are NOT recorded in spec.md and will reappear on the next clarify run.
4. **Given** I provide a custom answer instead of selecting a suggestion, **When** the answer is recorded, **Then** spec.md contains my custom text as the answer.

---

### User Story 5 - Non-Interactive Clarification Mode (Priority: P3)

As a developer, I want to run `specforge clarify <service> --report` to generate a report of all detected ambiguities without entering interactive mode, so that I can review questions offline or share them with team members for discussion before answering.

The report mode produces a structured list of all detected ambiguities with their categories, context, and suggested answers, written to a `clarifications-report.md` file in the service's feature directory. No changes are made to spec.md.

**Why this priority**: Not all ambiguities can be resolved by a single developer. Some require team discussion. A shareable report enables asynchronous collaboration on spec refinement.

**Independent Test**: Can be tested by running clarify with --report flag and verifying a report file is created while spec.md remains unchanged.

**Acceptance Scenarios**:

1. **Given** spec.md contains ambiguities, **When** I run `specforge clarify ledger-service --report`, **Then** `clarifications-report.md` is created in the service's feature directory with all questions, categories, and suggested answers.
2. **Given** I run clarify with --report, **When** the report is generated, **Then** spec.md is NOT modified.

---

### Edge Cases

- What happens when spec.md does not exist for the target service?
- What happens when plan.md does not exist when running research (Phase 2 depends on Phase 1 only)?
- What happens when clarify is run on a service with zero features mapped?
- What happens when the same ambiguity is detected across multiple features within one service?
- What happens when a clarification answer introduces a NEW ambiguity?
- What happens when research findings contradict information in spec.md?
- What happens when the service's manifest entry has no communication patterns declared?
- What happens when clarify is run concurrently with the spec generation pipeline?
- What happens when spec.md is manually edited between clarify runs (existing Clarifications section format is altered)?
- What happens when the manifest declares a dependency on a service that doesn't exist yet?
- What happens when architecture type in manifest changes between research runs?

## Requirements *(mandatory)*

### Functional Requirements

**Clarification Engine**

- **FR-001**: System MUST scan spec.md for ambiguity patterns including vague terms, undefined domain concepts, unspecified technical choices, and missing boundary definitions
- **FR-002**: System MUST categorize detected ambiguities into: domain, technical, service-boundary, and communication
- **FR-003**: System MUST generate structured questions for each detected ambiguity with 2-4 suggested answer options and their implications
- **FR-004**: System MUST detect intra-service cross-feature ambiguities for multi-feature services (e.g., shared concepts between accounts and transactions within ledger-service)
- **FR-005**: System MUST detect inter-service cross-boundary ambiguities when a concept is referenced by multiple services (e.g., "categories" used by both ledger and planning services) and present ownership options for the user to choose from, without auto-moving features between services
- **FR-006**: System MUST record answers in a "Clarifications" section appended to spec.md
- **FR-007**: System MUST preserve existing Clarifications entries on subsequent runs (append-only, never replace)
- **FR-008**: System MUST support interactive mode (default) where questions are presented one at a time with selectable options
- **FR-009**: System MUST support report mode (`--report`) that writes all questions to `clarifications-report.md` without modifying spec.md
- **FR-010**: System MUST allow skipping questions during interactive mode; skipped questions reappear on the next run
- **FR-011**: System MUST report "No ambiguities detected" when no patterns match, making no changes to spec.md

**Architecture-Change Detection**

- **FR-012**: System MUST detect when a project has undergone architecture remap (monolith to microservice or vice versa) by reading manifest.json metadata
- **FR-013**: System MUST generate additional architecture-change-specific questions covering: service boundaries, communication patterns, data ownership, shared state, and eventual consistency
- **FR-014**: System MUST NOT generate architecture-change questions when the project has always used the same architecture type
- **FR-014a**: System MUST mark existing architecture-related clarifications (service-boundary, communication, data-ownership categories) as requiring re-validation after a remap, while preserving domain-level clarifications unchanged

**Research Engine**

- **FR-015**: System MUST scan spec.md for "NEEDS CLARIFICATION" markers and technical references requiring verification
- **FR-016**: System MUST scan plan.md for technical unknowns when plan.md exists (plan.md is optional input; spec.md is required)
- **FR-017**: System MUST produce research.md with structured findings containing: topic, summary, source, and status (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING, where CONFLICTING indicates multiple sources disagree and lists the alternatives for user decision)
- **FR-018**: System MUST include microservice-specific research (communication patterns, container base images, message broker comparisons) when architecture is microservice, scoped to container-level concerns (Docker, health checks) and excluding orchestration-level concerns (Kubernetes, service mesh configuration)
- **FR-019**: System MUST omit microservice-specific research topics when architecture is monolithic
- **FR-020**: System MUST preserve existing RESOLVED findings when research is re-run, only re-researching new or BLOCKED findings
- **FR-021**: System MUST identify library and framework references in spec.md and plan.md and generate findings with version and compatibility information based on embedded knowledge; findings MUST use UNVERIFIED status when version information cannot be confirmed without external network access

**Integration with Existing Pipeline**

- **FR-022**: System MUST read manifest.json to resolve service metadata, feature mappings, architecture type, and communication patterns
- **FR-023**: System MUST operate within the existing pipeline directory structure (`.specforge/features/<service-slug>/`)
- **FR-024**: System MUST respect the existing pipeline state tracking (`.pipeline-state.json`) for the research phase
- **FR-025**: System MUST use Jinja2 templates (via TemplateRegistry from Feature 002) for rendering research.md and clarifications-report.md
- **FR-026**: System MUST validate that spec.md exists before running either clarify or research commands

**CLI Commands**

- **FR-027**: System MUST provide `specforge clarify <service>` command accepting a service slug or feature number
- **FR-028**: System MUST provide `specforge research <service>` command accepting a service slug or feature number
- **FR-029**: System MUST resolve feature numbers to owning services via manifest.json lookup (consistent with Feature 005 behavior)
- **FR-030**: System MUST display progress information during research and clarification using Rich terminal output

### Key Entities

- **AmbiguityPattern**: A regex or heuristic rule used to detect ambiguities in spec text. Contains pattern type (vague-term, undefined-concept, missing-boundary), the matching regex or keyword list, and the ambiguity category (domain, technical, service-boundary, communication).
- **ClarificationQuestion**: A structured question generated from a detected ambiguity. Contains the source text excerpt, category, question text, 2-4 suggested answers with implications, and answer status (unanswered, answered, skipped).
- **ClarificationSession**: Tracks state for one clarify run. Contains the target service, list of ClarificationQuestions, answers provided, and whether the session is interactive or report-only.
- **ResearchFinding**: A single research result. Contains topic, summary text, source reference, status (RESOLVED/UNVERIFIED/BLOCKED/CONFLICTING), and the originating spec marker or reference. CONFLICTING status includes a list of alternative findings with their respective sources.
- **ResearchContext**: Aggregated context for research generation. Contains the service's architecture type, communication patterns, referenced libraries and technologies, and all "NEEDS CLARIFICATION" markers extracted from spec.md and plan.md.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can identify and resolve all spec ambiguities for a typical service in under 10 minutes using the interactive clarification flow
- **SC-002**: Clarification engine detects at least 80% of ambiguities that would otherwise surface during implementation (measured by comparing pre-clarify specs against post-implementation change requests)
- **SC-003**: Research output covers all technical unknowns referenced in spec.md, with zero unaddressed "NEEDS CLARIFICATION" markers remaining
- **SC-004**: Running clarify twice on the same unchanged spec produces zero duplicate questions on the second run
- **SC-005**: Architecture-remap scenario generates at least 3 additional service-boundary questions per service compared to a native-architecture clarify run
- **SC-006**: Research.md for microservice architectures contains findings for all declared communication patterns (e.g., if gRPC is declared, gRPC-specific findings exist)
- **SC-007**: 100% of clarification answers are correctly persisted in spec.md and survive subsequent clarify runs without data loss

## Clarifications

### Session 2026-03-16

- Q: Should the research engine call external APIs (npm, NuGet, PyPI) to verify library versions? → A: No external API calls; use embedded knowledge only with UNVERIFIED status when version info cannot be confirmed locally
- Q: Should service-boundary clarifications suggest moving features between services, or only flag the ambiguity? → A: Flag with ownership options only; never auto-move features between services
- Q: How should research.md handle conflicting information from different sources? → A: Present all conflicting findings with a new CONFLICTING status, listing alternatives for user decision
- Q: When architecture changes via --remap, should ALL previous clarifications be invalidated? → A: Invalidate only architecture-related clarifications (service-boundary, communication, data-ownership); preserve domain-level clarifications unchanged
- Q: How deep should microservice-specific research go? → A: Container-level only (Docker, base images, health checks); orchestration (Kubernetes, service mesh) is out of scope

## Assumptions

- spec.md has already been generated by the spec generation pipeline (Feature 005, Phase 1) before clarify or research is run
- manifest.json has been generated by Feature 004's `specforge decompose` command
- The Jinja2 template engine (Feature 002) and TemplateRegistry are available for rendering research.md and report files
- Ambiguity pattern detection uses heuristic pattern matching (regex + keyword lists), not machine learning or LLM analysis
- The clarification engine operates on the text content of spec.md; it does not parse or understand code
- Research findings are generated from analysis of the spec content and manifest metadata; the engine does not make external network calls (findings use embedded knowledge with UNVERIFIED status when version accuracy cannot be guaranteed)
- Microservice research is scoped to container-level concerns (Docker, base images, health checks); orchestration (Kubernetes, Helm, service mesh) is explicitly out of scope
- The "Clarifications" section in spec.md follows a consistent Markdown format that the engine can parse and append to
- Architecture remap history is detectable from manifest.json metadata (e.g., a `previous_architecture` or `remapped_from` field)
- Interactive mode uses Rich prompts for terminal interaction (consistent with Feature 004's interactive prompts)
- Pipeline lock (`.pipeline-lock`) is checked before modifying spec.md to avoid conflicts with concurrent pipeline runs
