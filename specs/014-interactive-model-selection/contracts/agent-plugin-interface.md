# Contract: AgentPlugin Base Class Extension

**Feature**: 014-interactive-model-selection
**Type**: Internal Python interface (abstract base class)

## Current Interface (base.py)

```python
class AgentPlugin(ABC):
    @abstractmethod
    def agent_name(self) -> str: ...

    @abstractmethod
    def generate_config(self, target_dir: Path, context: dict[str, Any]) -> list[Path]: ...

    @abstractmethod
    def config_files(self) -> list[str]: ...
```

## Extended Interface

```python
class AgentPlugin(ABC):
    # Existing (unchanged)
    @abstractmethod
    def agent_name(self) -> str: ...

    @abstractmethod
    def generate_config(self, target_dir: Path, context: dict[str, Any]) -> list[Path]: ...

    @abstractmethod
    def config_files(self) -> list[str]: ...

    # NEW — commands directory support
    @property
    def commands_dir(self) -> str:
        """Agent-native commands directory path relative to project root.

        Override in subclasses for agent-specific locations.
        Default: '.specforge/commands'
        """
        return ".specforge/commands"

    @property
    def command_format(self) -> str:
        """Output format for command files: 'markdown' or 'toml'.

        Default: 'markdown'
        """
        return "markdown"

    @property
    def command_extension(self) -> str:
        """File extension for command files (including dot).

        Default: '.md'
        """
        return ".md"

    @property
    def args_placeholder(self) -> str:
        """Agent-native argument placeholder string.

        Default: '$ARGUMENTS'
        """
        return "$ARGUMENTS"
```

## Design Decision: Concrete defaults, not abstract

New properties use **concrete default implementations** (not `@abstractmethod`) to avoid
breaking all 25 existing plugin subclasses. Only agents with non-default values override.

## Override Map

| Plugin | `commands_dir` | `command_format` | `command_extension` | `args_placeholder` |
|--------|---------------|-----------------|--------------------|--------------------|
| ClaudePlugin | `.claude/commands` | default | default | default |
| CopilotPlugin | `.github/prompts` | default | `.prompt.md` | default |
| GeminiPlugin | `.gemini/commands` | `toml` | `.toml` | default |
| CursorPlugin | `.cursor/commands` | default | default | default |
| WindsurfPlugin | `.windsurf/commands` | default | default | default |
| CodexPlugin | `.codex/commands` | default | default | default |
| KiroPlugin | `.kiro/commands` | default | default | default |
| RoocodePlugin | `.roo/commands` | default | default | default |
| AmpPlugin | `.amp/commands` | default | default | default |
| AntigravityPlugin | `.agy/commands` | default | default | default |
| BobPlugin | `.bob/commands` | default | default | default |
| KilocodePlugin | `.kilocode/commands` | default | default | default |
| TraePlugin | `.trae/commands` | default | default | default |
| GenericPlugin | user-supplied or `commands` | default | default | default |
| *[single-file agents without dir]* | `.specforge/commands` | default | default | default |
