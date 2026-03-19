"""PhasePrompt — frozen dataclass + 8 prompt definitions (Feature 015)."""

from __future__ import annotations

from dataclasses import dataclass

from specforge.core.config import CLEAN_MARKDOWN_INSTRUCTION, PHASE_REQUIRED_SECTIONS


@dataclass(frozen=True)
class PhasePrompt:
    """Per-phase LLM instructions with Spec-Kit template skeleton."""

    phase_name: str
    system_instructions: str
    skeleton: str
    required_sections: tuple[str, ...]
    clean_markdown_instruction: str = CLEAN_MARKDOWN_INSTRUCTION


SPEC_PROMPT = PhasePrompt(
    phase_name="spec",
    system_instructions=(
        "You are a senior software architect writing a feature specification. "
        "Follow the exact Spec-Kit format below. Use FR-NNN for functional "
        "requirements, SC-NNN for success criteria. Every user story must "
        "have Given/When/Then acceptance scenarios. Include edge cases."
    ),
    skeleton="""\
# Feature Specification: {feature_name}

**Feature Branch**: `{slug}`
**Created**: {date}
**Status**: Draft

## Clarifications

## User Scenarios & Testing *(mandatory)*

### User Story 1 — [Title] (Priority: P1)

[Story description]

**Acceptance Scenarios**:

1. **Given** ... **When** ... **Then** ...

### Edge Cases

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: [requirement]

### Key Entities

## Success Criteria *(mandatory)*

- **SC-001**: [criterion]
""",
    required_sections=PHASE_REQUIRED_SECTIONS["spec"],
)


RESEARCH_PROMPT = PhasePrompt(
    phase_name="research",
    system_instructions=(
        "You are a technical researcher investigating implementation "
        "decisions for a software feature. For each research topic, "
        "provide a Decision, Rationale, and Alternatives Considered. "
        "Number sections as R1, R2, etc."
    ),
    skeleton="""\
# Research: {feature_name}

**Feature**: {slug}
**Date**: {date}

## R1: [Topic Title]

**Decision**: [chosen approach]

**Rationale**: [why this approach]

**Alternatives considered**:
- [alternative] — rejected because [reason]
""",
    required_sections=PHASE_REQUIRED_SECTIONS["research"],
)


DATAMODEL_PROMPT = PhasePrompt(
    phase_name="datamodel",
    system_instructions=(
        "You are a data architect designing the entity model for a "
        "software feature. Include an ASCII entity diagram, detailed "
        "entity tables with fields/types/constraints, and relationship "
        "descriptions. Consider the architecture type for entity scope."
    ),
    skeleton="""\
# Data Model: {feature_name}

**Feature**: {slug}
**Date**: {date}

## Entity Diagram

```text
[ASCII diagram of entities and relationships]
```

## Entities

### [EntityName]

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Primary key |
""",
    required_sections=PHASE_REQUIRED_SECTIONS["datamodel"],
)


EDGECASE_PROMPT = PhasePrompt(
    phase_name="edgecase",
    system_instructions=(
        "You are a QA engineer identifying edge cases, failure modes, "
        "and boundary conditions for a software feature. Categorize each "
        "edge case by severity (Critical/High/Medium/Low) and include "
        "the expected behavior and mitigation strategy."
    ),
    skeleton="""\
# Edge Cases: {feature_name}

**Feature**: {slug}
**Date**: {date}

## Edge Cases

### EC-001: [Edge Case Title]

**Category**: [Security/Performance/Data Integrity/Concurrency/Input Validation]
**Severity**: [Critical/High/Medium/Low]
**Scenario**: [description]
**Expected Behavior**: [what should happen]
**Mitigation**: [how to handle it]
""",
    required_sections=PHASE_REQUIRED_SECTIONS["edgecase"],
)


