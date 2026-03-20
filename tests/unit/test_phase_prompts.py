"""Unit tests for PhasePrompt dataclass and all 8 prompt instances."""

from __future__ import annotations

import dataclasses

from specforge.core.config import CLEAN_MARKDOWN_INSTRUCTION, PHASE_REQUIRED_SECTIONS
from specforge.core.phase_prompts import (
    CHECKLIST_PROMPT,
    DATAMODEL_PROMPT,
    DECOMPOSE_PROMPT,
    EDGECASE_PROMPT,
    PHASE_PROMPTS,
    PLAN_PROMPT,
    RESEARCH_PROMPT,
    SPEC_PROMPT,
    TASKS_PROMPT,
    PhasePrompt,
)


# ── PhasePrompt frozen dataclass ─────────────────────────────────────


class TestPhasePromptDataclass:
    def test_is_frozen(self) -> None:
        assert dataclasses.fields(PhasePrompt) is not None
        assert PhasePrompt.__dataclass_params__.frozen is True  # type: ignore[attr-defined]

    def test_cannot_mutate_fields(self) -> None:
        prompt = SPEC_PROMPT
        try:
            prompt.phase_name = "changed"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except dataclasses.FrozenInstanceError:
            pass

    def test_has_expected_fields(self) -> None:
        field_names = {f.name for f in dataclasses.fields(PhasePrompt)}
        expected = {
            "phase_name",
            "system_instructions",
            "skeleton",
            "required_sections",
            "clean_markdown_instruction",
            "enrichment_template",
        }
        assert field_names == expected

    def test_clean_markdown_default(self) -> None:
        prompt = PhasePrompt(
            phase_name="test",
            system_instructions="test instructions",
            skeleton="# test",
            required_sections=("Heading",),
        )
        assert prompt.clean_markdown_instruction == CLEAN_MARKDOWN_INSTRUCTION


# ── PHASE_PROMPTS registry ───────────────────────────────────────────


class TestPhasePromptsRegistry:
    def test_all_8_phases_present(self) -> None:
        expected_keys = {
            "spec", "research", "datamodel", "edgecase",
            "plan", "checklist", "tasks", "decompose",
        }
        assert set(PHASE_PROMPTS.keys()) == expected_keys

    def test_registry_has_8_entries(self) -> None:
        assert len(PHASE_PROMPTS) == 8

    def test_each_value_is_phase_prompt(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert isinstance(prompt, PhasePrompt), f"{key} is not a PhasePrompt"

    def test_phase_name_matches_key(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert prompt.phase_name == key


# ── Non-empty required attributes ────────────────────────────────────


class TestPhasePromptContent:
    def test_each_has_nonempty_system_instructions(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert len(prompt.system_instructions) > 0, (
                f"{key} has empty system_instructions"
            )

    def test_each_has_nonempty_skeleton(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert len(prompt.skeleton) > 0, f"{key} has empty skeleton"

    def test_each_has_nonempty_required_sections(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert len(prompt.required_sections) > 0, (
                f"{key} has empty required_sections"
            )

    def test_required_sections_match_config(self) -> None:
        for key, prompt in PHASE_PROMPTS.items():
            assert prompt.required_sections == PHASE_REQUIRED_SECTIONS[key], (
                f"{key} required_sections mismatch"
            )


# ── Spec skeleton content ────────────────────────────────────────────


class TestSpecPrompt:
    def test_skeleton_contains_user_scenarios(self) -> None:
        assert "User Scenarios" in SPEC_PROMPT.skeleton

    def test_skeleton_contains_requirements(self) -> None:
        assert "Requirements" in SPEC_PROMPT.skeleton

    def test_skeleton_contains_success_criteria(self) -> None:
        assert "Success Criteria" in SPEC_PROMPT.skeleton

    def test_skeleton_contains_acceptance_scenarios(self) -> None:
        assert "Acceptance Scenarios" in SPEC_PROMPT.skeleton

    def test_skeleton_contains_fr_format(self) -> None:
        assert "FR-001" in SPEC_PROMPT.skeleton

    def test_skeleton_contains_sc_format(self) -> None:
        assert "SC-001" in SPEC_PROMPT.skeleton


# ── Tasks skeleton content ───────────────────────────────────────────


class TestTasksPrompt:
    def test_skeleton_contains_phase_1(self) -> None:
        assert "Phase 1" in TASKS_PROMPT.skeleton

    def test_skeleton_contains_checkbox_format(self) -> None:
        assert "- [ ]" in TASKS_PROMPT.skeleton

    def test_skeleton_contains_task_id_format(self) -> None:
        assert "T001" in TASKS_PROMPT.skeleton

    def test_instructions_mention_tdd(self) -> None:
        assert "TDD" in TASKS_PROMPT.system_instructions


# ── Decompose skeleton content ───────────────────────────────────────


class TestDecomposePrompt:
    def test_skeleton_contains_features_key(self) -> None:
        assert '"features"' in DECOMPOSE_PROMPT.skeleton

    def test_skeleton_contains_services_key(self) -> None:
        assert '"services"' in DECOMPOSE_PROMPT.skeleton

    def test_skeleton_is_valid_json(self) -> None:
        import json

        parsed = json.loads(DECOMPOSE_PROMPT.skeleton)
        assert "features" in parsed
        assert "services" in parsed


# ── Individual prompt instances ──────────────────────────────────────


class TestIndividualPrompts:
    def test_research_skeleton_contains_decision(self) -> None:
        assert "Decision" in RESEARCH_PROMPT.skeleton

    def test_datamodel_skeleton_contains_entity_diagram(self) -> None:
        assert "Entity Diagram" in DATAMODEL_PROMPT.skeleton

    def test_edgecase_skeleton_contains_severity(self) -> None:
        assert "Severity" in EDGECASE_PROMPT.skeleton

    def test_plan_skeleton_contains_technical_context(self) -> None:
        assert "Technical Context" in PLAN_PROMPT.skeleton

    def test_plan_skeleton_contains_constitution_check(self) -> None:
        assert "Constitution Check" in PLAN_PROMPT.skeleton

    def test_checklist_skeleton_contains_chk_format(self) -> None:
        assert "CHK-001" in CHECKLIST_PROMPT.skeleton
