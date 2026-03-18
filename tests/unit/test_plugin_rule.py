"""Unit tests for PluginRule and DockerConfig frozen dataclasses."""

from __future__ import annotations

import pytest

from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule


# ── PluginRule Tests ─────────────────────────────────────────────────


class TestPluginRuleConstruction:
    """Valid PluginRule creation."""

    def test_basic_creation(self) -> None:
        rule = PluginRule(
            rule_id="BACK-DOTNET-MS-001",
            title="Per-Service DbContext Isolation",
            severity="ERROR",
            scope="all EF Core DbContext classes",
            description="Each service MUST own a single DbContext.",
            thresholds={"max_dbcontexts_per_service": "1"},
            example_correct="public class OrderDbContext : DbContext { }",
            example_incorrect="public class SharedDbContext : DbContext { }",
        )
        assert rule.rule_id == "BACK-DOTNET-MS-001"
        assert rule.severity == "ERROR"

    def test_warning_severity(self) -> None:
        rule = PluginRule(
            rule_id="BACK-001",
            title="Naming Convention",
            severity="WARNING",
            scope="all classes",
            description="Classes SHOULD follow naming convention.",
            thresholds={},
            example_correct="class OrderService { }",
            example_incorrect="class orderservice { }",
        )
        assert rule.severity == "WARNING"

    def test_empty_thresholds_allowed(self) -> None:
        rule = PluginRule(
            rule_id="SEC-001",
            title="Auth Required",
            severity="ERROR",
            scope="all endpoints",
            description="Every endpoint MUST require authentication.",
            thresholds={},
            example_correct="[Authorize] public class Api { }",
            example_incorrect="public class Api { }",
        )
        assert rule.thresholds == {}

    def test_multiple_thresholds(self) -> None:
        rule = PluginRule(
            rule_id="BACK-002",
            title="Method Length",
            severity="WARNING",
            scope="all methods",
            description="Methods SHOULD be short.",
            thresholds={"max_lines": "30", "max_params": "5"},
            example_correct="def short(): pass",
            example_incorrect="def long(): ...",
        )
        assert len(rule.thresholds) == 2


class TestPluginRuleImmutability:
    """PluginRule is frozen — field assignment must raise."""

    def test_cannot_assign_rule_id(self) -> None:
        rule = PluginRule(
            rule_id="BACK-001",
            title="T",
            severity="ERROR",
            scope="s",
            description="d",
            thresholds={},
            example_correct="c",
            example_incorrect="i",
        )
        with pytest.raises(AttributeError):
            rule.rule_id = "CHANGED"  # type: ignore[misc]

    def test_cannot_assign_severity(self) -> None:
        rule = PluginRule(
            rule_id="BACK-001",
            title="T",
            severity="ERROR",
            scope="s",
            description="d",
            thresholds={},
            example_correct="c",
            example_incorrect="i",
        )
        with pytest.raises(AttributeError):
            rule.severity = "WARNING"  # type: ignore[misc]