PLAN_PROMPT = PhasePrompt(
    phase_name="plan",
    system_instructions=(
        "You are a tech lead writing an implementation plan. Include "
        "a summary, technical context (language, dependencies, storage, "
        "testing, platform), constitution compliance check, project "
        "structure with file paths, implementation phases, and "
        "complexity tracking. Reference entities from data-model.md "
        "and edge cases from edge-cases.md."
    ),
    skeleton="""\
# Implementation Plan: {feature_name}

**Branch**: `{slug}` | **Date**: {date}

## Summary

[Brief description of the implementation approach]

## Technical Context

**Language/Version**: [e.g., Python 3.11+]
**Primary Dependencies**: [frameworks and libraries]
**Storage**: [database/filesystem approach]
**Testing**: [test framework and approach]

## Constitution Check

| Principle | Gate | Status |
|-----------|------|--------|
| I. Spec-First | spec.md exists | PASS |

## Project Structure

```text
src/
├── [file structure]
```

## Implementation Phases

### Phase 1: [Phase Name]

## Complexity Tracking

| Violation | Why Needed | Alternative Rejected |
|-----------|------------|---------------------|
""",
    required_sections=PHASE_REQUIRED_SECTIONS["plan"],
)


CHECKLIST_PROMPT = PhasePrompt(
    phase_name="checklist",
    system_instructions=(
        "You are a quality assurance lead creating an implementation "
        "checklist. Group items by category. Use CHK-NNN format for "
        "each item. Each item should validate a specific requirement "
        "from the spec, referencing the FR or SC number."
    ),
    skeleton="""\
# Implementation Checklist: {feature_name}

**Purpose**: Validate implementation satisfies all requirements
**Created**: {date}
**Feature**: {slug}

## 1. [Category Name]

- [ ] CHK-001 [Checklist item description] [Completeness, Spec §FR-001]
- [ ] CHK-002 [Checklist item description] [Clarity, Spec §SC-001]

## Notes
""",
    required_sections=PHASE_REQUIRED_SECTIONS["checklist"],
)


TASKS_PROMPT = PhasePrompt(
    phase_name="tasks",
    system_instructions=(
        "You are a project manager creating a task breakdown. Use "
        "TDD order: test tasks before implementation tasks in each "
        "phase. Mark parallel-safe tasks with [P]. Use T001 format "
        "with checkbox syntax. Group tasks into phases matching the "
        "implementation plan. Include dependencies and execution order."
    ),
    skeleton="""\
# Tasks: {feature_name}

**Input**: Design documents from `{slug}`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: TDD enforced — test files BEFORE implementation files.

## Phase 1: Setup

- [ ] T001 [Description with exact file paths]
- [ ] T002 [P] [Description — parallel-safe]

## Dependencies & Execution Order

## Implementation Strategy
""",
    required_sections=PHASE_REQUIRED_SECTIONS["tasks"],
)


DECOMPOSE_PROMPT = PhasePrompt(
    phase_name="decompose",
    system_instructions=(
        "You are a software architect decomposing an application into "
        "features and services. Output a JSON object with 'features' "
        "array (each with id, name, description, priority, category, "
        "service) and 'services' array (each with name, slug, features, "
        "rationale). Include dependency mappings between features."
    ),
    skeleton="""\
{
  "features": [
    {
      "id": "001",
      "name": "feature-name",
      "display_name": "Feature Name",
      "description": "What this feature does",
      "priority": "P0",
      "category": "foundation",
      "service": "service-slug"
    }
  ],
  "services": [
    {
      "name": "Service Name",
      "slug": "service-slug",
      "features": ["001"],
      "rationale": "Why this grouping"
    }
  ]
}
""",
    required_sections=PHASE_REQUIRED_SECTIONS["decompose"],
)


PHASE_PROMPTS: dict[str, PhasePrompt] = {
    "spec": SPEC_PROMPT,
    "research": RESEARCH_PROMPT,
    "datamodel": DATAMODEL_PROMPT,
    "edgecase": EDGECASE_PROMPT,
    "plan": PLAN_PROMPT,
    "checklist": CHECKLIST_PROMPT,
    "tasks": TASKS_PROMPT,
    "decompose": DECOMPOSE_PROMPT,
}
"""Registry of all 8 PhasePrompt instances keyed by phase name."""
