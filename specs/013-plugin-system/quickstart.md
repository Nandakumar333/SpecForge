# Quickstart: Plugin System for Multi-Agent and Multi-Stack Support

**Feature**: 013-plugin-system | **Date**: 2026-03-18

## Using Built-in Plugins

### Stack + Architecture Initialization

```bash
# Python microservice project
specforge init my-api --stack python --arch microservice --agent claude

# .NET monolith project
specforge init my-app --stack dotnet --arch monolithic --agent copilot

# Node.js with auto-detected agent
specforge init my-service --stack nodejs --arch microservice
```

### What Gets Generated

For `specforge init my-api --stack python --arch microservice --agent claude`:

```text
my-api/
├── CLAUDE.md                          # Agent config (Claude-specific)
├── .specforge/
│   ├── config.json                    # Project metadata
│   ├── prompts/
│   │   ├── architecture.prompts.md    # Base architecture rules
│   │   ├── backend.python.prompts.md  # Python base + microservice override rules
│   │   ├── database.prompts.md        # Database rules
│   │   ├── security.prompts.md        # Security rules
│   │   ├── testing.python.prompts.md  # Python testing rules
│   │   ├── frontend.prompts.md        # Frontend rules
│   │   └── cicd.prompts.md            # CI/CD rules
│   └── ...
└── ...
```

### List Available Plugins

```bash
specforge plugins list
```

Output:
```text
Stack Plugins:
  dotnet    .NET (C#/F#) — microservice, monolithic, modular-monolith
  nodejs    Node.js/TypeScript — microservice, monolithic, modular-monolith
  python    Python — microservice, monolithic, modular-monolith

Agent Plugins:
  claude    Claude Code → CLAUDE.md
  copilot   GitHub Copilot → .github/copilot-instructions.md + .github/prompts/
  cursor    Cursor → .cursorrules
  gemini    Gemini CLI → .gemini/
  windsurf  Windsurf → .windsurfrules
  ... (25+ agents)
  generic   Generic fallback → user-specified directory
```

## Creating a Custom Stack Plugin

### Step 1: Create Plugin File

Create `.specforge/plugins/stacks/rails_plugin.py`:

```python
from specforge.plugins.stack_plugin_base import StackPlugin
from specforge.plugins.stack_plugin_base import PluginRule


class RailsPlugin(StackPlugin):
    @property
    def plugin_name(self) -> str:
        return "rails"

    @property
    def description(self) -> str:
        return "Ruby on Rails"

    @property
    def supported_architectures(self) -> list[str]:
        return ["monolithic", "modular-monolith"]

    def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
        rules = {
            "backend": [
                PluginRule(
                    rule_id="BACK-RAILS-001",
                    title="Convention Over Configuration",
                    severity="ERROR",
                    scope="all Rails controllers and models",
                    description="Follow Rails naming conventions. "
                    "Controllers MUST be plural, models singular.",
                    thresholds={"max_controller_actions": "7"},
                    example_correct="class OrdersController < ApplicationController",
                    example_incorrect="class OrderController < ApplicationController",
                ),
            ],
        }
        return rules

    def get_build_commands(self, arch: str) -> list[str]:
        return ["bundle install", "rails db:migrate"]

    def get_docker_config(self, arch: str):
        return None

    def get_test_commands(self) -> list[str]:
        return ["bundle exec rspec"]

    def get_folder_structure(self, arch: str) -> dict[str, str]:
        return {
            "app/models/": "ActiveRecord models",
            "app/controllers/": "Action controllers",
            "app/services/": "Service objects",
        }
```

### Step 2: Use It

```bash
specforge init my-rails-app --stack rails --arch monolithic
```

The system discovers `rails_plugin.py`, loads `RailsPlugin`, and generates governance files with Rails-specific rules.