class TestPluginRuleValidation:
    """__post_init__ validation."""

    def test_invalid_rule_id_pattern_lowercase(self) -> None:
        with pytest.raises(ValueError, match="rule_id"):
            PluginRule(
                rule_id="back-001",
                title="T",
                severity="ERROR",
                scope="s",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_invalid_rule_id_empty(self) -> None:
        with pytest.raises(ValueError, match="rule_id"):
            PluginRule(
                rule_id="",
                title="T",
                severity="ERROR",
                scope="s",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            PluginRule(
                rule_id="BACK-001",
                title="T",
                severity="INFO",
                scope="s",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="title"):
            PluginRule(
                rule_id="BACK-001",
                title="",
                severity="ERROR",
                scope="s",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_empty_scope_rejected(self) -> None:
        with pytest.raises(ValueError, match="scope"):
            PluginRule(
                rule_id="BACK-001",
                title="T",
                severity="ERROR",
                scope="",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValueError, match="description"):
            PluginRule(
                rule_id="BACK-001",
                title="T",
                severity="ERROR",
                scope="s",
                description="",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )

    def test_whitespace_only_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="title"):
            PluginRule(
                rule_id="BACK-001",
                title="   ",
                severity="ERROR",
                scope="s",
                description="d",
                thresholds={},
                example_correct="c",
                example_incorrect="i",
            )


class TestPluginRuleEquality:
    """Frozen dataclasses support equality by value."""

    def test_equal_rules(self) -> None:
        kwargs = dict(
            rule_id="BACK-001",
            title="T",
            severity="ERROR",
            scope="s",
            description="d",
            thresholds={},
            example_correct="c",
            example_incorrect="i",
        )
        assert PluginRule(**kwargs) == PluginRule(**kwargs)

    def test_different_rules(self) -> None:
        base = dict(
            rule_id="BACK-001",
            title="T",
            severity="ERROR",
            scope="s",
            description="d",
            thresholds={},
            example_correct="c",
            example_incorrect="i",
        )
        assert PluginRule(**base) != PluginRule(**{**base, "severity": "WARNING"})

    def test_repr_contains_rule_id(self) -> None:
        rule = PluginRule(
            rule_id="BACK-001",
            title="T",
            severity="ERROR",
            scope="s",
            description="d",
            thresholds={},
            example_correct="c",
            example_incorrect="i",
        )
        assert "BACK-001" in repr(rule)


# ── DockerConfig Tests ───────────────────────────────────────────────


class TestDockerConfigConstruction:
    """Valid DockerConfig creation."""

    def test_basic_creation(self) -> None:
        cfg = DockerConfig(
            base_image="mcr.microsoft.com/dotnet/aspnet:8.0",
            build_stages=("restore", "build", "publish"),
            exposed_ports=(80, 443),
        )
        assert cfg.base_image == "mcr.microsoft.com/dotnet/aspnet:8.0"
        assert cfg.build_stages == ("restore", "build", "publish")
        assert cfg.exposed_ports == (80, 443)

    def test_default_health_check_path(self) -> None:
        cfg = DockerConfig(
            base_image="node:20-slim",
            build_stages=("install", "build"),
            exposed_ports=(3000,),
        )
        assert cfg.health_check_path == "/health"

    def test_custom_health_check_path(self) -> None:
        cfg = DockerConfig(
            base_image="python:3.12-slim",
            build_stages=("install",),
            exposed_ports=(8000,),
            health_check_path="/api/healthz",
        )
        assert cfg.health_check_path == "/api/healthz"

    def test_empty_ports(self) -> None:
        cfg = DockerConfig(
            base_image="alpine:3.19",
            build_stages=("build",),
            exposed_ports=(),
        )
        assert cfg.exposed_ports == ()


class TestDockerConfigImmutability:
    """DockerConfig is frozen."""

    def test_cannot_assign_base_image(self) -> None:
        cfg = DockerConfig(
            base_image="node:20",
            build_stages=("build",),
            exposed_ports=(3000,),
        )
        with pytest.raises(AttributeError):
            cfg.base_image = "node:22"  # type: ignore[misc]


class TestDockerConfigEquality:
    """Frozen dataclasses support equality by value."""

    def test_equal_configs(self) -> None:
        kwargs = dict(
            base_image="node:20",
            build_stages=("build",),
            exposed_ports=(3000,),
        )
        assert DockerConfig(**kwargs) == DockerConfig(**kwargs)

    def test_different_configs(self) -> None:
        base = dict(
            base_image="node:20",
            build_stages=("build",),
            exposed_ports=(3000,),
        )
        assert DockerConfig(**base) != DockerConfig(**{**base, "base_image": "node:22"})

    def test_repr_contains_base_image(self) -> None:
        cfg = DockerConfig(
            base_image="node:20",
            build_stages=("build",),
            exposed_ports=(3000,),
        )
        assert "node:20" in repr(cfg)
