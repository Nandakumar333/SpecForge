"""SharedInfraExecutor — cross-service infrastructure task executor."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import (
    EXECUTION_STATE_FILENAME,
    FEATURES_DIR,
    MANIFEST_PATH,
)
from specforge.core.execution_state import (
    create_initial_state,
    get_next_pending_task,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    save_state,
)
from specforge.core.executor_models import (
    ExecutionMode,
    ExecutionState,
    ImplementPrompt,
)
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.context_builder import ContextBuilder
    from specforge.core.task_runner import TaskRunner

logger = logging.getLogger(__name__)

_TASK_RE = re.compile(r"^- \[[ Xx]\]\s+(T\d+)\s+(.+)$", re.MULTILINE)

_VALID_ARCHITECTURES = frozenset({"microservice", "modular-monolith"})

_INFRA_SLUG = "cross-service-infra"


class SharedInfraExecutor:
    """Orchestrates implementation for cross-service shared infrastructure."""

    def __init__(
        self,
        context_builder: ContextBuilder,
        task_runner: TaskRunner,
        quality_checker_factory: callable,
        auto_fix_loop: object | None,
        project_root: Path,
    ) -> None:
        self._ctx_builder = context_builder
        self._runner = task_runner
        self._qc_factory = quality_checker_factory
        self._auto_fix = auto_fix_loop
        self._root = project_root

    def execute(
        self,
        mode: ExecutionMode,
    ) -> Result[ExecutionState, str]:
        """Execute shared infrastructure tasks.

        1. Load manifest and validate architecture.
        2. Locate cross-service-infra/tasks.md.
        3. Build context and process tasks.
        4. Mark shared_infra_complete on state.
        """
        manifest_result = self._load_manifest()
        if not manifest_result.ok:
            return manifest_result
        manifest = manifest_result.value

        arch = manifest.get("architecture", "monolithic")
        if arch not in _VALID_ARCHITECTURES:
            return Err(
                f"Shared infrastructure requires microservice or modular-monolith "
                f"architecture, got '{arch}'. Monolithic projects do not need "
                f"cross-service infrastructure.",
            )

        feature_dir = self._root / FEATURES_DIR / _INFRA_SLUG
        tasks_path = feature_dir / "tasks.md"
        if not tasks_path.exists():
            return Err(
                f"Shared infrastructure tasks not found: {tasks_path}. "
                f"Run the spec pipeline for cross-service-infra first.",
            )

        svc_ctx = self._build_infra_context(manifest)

        return self._run_tasks(svc_ctx, arch, mode, feature_dir)

    # ── Private helpers ─────────────────────────────────────────────

    def _run_tasks(
        self,
        svc_ctx: object,
        arch: str,
        mode: ExecutionMode,
        feature_dir: Path,
    ) -> Result[ExecutionState, str]:
        """Execute the task loop for shared infrastructure."""
        state_path = feature_dir / EXECUTION_STATE_FILENAME
        tasks_md = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        task_ids = tuple(m.group(1) for m in _TASK_RE.finditer(tasks_md))
        task_descs = {m.group(1): m.group(2) for m in _TASK_RE.finditer(tasks_md)}

        if not task_ids:
            return Err("No tasks found in cross-service-infra/tasks.md")

        state = create_initial_state(_INFRA_SLUG, arch, mode, task_ids)
        checker = self._qc_factory(self._root, _INFRA_SLUG)

        while True:
            next_id = get_next_pending_task(state)
            if next_id is None:
                break

            task_desc = task_descs.get(next_id, next_id)
            state = mark_task_in_progress(state, next_id)
            save_state(state_path, state)

            task_item = self._make_task_item(next_id, task_desc)
            ctx_result = self._ctx_builder.build(svc_ctx, task_item)
            if not ctx_result.ok:
                state = mark_task_failed(state, next_id, ctx_result.error, ())
                save_state(state_path, state)
                return Err(
                    f"Context build failed for {next_id}: {ctx_result.error}",
                )

            prompt = self._build_prompt(ctx_result.value, task_item)
            run_result = self._runner.run(prompt, mode)

            if not run_result.ok:
                state = mark_task_failed(state, next_id, run_result.error, ())
                save_state(state_path, state)
                return Err(f"Task {next_id} failed: {run_result.error}")

            changed_files = run_result.value
            if not changed_files:
                idx = next(
                    i for i, t in enumerate(state.tasks) if t.task_id == next_id
                )
                tasks_list = list(state.tasks)
                tasks_list[idx] = replace(tasks_list[idx], status="skipped")
                state = replace(state, tasks=tuple(tasks_list))
                save_state(state_path, state)
                continue

            qc_result = checker.check(changed_files)
            if qc_result.ok and qc_result.value.passed:
                sha = self._git_commit(next_id, task_desc)
                state = mark_task_completed(state, next_id, sha or "no-sha")
                save_state(state_path, state)
            elif self._auto_fix is not None:
                fix_result = self._auto_fix.fix(
                    prompt, qc_result.value, changed_files, mode,
                )
                if fix_result.ok:
                    sha = self._git_commit(next_id, task_desc)
                    state = mark_task_completed(state, next_id, sha or "no-sha")
                else:
                    state = mark_task_failed(
                        state, next_id, fix_result.error, (),
                    )
                    save_state(state_path, state)
                    return Err(f"Auto-fix exhausted for {next_id}")
                save_state(state_path, state)
            else:
                sha = self._git_commit(next_id, task_desc)
                state = mark_task_completed(state, next_id, sha or "no-sha")
                save_state(state_path, state)

        state = replace(state, shared_infra_complete=True)
        save_state(state_path, state)
        return Ok(state)

    def _load_manifest(self) -> Result[dict, str]:
        """Load the project manifest."""
        path = self._root / MANIFEST_PATH
        if not path.exists():
            return Err(f"Manifest not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Ok(data)
        except (json.JSONDecodeError, OSError) as exc:
            return Err(f"Invalid manifest: {exc}")

    def _build_infra_context(self, manifest: dict) -> object:
        """Create a synthetic ServiceContext for cross-service infrastructure."""
        from specforge.core.service_context import ServiceContext

        return ServiceContext(
            service_slug=_INFRA_SLUG,
            service_name="Shared Infrastructure",
            architecture=manifest.get("architecture", "monolithic"),
            project_description=manifest.get("project_description", ""),
            domain=manifest.get("domain", ""),
            features=(),
            dependencies=(),
            events=(),
            output_dir=self._root / FEATURES_DIR / _INFRA_SLUG,
        )

    def _make_task_item(self, task_id: str, desc: str) -> object:
        """Create a minimal TaskItem for ContextBuilder."""
        from specforge.core.task_models import TaskItem

        return TaskItem(
            id=task_id,
            description=desc,
            phase=1,
            layer="infrastructure",
            dependencies=(),
            parallel=False,
            effort="M",
            user_story="",
            file_paths=(),
            service_scope=_INFRA_SLUG,
            governance_rules=(),
            commit_message=f"feat({_INFRA_SLUG}): {desc}",
        )

    def _build_prompt(self, ctx: object, task_item: object) -> ImplementPrompt:
        """Build an ImplementPrompt from ExecutionContext."""
        return ImplementPrompt(
            system_context=(
                f"{ctx.constitution}\n\n"
                f"{ctx.governance_prompts}\n\n"
                f"{ctx.architecture_prompts}"
            ),
            task_description=ctx.current_task,
            file_hints=task_item.file_paths,
            dependency_context="\n".join(
                f"## {k}\n{v}" for k, v in ctx.dependency_contracts.items()
            ),
        )

    def _git_commit(self, task_id: str, desc: str) -> str | None:
        """Create a conventional commit for the infra task."""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self._root), capture_output=True, timeout=10,
            )
            msg = f"feat({_INFRA_SLUG}): {desc} [{task_id}]"
            result = subprocess.run(
                ["git", "commit", "-m", msg, "--allow-empty"],
                cwd=str(self._root), capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                sha_result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(self._root),
                    capture_output=True, text=True, timeout=5,
                )
                return sha_result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Git commit failed: %s", exc)
        return None
