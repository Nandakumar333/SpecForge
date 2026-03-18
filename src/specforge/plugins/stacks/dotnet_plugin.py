"""DotnetPlugin — .NET stack plugin with architecture-aware rules."""

from __future__ import annotations

from specforge.core.config import VALID_ARCHITECTURES
from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule, StackPlugin
from specforge.plugins.stacks.dotnet_rules import (
    MICROSERVICE_BACKEND_RULES,
    MICROSERVICE_CICD_RULES,
    MICROSERVICE_DATABASE_RULES,
    MODULAR_MONOLITH_BACKEND_RULES,
    MONOLITH_BACKEND_RULES,
    MONOLITH_CICD_RULES,
    MONOLITH_DATABASE_RULES,
)


class DotnetPlugin(StackPlugin):
    """C#/.NET stack plugin providing architecture-specific governance rules."""

    @property
    def plugin_name(self) -> str:
        return "dotnet"

    @property
    def description(self) -> str:
        return (
            "C#/.NET stack plugin with architecture-aware governance "
            "rules for microservice, monolithic, and modular-monolith patterns."
        )

    @property
    def supported_architectures(self) -> list[str]:
        return list(VALID_ARCHITECTURES)

    # ── Rules ────────────────────────────────────────────────────────

    def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
        if arch == "microservice":
            return self._microservice_rules()
        if arch == "monolithic":
            return self._monolith_rules()
        if arch == "modular-monolith":
            return self._modular_monolith_rules()
        return {}

    def _microservice_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MICROSERVICE_BACKEND_RULES),
            "database": list(MICROSERVICE_DATABASE_RULES),
            "cicd": list(MICROSERVICE_CICD_RULES),
        }

    def _monolith_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MONOLITH_BACKEND_RULES),
            "database": list(MONOLITH_DATABASE_RULES),
            "cicd": list(MONOLITH_CICD_RULES),
        }

    def _modular_monolith_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MODULAR_MONOLITH_BACKEND_RULES),
            "database": list(MONOLITH_DATABASE_RULES),
            "cicd": list(MONOLITH_CICD_RULES),
        }

    # ── Docker ───────────────────────────────────────────────────────

    def get_docker_config(self, arch: str) -> DockerConfig | None:
        if arch == "microservice":
            return DockerConfig(
                base_image="mcr.microsoft.com/dotnet/aspnet:8.0",
                build_stages=("sdk", "publish", "runtime"),
                exposed_ports=(8080,),
            )
        return None

    # ── Build Commands ───────────────────────────────────────────────

    def get_build_commands(self, arch: str) -> list[str]:
        if arch == "microservice":
            return [
                "dotnet restore",
                "dotnet build --configuration Release",
                "dotnet publish --configuration Release --no-build",
            ]
        return [
            "dotnet restore",
            "dotnet build --configuration Release",
        ]

    # ── Test Commands ────────────────────────────────────────────────

    def get_test_commands(self) -> list[str]:
        return ["dotnet test"]

    # ── Folder Structure ─────────────────────────────────────────────

    def get_folder_structure(self, arch: str) -> dict[str, str]:
        if arch == "microservice":
            return self._microservice_folders()
        if arch == "modular-monolith":
            return self._modular_monolith_folders()
        return self._monolith_folders()

    def _microservice_folders(self) -> dict[str, str]:
        return {
            "src/Services/": "Individual microservice projects",
            "src/Contracts/": "Shared proto/contract definitions",
            "src/BuildingBlocks/": "Shared libraries and utilities",
            "tests/": "Test projects per service",
            "deploy/": "Deployment manifests and Dockerfiles",
        }

    def _monolith_folders(self) -> dict[str, str]:
        return {
            "src/App.Api/": "Web API entry point",
            "src/App.Application/": "Application layer (handlers, DTOs)",
            "src/App.Domain/": "Domain models and interfaces",
            "src/App.Infrastructure/": "Data access and external services",
            "tests/": "Unit and integration test projects",
        }

    def _modular_monolith_folders(self) -> dict[str, str]:
        return {
            "src/Modules/": "Feature modules with contracts",
            "src/App.Host/": "Composition root and startup",
            "src/App.SharedKernel/": "Shared domain primitives",
            "tests/": "Test projects per module",
        }
