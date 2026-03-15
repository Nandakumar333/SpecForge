"""PromptContextBuilder — assembles governance context string for sub-agents."""

from __future__ import annotations

from specforge.core.prompt_models import PromptSet


class PromptContextBuilder:
    """Builds a single context string from all governance files in a PromptSet."""

    @staticmethod
    def build(prompt_set: PromptSet, task_domain: str | None = None) -> str:
        """Concatenate all governance files' raw_content in precedence order.

        If *task_domain* matches a domain in the prompt set, that domain's
        content is placed first, followed by the remaining domains in
        ``prompt_set.precedence`` order (skipping the already-emitted domain).
        An unrecognised *task_domain* is silently ignored and the default
        precedence order is used.
        """
        order: list[str] = list(prompt_set.precedence)

        if task_domain and task_domain in prompt_set.files:
            order = [task_domain] + [d for d in order if d != task_domain]

        parts: list[str] = []
        for domain in order:
            pf = prompt_set.files.get(domain)
            if pf is not None:
                parts.append(pf.raw_content)

        return "\n".join(parts)
