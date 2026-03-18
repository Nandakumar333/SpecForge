"""Plugin system for multi-agent and multi-stack support."""

from specforge.plugins.agents.base import AgentPlugin
from specforge.plugins.plugin_manager import PluginManager
from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule, StackPlugin

__all__ = ["AgentPlugin", "DockerConfig", "PluginManager", "PluginRule", "StackPlugin"]
