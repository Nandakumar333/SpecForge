"""Unit tests for config constants and type literals."""

from specforge.core.config import (
    AGENT_EXECUTABLES,
    AGENT_PRIORITY,
    EDGE_CASE_BASE_COUNT,
    EDGE_CASE_CATEGORY_PRIORITY,
    EDGE_CASE_MAX_PER_SERVICE,
    EDGE_CASE_PER_DEPENDENCY,
    EDGE_CASE_PER_EVENT,
    EDGE_CASE_PER_EXTRA_FEATURE,
    MICROSERVICE_EDGE_CASE_CATEGORIES,
    MODULAR_MONOLITH_EXTRA_CATEGORIES,
    PREREQUISITES,
    SEVERITY_DATA_OWNERSHIP,
    SEVERITY_DEFAULT_OPTIONAL,
    SEVERITY_DEFAULT_REQUIRED,
    SEVERITY_INTERFACE_CONTRACT,
    SEVERITY_MATRIX_MICROSERVICE,
    SEVERITY_MATRIX_MONOLITH,
    STANDARD_EDGE_CASE_CATEGORIES,
    SUPPORTED_STACKS,
)


class TestAgentPriority:
    def test_priority_order(self) -> None:
        expected = ["claude", "copilot", "gemini", "cursor", "windsurf", "codex"]
        assert expected == AGENT_PRIORITY

    def test_priority_has_six_agents(self) -> None:
        assert len(AGENT_PRIORITY) == 6

    def test_all_agents_have_executables(self) -> None:
        for agent in AGENT_PRIORITY:
            assert agent in AGENT_EXECUTABLES


class TestSupportedStacks:
    def test_stacks_membership(self) -> None:
        expected = {"dotnet", "nodejs", "python", "go", "java"}
        assert set(SUPPORTED_STACKS) == expected


class TestAgentExecutables:
    def test_keys_match_priority(self) -> None:
        assert set(AGENT_EXECUTABLES.keys()) == set(AGENT_PRIORITY)

    def test_each_entry_is_nonempty_list(self) -> None:
        for agent, execs in AGENT_EXECUTABLES.items():
            assert isinstance(execs, list), f"{agent} executables is not a list"
            assert len(execs) > 0, f"{agent} has no executables"

    def test_copilot_executable(self) -> None:
        assert AGENT_EXECUTABLES["copilot"] == ["copilot"]

    def test_claude_executable(self) -> None:
        assert AGENT_EXECUTABLES["claude"] == ["claude"]


class TestPrerequisites:
    def test_prerequisites_contains_git(self) -> None:
        assert "git" in PREREQUISITES

    def test_prerequisites_contains_python(self) -> None:
        assert "python" in PREREQUISITES

    def test_prerequisites_contains_uv(self) -> None:
        assert "uv" in PREREQUISITES


# ── Feature 007: Edge Case Analysis Engine constants ──────────────────


class TestEdgeCaseConstants:
    def test_max_per_service(self) -> None:
        assert EDGE_CASE_MAX_PER_SERVICE == 30

    def test_budget_formula_constants(self) -> None:
        assert EDGE_CASE_BASE_COUNT == 6
        assert EDGE_CASE_PER_DEPENDENCY == 2
        assert EDGE_CASE_PER_EVENT == 1
        assert EDGE_CASE_PER_EXTRA_FEATURE == 2

    def test_standard_categories_count(self) -> None:
        assert len(STANDARD_EDGE_CASE_CATEGORIES) == 6

    def test_standard_categories_members(self) -> None:
        expected = {
            "concurrency", "data_boundary", "state_machine",
            "ui_ux", "security", "data_migration",
        }
        assert set(STANDARD_EDGE_CASE_CATEGORIES) == expected

    def test_microservice_categories_count(self) -> None:
        assert len(MICROSERVICE_EDGE_CASE_CATEGORIES) == 6

    def test_microservice_categories_members(self) -> None:
        expected = {
            "service_unavailability", "network_partition",
            "eventual_consistency", "distributed_transaction",
            "version_skew", "data_ownership",
        }
        assert set(MICROSERVICE_EDGE_CASE_CATEGORIES) == expected

    def test_modular_monolith_extra(self) -> None:
        assert MODULAR_MONOLITH_EXTRA_CATEGORIES == (
            "interface_contract_violation",
        )


class TestSeverityMatrices:
    def test_microservice_matrix_uses_singular_async_event(self) -> None:
        for key in SEVERITY_MATRIX_MICROSERVICE:
            _, pattern = key
            assert pattern != "async-events", (
                "Must use async-event (singular)"
            )

    def test_microservice_required_sync_rest_is_critical(self) -> None:
        assert SEVERITY_MATRIX_MICROSERVICE[(True, "sync-rest")] == "critical"

    def test_microservice_optional_async_event_is_medium(self) -> None:
        assert SEVERITY_MATRIX_MICROSERVICE[(False, "async-event")] == "medium"

    def test_monolith_matrix_keys_are_standard_categories(self) -> None:
        for key in SEVERITY_MATRIX_MONOLITH:
            assert key in STANDARD_EDGE_CASE_CATEGORIES

    def test_monolith_security_is_high(self) -> None:
        assert SEVERITY_MATRIX_MONOLITH["security"] == "high"

    def test_severity_defaults(self) -> None:
        assert SEVERITY_DEFAULT_REQUIRED == "high"
        assert SEVERITY_DEFAULT_OPTIONAL == "medium"
        assert SEVERITY_DATA_OWNERSHIP == "high"
        assert SEVERITY_INTERFACE_CONTRACT == "high"


class TestEdgeCaseCategoryPriority:
    def test_has_13_entries(self) -> None:
        assert len(EDGE_CASE_CATEGORY_PRIORITY) == 13

    def test_includes_interface_contract_violation(self) -> None:
        assert "interface_contract_violation" in EDGE_CASE_CATEGORY_PRIORITY

    def test_service_unavailability_is_highest(self) -> None:
        assert EDGE_CASE_CATEGORY_PRIORITY["service_unavailability"] == 1

    def test_data_migration_is_lowest(self) -> None:
        assert EDGE_CASE_CATEGORY_PRIORITY["data_migration"] == 13

    def test_all_categories_covered(self) -> None:
        all_cats = (
            set(STANDARD_EDGE_CASE_CATEGORIES)
            | set(MICROSERVICE_EDGE_CASE_CATEGORIES)
            | set(MODULAR_MONOLITH_EXTRA_CATEGORIES)
        )
        assert set(EDGE_CASE_CATEGORY_PRIORITY.keys()) == all_cats
