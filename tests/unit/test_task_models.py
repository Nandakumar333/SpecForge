"""Tests for Feature 008 task generation data models."""

from __future__ import annotations

import pytest


class TestEffortSize:
    """EffortSize literal type validation."""

    def test_valid_sizes(self) -> None:
        from specforge.core.task_models import EffortSize

        for size in ("S", "M", "L", "XL"):
            assert size in EffortSize.__args__

    def test_all_four_sizes_defined(self) -> None:
        from specforge.core.task_models import EffortSize

        assert len(EffortSize.__args__) == 4


class TestBuildStep:
    """BuildStep frozen dataclass tests."""

    def test_creation(self) -> None:
        from specforge.core.task_models import BuildStep

        step = BuildStep(
            order=1,
            category="scaffolding",
            description_template="Set up {service} project scaffold",
            default_effort="S",
            file_path_pattern="src/{service}/",
            depends_on=(),
            parallelizable_with=(),
        )
        assert step.order == 1
        assert step.category == "scaffolding"
        assert step.default_effort == "S"

    def test_immutability(self) -> None:
        from specforge.core.task_models import BuildStep

        step = BuildStep(
            order=1,
            category="scaffolding",
            description_template="Set up {service}",
            default_effort="S",
            file_path_pattern="src/{service}/",
            depends_on=(),
            parallelizable_with=(),
        )
        with pytest.raises(AttributeError):
            step.order = 2  # type: ignore[misc]

    def test_depends_on_tuple(self) -> None:
        from specforge.core.task_models import BuildStep

        step = BuildStep(
            order=5,
            category="service_layer",
            description_template="Implement service layer",
            default_effort="L",
            file_path_pattern="src/{service}/services/",
            depends_on=(3, 4),
            parallelizable_with=(6,),
        )
        assert step.depends_on == (3, 4)
        assert step.parallelizable_with == (6,)


class TestTaskItem:
    """TaskItem frozen dataclass tests."""

    def test_creation_all_fields(self) -> None:
        from specforge.core.task_models import TaskItem

        task = TaskItem(
            id="T001",
            description="Create Account entity",
            phase=1,
            layer="domain",
            dependencies=(),
            parallel=False,
            effort="S",
            user_story="US1",
            file_paths=("src/ledger/models/Account.cs",),
            service_scope="ledger-service",
            governance_rules=("ARCH-001",),
            commit_message="feat(ledger): add Account entity",
        )
        assert task.id == "T001"
        assert task.layer == "domain"
        assert task.effort == "S"
        assert task.governance_rules == ("ARCH-001",)

    def test_immutability(self) -> None:
        from specforge.core.task_models import TaskItem

        task = TaskItem(
            id="T001",
            description="Test",
            phase=1,
            layer="domain",
            dependencies=(),
            parallel=False,
            effort="S",
            user_story="US1",
            file_paths=(),
            service_scope="test",
            governance_rules=(),
            commit_message="feat: test",
        )
        with pytest.raises(AttributeError):
            task.id = "T002"  # type: ignore[misc]

    def test_external_dependency_format(self) -> None:
        from specforge.core.task_models import TaskItem

        task = TaskItem(
            id="T006",
            description="Create gRPC client",
            phase=6,
            layer="infrastructure",
            dependencies=("T005", "cross-service-infra/X-T001"),
            parallel=False,
            effort="M",
            user_story="US1",
            file_paths=(),
            service_scope="ledger-service",
            governance_rules=(),
            commit_message="feat(ledger): add grpc client",
        )
        assert "cross-service-infra/X-T001" in task.dependencies


class TestTaskFile:
    """TaskFile frozen dataclass tests."""

    def test_creation(self) -> None:
        from specforge.core.task_models import TaskFile, TaskItem

        t1 = TaskItem(
            id="T001", description="Setup", phase=1, layer="scaffolding",
            dependencies=(), parallel=False, effort="S", user_story="US1",
            file_paths=(), service_scope="svc", governance_rules=(),
            commit_message="feat: setup",
        )
        tf = TaskFile(
            target_name="ledger-service",
            architecture="microservice",
            tasks=(t1,),
            phases=((1, (t1,)),),
            total_count=1,
        )
        assert tf.target_name == "ledger-service"
        assert tf.total_count == 1
        assert len(tf.tasks) == 1

    def test_phase_grouping(self) -> None:
        from specforge.core.task_models import TaskFile, TaskItem

        t1 = TaskItem(
            id="T001", description="A", phase=1, layer="scaffolding",
            dependencies=(), parallel=False, effort="S", user_story="US1",
            file_paths=(), service_scope="svc", governance_rules=(),
            commit_message="feat: a",
        )
        t2 = TaskItem(
            id="T002", description="B", phase=2, layer="domain",
            dependencies=("T001",), parallel=False, effort="M",
            user_story="US1", file_paths=(), service_scope="svc",
            governance_rules=(), commit_message="feat: b",
        )
        tf = TaskFile(
            target_name="svc",
            architecture="microservice",
            tasks=(t1, t2),
            phases=((1, (t1,)), (2, (t2,))),
            total_count=2,
        )
        assert len(tf.phases) == 2
        assert tf.phases[0][0] == 1
        assert tf.phases[1][0] == 2


class TestDependencyGraph:
    """DependencyGraph dataclass tests."""

    def test_creation(self) -> None:
        from specforge.core.task_models import DependencyGraph

        graph = DependencyGraph(
            adjacency={"T001": (), "T002": ("T001",)},
            in_degree={"T001": 0, "T002": 1},
            tasks_by_id={},
            depth_levels={"T001": 0, "T002": 1},
        )
        assert graph.in_degree["T001"] == 0
        assert graph.in_degree["T002"] == 1
        assert graph.adjacency["T002"] == ("T001",)

    def test_mutable(self) -> None:
        from specforge.core.task_models import DependencyGraph

        graph = DependencyGraph(
            adjacency={}, in_degree={}, tasks_by_id={}, depth_levels={},
        )
        graph.adjacency["T001"] = ()
        graph.in_degree["T001"] = 0
        assert "T001" in graph.adjacency


class TestGenerationSummary:
    """GenerationSummary frozen dataclass tests."""

    def test_creation(self) -> None:
        from specforge.core.task_models import GenerationSummary

        summary = GenerationSummary(
            generated_files=("ledger-service/tasks.md",),
            task_counts={"ledger-service": 14},
            cross_dependencies=("cross-service-infra/X-T001",),
            warnings=(),
        )
        assert summary.generated_files == ("ledger-service/tasks.md",)
        assert summary.task_counts["ledger-service"] == 14

    def test_immutability(self) -> None:
        from specforge.core.task_models import GenerationSummary

        summary = GenerationSummary(
            generated_files=(), task_counts={}, cross_dependencies=(),
            warnings=(),
        )
        with pytest.raises(AttributeError):
            summary.generated_files = ("new",)  # type: ignore[misc]
