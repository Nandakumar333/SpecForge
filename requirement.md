# SpecForge — Requirements Document

> **AI-Powered Spec-Driven Development Engine**
> *From One Prompt to Production-Ready Features*
>
> Version 1.0 — March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [System Architecture Requirements](#4-system-architecture-requirements)
5. [Agent Instruction Prompt File Requirements](#5-agent-instruction-prompt-file-requirements)
6. [Feature Decomposition Requirements](#6-feature-decomposition-requirements)
7. [Per-Feature Spec Pipeline Requirements](#7-per-feature-spec-pipeline-requirements)
8. [Sub-Agent Execution Requirements](#8-sub-agent-execution-requirements)
9. [CLI Commands Requirements](#9-cli-commands-requirements)
10. [Edge Case Handling Requirements](#10-edge-case-handling-requirements)
11. [Development Roadmap Phases](#11-development-roadmap-phases)

---

## 1. Overview

### 1.1 Purpose

SpecForge is an AI-powered development engine that takes a single natural-language prompt and produces a fully decomposed, spec-driven, production-ready web application. It extends the philosophy of GitHub's Spec Kit — where specifications are the primary artifact — but adds automatic feature decomposition, per-feature sub-agent execution, and strict code quality enforcement through agent instruction prompts.

### 1.2 Core Concept

> **"Create a webapp for PersonalFinance"** → SpecForge auto-decomposes this into 12+ features, generates spec/plan/research/datamodel/checklist/tasks for each, and implements each feature independently using sub-agents governed by strict architecture, backend, frontend, database, security, testing, and CI/CD prompt files.

### 1.3 Key Differentiators

| # | Differentiator | Description |
|---|----------------|-------------|
| D-1 | **Automatic Feature Decomposition** | Takes a one-line app description and intelligently splits it into bounded features (Spec Kit requires manual feature definition). |
| D-2 | **Independent Sub-Agent Execution** | Each feature runs as an isolated sub-agent with its own context, allowing parallel implementation without context pollution. |
| D-3 | **Agent Instruction Prompts** | Opinionated, strict coding-standard prompt files (backend, frontend, etc.) that enforce SOLID principles, design patterns, function length limits, layer separation, and more. |
| D-4 | **No Industry Standard Bias** | Does NOT follow default industry conventions unless explicitly instructed. Prevents AI agents from making assumptions about architecture, patterns, or libraries. |
| D-5 | **Edge Case First** | Designed to identify and fix edge cases before implementation, not after. Every spec phase includes edge-case analysis as a first-class artifact. |

---

## 2. Functional Requirements

### 2.1 Core Pipeline

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-001 | The system SHALL accept a single natural-language prompt describing a web application. | P0 |
| FR-002 | The system SHALL analyze the prompt to understand the domain, identify bounded contexts, and extract features via an App Analyzer Agent. | P0 |
| FR-003 | The system SHALL decompose the application into 10–15 independent feature modules via a Feature Decomposer. | P0 |
| FR-004 | The system SHALL generate a 7-phase spec pipeline for each feature: spec → research → datamodel → plan → checklist → edge-cases → tasks. | P0 |
| FR-005 | The system SHALL implement each feature via isolated sub-agents with strict prompt governance. | P0 |
| FR-006 | The system SHALL merge features, resolve cross-cutting concerns, and run integration tests via an Integration Orchestrator. | P0 |
| FR-007 | The system SHALL enforce automated quality gates: test-fix loops, security scan, lint, and build validation. | P0 |

### 2.2 Project Initialization

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-008 | The system SHALL scaffold a project with the `.specforge/` directory structure, prompt files, templates, and agent configuration. | P0 |
| FR-009 | The system SHALL support interactive `constitution.md` creation with domain-aware defaults. | P0 |
| FR-010 | The system SHALL auto-increment feature numbers, create git branches, and scaffold feature directories. | P1 |

### 2.3 Clarification & Analysis

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-011 | The system SHALL enter an interactive clarification loop (3–5 targeted questions) when the prompt is ambiguous. | P1 |
| FR-012 | The system SHALL provide cross-artifact consistency checking via an analyze command. | P1 |
| FR-013 | The system SHALL auto-resolve "NEEDS CLARIFICATION" items by searching docs, checking versions, and evaluating libraries. | P1 |

### 2.4 Implementation & Integration

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-014 | The system SHALL execute sub-agents in isolated contexts, loading only governance files + feature-specific artifacts. | P0 |
| FR-015 | The system SHALL support parallel execution of features without dependencies. | P1 |
| FR-016 | The system SHALL support task-level parallelism within features (tasks marked with `[P]`). | P1 |
| FR-017 | The system SHALL auto-create PRs per feature with spec summary, checklist status, and test results. | P2 |

### 2.5 Progress & Monitoring

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-018 | The system SHALL provide a real-time progress dashboard showing feature status: specifying → planning → implementing → testing → complete. | P1 |
| FR-019 | The system SHALL generate a status report for all features on demand. | P1 |

---

## 3. Non-Functional Requirements

### 3.1 Tech Stack Agnosticism

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-001 | The system SHALL ship with .NET defaults for prompt files. | P0 |
| NFR-002 | The system SHALL support pluggable tech stack prompt files: .NET, Node.js, Python, Go, Java. | P1 |
| NFR-003 | The system SHALL support pluggable frontend frameworks: React, Vue, Svelte, Angular. | P1 |
| NFR-004 | The system SHALL auto-adapt prompt file rules to the target stack (e.g., FluentValidation → Pydantic, EF Core → SQLAlchemy). | P2 |

### 3.2 Multi-Agent Compatibility

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-005 | The system SHALL support multiple AI agents: Claude Code, Copilot, Gemini CLI, Cursor, Windsurf, Codex. | P1 |

### 3.3 Extensibility

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-006 | The system SHALL support brownfield mode: analyze existing codebases, generate specs from code, add features incrementally. | P2 |
| NFR-007 | The system SHALL support custom prompt authoring via UI/CLI for teams. | P2 |

### 3.4 IDE Integration

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-008 | The system SHALL provide a VS Code extension with sidebar showing feature tree, spec status, and one-click artifact navigation. | P2 |

---

## 4. System Architecture Requirements

### 4.1 High-Level Pipeline

The system SHALL implement the following 7-stage pipeline:

| Stage | Name | Description |
|-------|------|-------------|
| 1 | User Prompt | Accept a single natural-language app description. |
| 2 | App Analyzer Agent | Understand domain, identify bounded contexts, extract features. |
| 3 | Feature Decomposer | Split app into 10–15 independent feature modules. |
| 4 | Per-Feature Spec Pipeline | Generate: spec → research → datamodel → plan → checklist → edge-cases → tasks. |
| 5 | Sub-Agent Executor | Implement each feature via isolated sub-agent with strict prompt governance. |
| 6 | Integration Orchestrator | Merge features, resolve cross-cutting concerns, run integration tests. |
| 7 | Quality Gate | Automated test-fix loops, security scan, lint, build validation. |

### 4.2 Directory Structure

The system SHALL generate the following project structure:

```
project-root/
├── .specforge/
│   ├── constitution.md                    # Project-wide principles
│   ├── memory/
│   │   ├── constitution.md                # Governance rules
│   │   └── decisions.md                   # Architecture Decision Records
│   ├── prompts/                           # Agent instruction files
│   │   ├── architecture.prompts.md
│   │   ├── backend.prompts.md
│   │   ├── frontend.prompts.md
│   │   ├── database.prompts.md
│   │   ├── security.prompts.md
│   │   ├── testing.prompts.md
│   │   ├── cicd.prompts.md
│   │   └── api-design.prompts.md
│   ├── features/
│   │   ├── 001-<feature-name>/
│   │   │   ├── spec.md
│   │   │   ├── research.md
│   │   │   ├── data-model.md
│   │   │   ├── plan.md
│   │   │   ├── checklist.md
│   │   │   ├── tasks.md
│   │   │   ├── edge-cases.md
│   │   │   └── contracts/
│   │   │       └── api-spec.json
│   │   └── ... (all features)
│   ├── templates/
│   │   ├── spec-template.md
│   │   ├── plan-template.md
│   │   ├── tasks-template.md
│   │   ├── checklist-template.md
│   │   ├── research-template.md
│   │   ├── datamodel-template.md
│   │   └── edge-cases-template.md
│   └── scripts/
│       ├── decompose.sh
│       ├── generate-feature.sh
│       └── run-sub-agent.sh
├── src/
│   ├── backend/
│   ├── frontend/
│   └── shared/
└── tests/
```

---

## 5. Agent Instruction Prompt File Requirements

These prompt files serve as **hard constraints** (not suggestions) that every sub-agent MUST comply with. Violations trigger automatic rejection and re-generation.

### 5.1 Backend Prompts (backend.prompts.md)

#### REQ-BP-001: Architecture Rules

| Req ID | Requirement |
|--------|-------------|
| REQ-BP-001a | Each bounded context SHALL be 1 microservice. No monoliths. |
| REQ-BP-001b | Services SHALL communicate via async messaging (RabbitMQ/MassTransit) or gRPC for sync calls. |
| REQ-BP-001c | Clean Architecture SHALL be enforced: Domain → Application → Infrastructure → Presentation. Dependencies point inward ONLY. |
| REQ-BP-001d | CQRS pattern SHALL be enforced: Commands mutate state, Queries read state. Never mixed. |
| REQ-BP-001e | An API Gateway (Ocelot or YARP) SHALL be used for routing. No direct client-to-microservice calls. |

#### REQ-BP-002: Microservice Folder Structure

Each microservice SHALL follow this structure:

```
ServiceName/
├── ServiceName.Domain/          # Entities, Value Objects, Domain Events
├── ServiceName.Application/     # Use Cases, DTOs, Interfaces, Validators
│   ├── Commands/
│   ├── Queries/
│   ├── DTOs/
│   ├── Interfaces/
│   ├── Validators/              # FluentValidation
│   └── Mappings/                # AutoMapper profiles
├── ServiceName.Infrastructure/  # EF Core, Repos, External Services
│   ├── Persistence/
│   ├── Repositories/
│   └── Services/
├── ServiceName.API/             # Controllers, Middleware, DI
│   ├── Controllers/
│   ├── Middleware/
│   └── Extensions/
└── ServiceName.Tests/
    ├── Unit/
    ├── Integration/
    └── Contract/
```

#### REQ-BP-003: SOLID Principles — Enforced

| Principle | Requirement |
|-----------|-------------|
| **Single Responsibility** | One class = one reason to change. Controllers ONLY route HTTP. Services ONLY contain business logic. Repositories ONLY handle data access. |
| **Open/Closed** | Use strategy pattern for business rule variations. Never modify existing classes to add new behavior — extend via interfaces. |
| **Liskov Substitution** | All implementations MUST be fully substitutable for their interfaces. No interface methods throwing `NotImplementedException`. |
| **Interface Segregation** | No fat interfaces. Split into focused interfaces (e.g., `IUserService`, `IEmailService`, `INotificationService`). |
| **Dependency Inversion** | Controllers inject `IService` (not `Service`). Services inject `IRepository` (not `Repository`). NEVER use `new` for dependencies. |

#### REQ-BP-004: Hard Code Quality Rules

| Req ID | Rule |
|--------|------|
| REQ-BP-004a | Functions/methods: MAXIMUM 30 lines. If longer, extract helper methods. |
| REQ-BP-004b | Classes: MAXIMUM 300 lines. If longer, split responsibilities. |
| REQ-BP-004c | Controllers: ONLY call service layer through interfaces. No business logic. Max 5 actions per controller. |
| REQ-BP-004d | Service layer MUST use FluentValidation for input validation and AutoMapper/Mapster for DTO mapping. No direct EF Core calls — use repository pattern. |
| REQ-BP-004e | Generic `IRepository<T>` base + specific repositories for complex queries. |
| REQ-BP-004f | Global exception middleware. No try-catch in controllers. Domain exceptions translate to HTTP status codes. |
| REQ-BP-004g | Structured logging via Serilog. Every service method logs entry/exit at Debug level. |
| REQ-BP-004h | No magic strings. All constants in dedicated `Constants.cs` or enum types. |
| REQ-BP-004i | No primitive obsession. Use Value Objects for Email, Money, PhoneNumber, etc. |
| REQ-BP-004j | Use `Result<T>` pattern instead of throwing exceptions for business logic failures. |

### 5.2 Frontend Prompts (frontend.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-FP-001 | Component architecture SHALL follow Atomic Design (atoms → molecules → organisms → templates → pages). |
| REQ-FP-002 | State management SHALL use Zustand or Redux Toolkit. No prop drilling beyond 2 levels. |
| REQ-FP-003 | A dedicated `api/` directory with typed client SHALL exist. All API calls go through a central `httpClient` wrapper. |
| REQ-FP-004 | Components: MAXIMUM 150 lines. Extract custom hooks for logic. Presentational vs Container separation. |
| REQ-FP-005 | CSS: Tailwind utility-first OR CSS Modules. No inline styles. No global CSS except resets. |
| REQ-FP-006 | Forms SHALL use React Hook Form + Zod schema validation. Never manual validation. |
| REQ-FP-007 | Every route SHALL be wrapped in `ErrorBoundary`. Fallback UI for every error state. |
| REQ-FP-008 | Accessibility: WCAG 2.1 AA minimum. Every interactive element has aria labels. Keyboard navigation required. |
| REQ-FP-009 | Testing: React Testing Library. Test behavior not implementation. Minimum 80% coverage for components. |
| REQ-FP-010 | Strict TypeScript. All props typed. All API responses typed. Zero `any` allowed. |

### 5.3 Database Prompts (database.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-DB-001 | Schema-first: All schema changes via EF Core migrations. No manual SQL in production. |
| REQ-DB-002 | Naming: `snake_case` for PostgreSQL tables/columns. `PascalCase` for SQL Server. |
| REQ-DB-003 | Every foreign key SHALL be indexed. Composite indexes for frequent query patterns. Covering indexes for read-heavy tables. |
| REQ-DB-004 | Soft deletes: All entities SHALL use `IsDeleted` + `DeletedAt`. Never hard delete user data. |
| REQ-DB-005 | Audit trail: `CreatedAt`, `UpdatedAt`, `CreatedBy`, `UpdatedBy` on every table. |
| REQ-DB-006 | Connection pooling enabled. Connection string in environment variables, never in code. |
| REQ-DB-007 | No N+1 queries. Use `.Include()` for eager loading or projection queries. Log slow queries (>100ms). |
| REQ-DB-008 | Separate seeder per microservice. Test data in development only. |

### 5.4 Security Prompts (security.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-SEC-001 | JWT Bearer with refresh tokens. Access token: 15 min TTL. Refresh token: 7 day TTL, single use, stored hashed. |
| REQ-SEC-002 | Policy-based authorization. No role checks in controllers. Use `[Authorize(Policy = "...")]`. |
| REQ-SEC-003 | Validate at API boundary (FluentValidation) AND domain layer. Never trust client input. |
| REQ-SEC-004 | ONLY parameterized queries via EF Core. No raw SQL concatenation. If raw SQL needed, use `FromSqlInterpolated`. |
| REQ-SEC-005 | Output encoding by default. CSP headers. No `dangerouslySetInnerHTML` without sanitization. |
| REQ-SEC-006 | Explicit CORS origin whitelist. No wildcard (`*`) in production. |
| REQ-SEC-007 | Secrets in Azure Key Vault or AWS Secrets Manager. Never in `appsettings.json`. Never committed to git. |
| REQ-SEC-008 | ASP.NET Rate Limiter middleware. Per-endpoint and per-user limits. |
| REQ-SEC-009 | Enforce HSTS. Redirect HTTP to HTTPS. Min TLS 1.2. |
| REQ-SEC-010 | Dependabot or Snyk for dependency scanning. Block PRs with critical vulnerabilities. |

### 5.5 Testing Prompts (testing.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-TST-001 | Unit tests: xUnit + Moq/NSubstitute. One test class per production class. Arrange-Act-Assert pattern. |
| REQ-TST-002 | Integration tests: `WebApplicationFactory<Program>`. Test full HTTP pipeline. Use Testcontainers for database. |
| REQ-TST-003 | Contract tests: Pact.NET for consumer-driven contracts between microservices. |
| REQ-TST-004 | Minimum 80% line coverage. 100% for domain logic. Coverage gate blocks CI if below threshold. |
| REQ-TST-005 | Naming convention: `MethodName_StateUnderTest_ExpectedBehavior`. |
| REQ-TST-006 | Each test fully isolated. No shared mutable state. Use fresh database per test class. |
| REQ-TST-007 | Mutation testing: Stryker.NET for critical business logic. Mutation score > 70%. |
| REQ-TST-008 | Performance tests: k6 or NBomber for load testing. Define SLOs upfront. |

### 5.6 CI/CD Prompts (cicd.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-CI-001 | Pipeline stages: Restore → Build → Test → Lint → Security Scan → Docker Build → Deploy to Staging → Integration Tests → Deploy to Prod. |
| REQ-CI-002 | Docker: Multi-stage builds. Non-root user. Alpine-based images. Layer caching optimized. |
| REQ-CI-003 | Infrastructure: Terraform/Pulumi for IaC. No manual cloud console changes. |
| REQ-CI-004 | GitFlow: `main` (production), `develop` (staging), `feature/*` branches. PR required for all merges. |
| REQ-CI-005 | Commit convention: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`). Enforce via commitlint. |
| REQ-CI-006 | Health check failure triggers automatic rollback to previous version. |
| REQ-CI-007 | Secrets: GitHub Actions secrets or Azure DevOps variable groups. Never echoed in logs. |
| REQ-CI-008 | Artifact versioning: SemVer. Auto-incremented by CI. Docker tags match git tags. |

### 5.7 API Design Prompts (api-design.prompts.md)

| Req ID | Requirement |
|--------|-------------|
| REQ-API-001 | REST: Resource-oriented URLs. Plural nouns (`/api/v1/users`). HTTP verbs for actions. |
| REQ-API-002 | URL-based versioning (`v1`, `v2`). Never break existing consumers. |
| REQ-API-003 | Response envelope: `{ data, errors, meta }` structure. Consistent across all endpoints. |
| REQ-API-004 | Cursor-based pagination for large datasets. Offset-based for small. Always return `totalCount` and `hasMore`. |
| REQ-API-005 | Error format: RFC 7807 Problem Details. Include `type`, `title`, `status`, `detail`, `instance`. |
| REQ-API-006 | OpenAPI spec generated from code annotations. Swagger UI in development. Schema validation in CI. |
| REQ-API-007 | POST/PUT endpoints SHALL accept `Idempotency-Key` header. Store and deduplicate. |
| REQ-API-008 | Include `_links` in responses for HATEOAS discoverability (recommended for public APIs). |

---

## 6. Feature Decomposition Requirements

### 6.1 Decomposition Rules

| Req ID | Requirement |
|--------|-------------|
| FR-DEC-001 | The App Analyzer Agent SHALL decompose a prompt into bounded features using LLM reasoning and domain patterns (finance, e-commerce, social, SaaS). |
| FR-DEC-002 | Each feature SHALL be independently implementable with its own bounded context. |
| FR-DEC-003 | Features SHALL be assigned priority levels (P0–P2). |
| FR-DEC-004 | A dependency graph (DAG) SHALL be generated to determine implementation ordering. |

### 6.2 PersonalFinance Example Decomposition

| Feature ID | Feature Name | Description | Priority |
|------------|-------------|-------------|----------|
| 001 | Authentication & User Management | User registration, login (email/OAuth), MFA, profile management, session handling, password reset, account deletion | P0 — Critical Path |
| 002 | Accounts & Wallets | Bank accounts, credit cards, cash wallets, crypto wallets, net worth calculation, account linking, balance tracking | P0 — Critical Path |
| 003 | Transactions | Income/expense tracking, categorization (auto + manual), recurring transactions, splits, attachments (receipts), search & filter | P0 — Critical Path |
| 004 | Budgeting | Monthly/custom period budgets, category-level budgets, budget alerts, rollover rules, envelope budgeting, budget vs actual reports | P1 — High |
| 005 | Investments | Portfolio tracking, stock/mutual fund/ETF, P&L calculation, dividend tracking, asset allocation, benchmark comparison | P1 — High |
| 006 | Bills & Subscriptions | Recurring bill tracking, due date reminders, subscription detection from transactions, cancellation tracking, cost optimization suggestions | P1 — High |
| 007 | Financial Goals | Goal creation (emergency fund, vacation, house), progress tracking, suggested monthly savings, goal-linked accounts, milestone celebrations | P2 — Medium |
| 008 | Reports & Analytics | Spending trends, income vs expense, category breakdown, net worth over time, tax-ready reports, export (PDF/CSV), custom date ranges | P1 — High |
| 009 | Alerts & Notifications | Budget exceeded, bill due, large transaction, low balance, goal milestones, weekly/monthly summaries, multi-channel (email, push, in-app) | P2 — Medium |
| 010 | Data Import & Bank Integration | Plaid/Yodlee integration, CSV import, OFX/QFX import, transaction reconciliation, duplicate detection, import history | P1 — High |
| 011 | AI Financial Advisor | Spending pattern analysis, savings recommendations, anomaly detection, cash flow forecasting, debt payoff optimization, natural language queries | P2 — Medium |
| 012 | Admin & System Management | User management, system health dashboard, feature flags, audit logs, data export compliance (GDPR), rate limiting config | P1 — High |

### 6.3 Feature Dependency Graph

| Feature | Depends On | Phase |
|---------|-----------|-------|
| 001 Authentication | None (foundation) | Phase 1 |
| 002 Accounts & Wallets | 001 | Phase 1 |
| 003 Transactions | 001, 002 | Phase 2 |
| 004 Budgeting | 001, 002, 003 | Phase 2 |
| 005 Investments | 001, 002 | Phase 2 |
| 006 Bills & Subscriptions | 001, 002, 003 | Phase 2 |
| 007 Financial Goals | 001, 002 | Phase 3 |
| 008 Reports & Analytics | 001, 002, 003, 004, 005 | Phase 3 |
| 009 Alerts & Notifications | 001 + any notifiable feature | Phase 3 |
| 010 Data Import | 001, 002, 003 | Phase 2 |
| 011 AI Advisor | 001, 002, 003, 004, 005, 008 | Phase 4 |
| 012 Admin | 001 | Phase 1 |

---

## 7. Per-Feature Spec Pipeline Requirements

Each feature SHALL go through an identical 7-phase pipeline producing the following artifacts:

### 7.1 spec.md — Feature Specification

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-001 | SHALL define WHAT and WHY. No tech stack. No implementation details. |
| REQ-PIPE-002 | SHALL include: feature overview, business justification, user personas, user stories (Given/When/Then), functional requirements (numbered, testable), non-functional requirements (performance SLOs, availability targets), out-of-scope exclusions, assumptions/constraints, and edge cases. |

### 7.2 research.md — Technical Research

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-003 | SHALL resolve all unknowns BEFORE planning begins. |
| REQ-PIPE-004 | SHALL include: technology options with pros/cons matrix, library version compatibility, third-party service evaluation, performance benchmarks, security considerations, known limitations, and reference implementations. |

### 7.3 data-model.md — Data Model Design

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-005 | SHALL provide complete entity design for the feature's bounded context. |
| REQ-PIPE-006 | SHALL include: entity definitions with properties/types, relationships, value objects with validation rules, index strategy, migration plan, seed data specification, and data retention rules. |

### 7.4 plan.md — Technical Implementation Plan

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-007 | SHALL define the HOW, referencing prompt files for coding standards. |
| REQ-PIPE-008 | SHALL include: architecture decisions, component breakdown, API endpoint design (request/response schemas), frontend component tree, integration points, performance strategy, constitution compliance check, and applicable prompt file references. |

### 7.5 checklist.md — Quality Checklist

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-009 | SHALL serve as a validation gate — feature cannot move to implementation until all items pass. |
| REQ-PIPE-010 | SHALL validate: user stories have acceptance criteria, data model reviewed for normalization, API contracts defined and versioned, security requirements addressed, edge cases documented, performance SLOs defined, cross-feature dependencies identified, and prompt file compliance verified. |

### 7.6 edge-cases.md — Edge Case Analysis

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-011 | Edge cases SHALL be treated as a first-class spec artifact. |
| REQ-PIPE-012 | SHALL cover: concurrency scenarios, network failure handling, data boundary conditions, state machine edge cases, integration failure scenarios, security edge cases, UI edge cases, and data migration edge cases. |

### 7.7 tasks.md — Actionable Task Breakdown

| Req ID | Requirement |
|--------|-------------|
| REQ-PIPE-013 | Tasks SHALL be ordered by dependency with parallel execution markers `[P]`. |
| REQ-PIPE-014 | SHALL include: tasks grouped by user story, each task with ID/description/file paths/dependencies/estimated effort, test tasks BEFORE implementation tasks (TDD enforcement), checkpoints per user story, and conventional commit convention per task. |

---

## 8. Sub-Agent Execution Requirements

### 8.1 Context Loading

| Req ID | Requirement |
|--------|-------------|
| REQ-SA-001 | Sub-agents SHALL load ONLY: `constitution.md`, applicable prompt files, the feature's own spec artifacts, and shared contracts from dependent features. |
| REQ-SA-002 | Sub-agents SHALL NOT load any other feature's implementation code. |

### 8.2 Execution Loop

| Step | Req ID | Requirement |
|------|--------|-------------|
| 1 | REQ-SA-003 | **Load Context**: Read all governance files + feature spec artifacts. |
| 2 | REQ-SA-004 | **Validate Preconditions**: Ensure dependent features' contracts are available. |
| 3 | REQ-SA-005 | **Execute Tasks**: Follow `tasks.md` in order, respecting `[P]` parallel markers. |
| 4 | REQ-SA-006 | **Quality Check**: After each task — lint, build, run unit tests. |
| 5 | REQ-SA-007 | **Edge Case Verification**: Cross-reference `edge-cases.md` after implementation. |
| 6 | REQ-SA-008 | **Self-Review**: Agent reviews own code against prompt file rules. |
| 7 | REQ-SA-009 | **Auto-Fix Loop**: Test failure → analyze → fix → re-test. Maximum 3 iterations before escalation. |
| 8 | REQ-SA-010 | **Commit & Report**: Conventional commit per task. Status report to orchestrator. |

---

## 9. CLI Commands Requirements

| Req ID | Command | Description | Example |
|--------|---------|-------------|---------|
| REQ-CLI-001 | `specforge init <project>` | Scaffold project with `.specforge/` directory, prompt files, templates, and agent config. | `specforge init PersonalFinance --agent claude --stack dotnet` |
| REQ-CLI-002 | `specforge decompose` | Take the app description from constitution and auto-split into features. | `specforge decompose "Create a webapp for PersonalFinance"` |
| REQ-CLI-003 | `specforge specify <feature>` | Generate `spec.md` for a specific feature. | `/specforge.specify 001-authentication` |
| REQ-CLI-004 | `specforge research <feature>` | Generate `research.md` resolving all technical unknowns. | `/specforge.research 001-authentication` |
| REQ-CLI-005 | `specforge datamodel <feature>` | Generate `data-model.md` with entities, relationships, indexes. | `/specforge.datamodel 001-authentication` |
| REQ-CLI-006 | `specforge plan <feature>` | Generate `plan.md` with full implementation blueprint. | `/specforge.plan 001-authentication` |
| REQ-CLI-007 | `specforge checklist <feature>` | Generate and validate `checklist.md` quality gate. | `/specforge.checklist 001-authentication` |
| REQ-CLI-008 | `specforge edgecases <feature>` | Generate `edge-cases.md` with comprehensive edge case analysis. | `/specforge.edgecases 001-authentication` |
| REQ-CLI-009 | `specforge tasks <feature>` | Generate `tasks.md` with ordered, parallelizable implementation tasks. | `/specforge.tasks 001-authentication` |
| REQ-CLI-010 | `specforge implement <feature>` | Execute all tasks for a feature via sub-agent. | `/specforge.implement 001-authentication` |
| REQ-CLI-011 | `specforge implement --all` | Execute all features respecting dependency graph. | `specforge implement --all --parallel` |
| REQ-CLI-012 | `specforge analyze` | Cross-feature consistency and coverage analysis. | `/specforge.analyze` |
| REQ-CLI-013 | `specforge status` | Show progress dashboard for all features. | `specforge status` |

---

## 10. Edge Case Handling Requirements

The following edge cases in the SpecForge tool itself SHALL be handled:

| Req ID | Edge Case | Required Handling |
|--------|-----------|-------------------|
| REQ-EC-001 | **Circular Feature Dependencies** | Dependency graph validation at decomposition time. If A depends on B and B depends on A, the decomposer SHALL extract the shared concern into a new feature (e.g., `000-shared-contracts`). |
| REQ-EC-002 | **Context Window Overflow** | Sub-agents load only their feature's artifacts + shared contracts. If a single feature's spec exceeds context limits, the system SHALL split it into sub-features automatically. |
| REQ-EC-003 | **Ambiguous One-Line Prompt** | If the App Analyzer cannot confidently decompose, it SHALL enter an interactive clarification loop asking 3–5 targeted questions before proceeding. |
| REQ-EC-004 | **Conflicting Prompt Rules** | Prompt files have explicit precedence: `security.prompts.md` > `architecture.prompts.md` > `backend.prompts.md`. Conflicts resolved by highest-priority file. |
| REQ-EC-005 | **AI Hallucinating Libraries/APIs** | Research phase MUST verify every library exists, check the version number, and confirm API compatibility. Unverified dependencies block planning. |
| REQ-EC-006 | **Feature Scope Creep During Implementation** | Sub-agents are bound to `tasks.md`. Any generated code not traceable to a task ID SHALL be flagged and rejected. |
| REQ-EC-007 | **Test-Fix Loop Infinite Cycling** | Maximum 3 fix iterations. After 3 failures, the task SHALL be escalated to the user with a diagnostic report. |
| REQ-EC-008 | **Cross-Feature Contract Breaking Changes** | Shared contracts are versioned. A feature SHALL NOT modify a contract without bumping the version and updating all consumers. |
| REQ-EC-009 | **Prompt File Not Applicable to Tech Stack** | If user specifies a different stack than prompt file defaults, the system SHALL auto-adapt rules to the target stack. |
| REQ-EC-010 | **Partial Implementation Recovery** | Each task commit is atomic. If the agent crashes mid-feature, it SHALL resume from the last committed task, not from scratch. |

---

## 11. Development Roadmap Phases

These phases describe building SpecForge itself (the tool), not the target applications it generates.

### Phase 1 — Foundation (Weeks 1–4)

| Req ID | Deliverable |
|--------|-------------|
| REQ-RD-001 | CLI scaffold: `specforge init <project>` command with template download, agent detection, directory structure creation. |
| REQ-RD-002 | Constitution generator: Interactive `constitution.md` creation with domain-aware defaults. |
| REQ-RD-003 | Prompt file library: All 7 prompt files with .NET defaults and pluggable tech stacks. |
| REQ-RD-004 | Template engine: All 7 per-feature templates with smart placeholders. |
| REQ-RD-005 | Feature numbering & branching: Auto-increment, git branches, directory scaffolding. |
| REQ-RD-006 | Basic slash commands: `/specforge.constitution`, `/specforge.specify`, `/specforge.plan`, `/specforge.tasks`, `/specforge.implement`. |

### Phase 2 — Intelligence Layer (Weeks 5–8)

| Req ID | Deliverable |
|--------|-------------|
| REQ-RD-007 | App Analyzer Agent: Takes one-line prompt, understands domain, identifies features using LLM reasoning. |
| REQ-RD-008 | Feature Decomposer: Splits app into bounded features with dependency graph using domain patterns. |
| REQ-RD-009 | Edge Case Analyzer: Auto-generates `edge-cases.md` by analyzing spec against known patterns. |
| REQ-RD-010 | Research Agent: Auto-resolves "NEEDS CLARIFICATION" items. |
| REQ-RD-011 | Clarification Engine: `/specforge.clarify` with structured Q&A. |
| REQ-RD-012 | Analyze Command: `/specforge.analyze` for cross-artifact consistency checking. |

### Phase 3 — Sub-Agent Engine (Weeks 9–12)

| Req ID | Deliverable |
|--------|-------------|
| REQ-RD-013 | Sub-Agent Isolation: Each feature in isolated context. No cross-contamination. |
| REQ-RD-014 | Parallel Execution: Features without dependencies run simultaneously. Task-level parallelism. |
| REQ-RD-015 | Auto-Fix Loop: Test failure → analysis → fix → re-test (max 3 iterations). |
| REQ-RD-016 | Quality Gate: Post-implementation validation (lint, build, test coverage, security scan, prompt compliance). |
| REQ-RD-017 | Cross-Feature Integration: Merge features, resolve shared contracts, run integration tests. |
| REQ-RD-018 | Progress Dashboard: Real-time status of all features. |

### Phase 4 — Polish & Ecosystem (Weeks 13–16)

| Req ID | Deliverable |
|--------|-------------|
| REQ-RD-019 | Multi-Agent Support: Claude Code, Copilot, Gemini CLI, Cursor, Windsurf, Codex compatibility. |
| REQ-RD-020 | Tech Stack Plugins: Pluggable prompt files for multiple backend/frontend frameworks. |
| REQ-RD-021 | Brownfield Mode: Analyze existing codebase, generate specs from code, add features incrementally. |
| REQ-RD-022 | PR Workflow: Auto-create PRs per feature with spec summary, checklist status, test results. |
| REQ-RD-023 | Custom Prompt Authoring: UI/CLI for teams to write and validate their own prompt files. |
| REQ-RD-024 | VS Code Extension: Sidebar showing feature tree, spec status, one-click artifact navigation. |

---

*End of Requirements Document*
