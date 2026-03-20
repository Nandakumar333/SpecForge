"""Unit tests for ArtifactExtractor (Feature 017)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.artifact_extractor import ArtifactExtractor

SAMPLE_SPEC = """\
# Feature Specification: Auth Service

## User Scenarios & Testing

### User Story 1 — Login Flow (Priority: P1)

As a user I want to log in securely.

**Acceptance Scenarios**:

1. **Given** valid credentials **When** login **Then** token issued
2. **Given** invalid password **When** login **Then** 401 returned

### User Story 2 — Registration (Priority: P2)

As a new user I want to register.

**Acceptance Scenarios**:

1. **Given** unique email **When** register **Then** account created

## Requirements

- **FR-001**: System MUST validate email format
- **FR-002**: System MUST hash passwords with bcrypt
- **FR-003**: System MUST issue JWT tokens

## Success Criteria

- **SC-001**: Login completes under 200ms
- **SC-002**: Registration validates email uniqueness
"""

SAMPLE_RESEARCH = """\
# Research: Auth Service

## R1: Password Hashing Algorithm

**Decision**: bcrypt with cost factor 12

**Rationale**: Industry standard, resistant to GPU attacks

**Alternatives considered**:
- scrypt — rejected because higher memory requirements
- argon2 — rejected because less widespread library support

## R2: Token Format

**Decision**: JWT with RS256

**Rationale**: Asymmetric signing allows distributed verification
"""

SAMPLE_DATA_MODEL = """\
# Data Model: Auth Service

## Entity Diagram

```text
User -> Session
```

## Entities

### User

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email |
| password_hash | VARCHAR(72) | NOT NULL | Bcrypt hash |

### Session

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Session ID |
| user_id | UUID | FK | Owner |
| expires_at | TIMESTAMP | NOT NULL | Expiry |
"""

SAMPLE_EDGE_CASES = """\
# Edge Cases: Auth Service

### EC-001: Brute Force Attack

**Severity**: Critical
**Scenario**: Multiple failed login attempts

### EC-002: Expired Token Replay

**Severity**: High
**Scenario**: Token used after expiration

### EC-003: Unicode Email Edge

**Severity**: Medium
**Scenario**: Email with international characters
"""

SAMPLE_PLAN = """\
# Implementation Plan: Auth Service

## Summary

Implement auth with JWT tokens.

## Technical Context

Python 3.11+ with FastAPI.

## Phase 1: Setup

Database migration scripts.

## Phase 2: Core Logic

Token generation and validation.

## Phase 3: Testing

Unit and integration tests.
"""


class TestArtifactExtractor:
    def setup_method(self) -> None:
        self.extractor = ArtifactExtractor()

    def test_extract_from_spec(self) -> None:
        result = self.extractor.extract_from_spec(SAMPLE_SPEC)
        assert "user_stories" in result
        assert len(result["user_stories"]) == 2
        assert result["user_stories"][0]["title"] == "Login Flow"
        assert result["user_stories"][0]["priority"] == "P1"
        assert result["user_stories"][0]["scenario_count"] == 2
        assert len(result["functional_requirements"]) == 3
        assert len(result["success_criteria"]) == 2

    def test_extract_from_research(self) -> None:
        result = self.extractor.extract_from_research(SAMPLE_RESEARCH)
        assert "decisions" in result
        assert len(result["decisions"]) == 2
        assert result["decisions"][0]["topic"] == "Password Hashing Algorithm"
        assert "bcrypt" in result["decisions"][0]["decision"]

    def test_extract_from_data_model(self) -> None:
        result = self.extractor.extract_from_data_model(SAMPLE_DATA_MODEL)
        assert "entities" in result
        assert len(result["entities"]) == 2
        assert result["entities"][0]["name"] == "User"
        assert result["entities"][0]["field_count"] >= 2

    def test_extract_from_edge_cases(self) -> None:
        result = self.extractor.extract_from_edge_cases(SAMPLE_EDGE_CASES)
        assert "edge_cases" in result
        assert len(result["edge_cases"]) == 3
        assert result["edge_cases"][0]["id"] == "EC-001"
        assert result["edge_cases"][0]["severity"] == "Critical"

    def test_extract_from_plan(self) -> None:
        result = self.extractor.extract_from_plan(SAMPLE_PLAN)
        assert "phases" in result
        assert len(result["phases"]) == 3

    def test_empty_input(self) -> None:
        assert self.extractor.extract_from_spec(None) == {}
        assert self.extractor.extract_from_spec("") == {}
        assert self.extractor.extract_from_research(None) == {}
        assert self.extractor.extract_from_data_model(None) == {}
        assert self.extractor.extract_from_edge_cases(None) == {}
        assert self.extractor.extract_from_plan(None) == {}

    def test_format_for_prompt_compact(self) -> None:
        extractions = {
            "spec": self.extractor.extract_from_spec(SAMPLE_SPEC),
            "research": self.extractor.extract_from_research(SAMPLE_RESEARCH),
        }
        formatted = self.extractor.format_for_prompt("plan", extractions)
        assert "### Prior: spec" in formatted
        assert "### Prior: research" in formatted
        assert len(formatted) > 0

    def test_format_for_prompt_smaller_than_raw(self) -> None:
        """Structured extraction should be ≥30% smaller than raw text."""
        extractions = {
            "spec": self.extractor.extract_from_spec(SAMPLE_SPEC),
            "research": self.extractor.extract_from_research(SAMPLE_RESEARCH),
            "datamodel": self.extractor.extract_from_data_model(SAMPLE_DATA_MODEL),
        }
        formatted = self.extractor.format_for_prompt("plan", extractions)
        raw = SAMPLE_SPEC + SAMPLE_RESEARCH + SAMPLE_DATA_MODEL
        assert len(formatted) < len(raw) * 0.7

    def test_extract_all_reads_files(self, tmp_path: Path) -> None:
        service_dir = tmp_path / "auth-service"
        service_dir.mkdir()
        (service_dir / "spec.md").write_text(SAMPLE_SPEC, encoding="utf-8")
        (service_dir / "research.md").write_text(SAMPLE_RESEARCH, encoding="utf-8")

        result = self.extractor.extract_all(service_dir, "datamodel")
        assert result.ok
        assert "spec" in result.value
        assert "research" in result.value
        assert "datamodel" not in result.value

    def test_extract_all_missing_files(self, tmp_path: Path) -> None:
        service_dir = tmp_path / "empty"
        service_dir.mkdir()
        result = self.extractor.extract_all(service_dir, "plan")
        assert result.ok
        assert result.value.get("spec") == {}
