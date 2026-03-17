"""SubAgentExecutor — main orchestrator per service."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import (
    EXECUTION_LOCK_FILENAME,
    EXECUTION_STATE_FILENAME,
    FEATURES_DIR,
    MANIFEST_PATH,
)
from specforge.core.execution_state import (
    create_initial_state,
    get_next_pending_task,
    load_state,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    save_state,
    validate_against_tasks,
)
from specforge.core.executor_models import (
    ExecutionMode,
    ExecutionState,
    ImplementPrompt,
)
from specforge.core.pipeline_lock import acquire_lock, release_lock
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.context_builder import ContextBuilder
    from specforge.core.task_runner import TaskRunner

logger = logging.getLogger(__name__)

_TASK_RE = re.compile(r"^- \[[ Xx]\]\s+(T\d+)\s+(.+)$", re.MULTILINE)


class SubAgentExecutor:
    """Orchestrates implementation for a single service."""

    def __init__(
        self,
        context_builder: ContextBuilder,
        task_runner: TaskRunner,
        quality_checker_factory: callable,
        auto_fix_loop: object | None,
        docker_manager: object | None,
        project_root: Path,
    ) -> None:
        self._ctx_builder = context_builder
        self._runner = task_runner
        self._qc_factory = quality_checker_factory
        self._auto_fix = auto_fix_loop
        self._docker = docker_manager
        self._root = project_root

    def execute(
        self,
        service_slug: str,
        mode: ExecutionMode,
        resume: bool = False,
    ) -> Result[ExecutionState, str]:
        """Execute implementation for a service."""
        manifest_result = self._load_manifest()
        if not manifest_result.ok:
            return manifest_result
        manifest = manifest_result.value

        svc_ctx_result = self._resolve_service(manifest, service_slug)
        if not svc_ctx_result.ok:
            return svc_ctx_result
        svc_ctx = svc_ctx_result.value

        artifacts_ok = self._validate_artifacts(service_slug)
        if not artifacts_ok.ok:
            return artifacts_ok

        feature_dir = self._root / FEATURES_DIR / service_slug
        lock_path = feature_dir / EXECUTION_LOCK_FILENAME
        lock_result = acquire_lock(lock_path, service_slug)
        if not lock_result.ok:
            return lock_result

        try:
            result = self._run_tasks(
                svc_ctx, service_slug, mode, resume, feature_dir,
            )
            if result.ok:
                self._print_summary(result.value)
            return result
        finally:
            release_lock(lock_path)

    def _run_tasks(
        self, svc_ctx, service_slug: str, mode: ExecutionMode,
        resume: bool, feature_dir: Path,
    ) -> Result[ExecutionState, str]:
        """Execute task loop."""
        state_path = feature_dir / EXECUTION_STATE_FILENAME
        arch = svc_ctx.architecture
        tasks_md = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        task_ids = tuple(m.group(1) for m in _TASK_RE.finditer(tasks_md))
        task_descs = {m.group(1): m.group(2) for m in _TASK_RE.finditer(tasks_md)}

        if not task_ids:
            return Err("No tasks found in tasks.md")

        state = self._load_or_create_state(
            state_path, service_slug, arch, mode, task_ids, resume,
        )

        checker = self._qc_factory(self._root, service_slug)

        while True:
            next_id = get_next_pending_task(state)
            if next_id is None:
                break

            task_desc = task_descs.get(next_id, next_id)
            state = mark_task_in_progress(state, next_id)
            save_state(state_path, state)

            task_item = self._make_task_item(next_id, task_desc, service_slug)
            ctx_result = self._ctx_builder.build(svc_ctx, task_item)
            if not ctx_result.ok:
                state = mark_task_failed(state, next_id, ctx_result.error, ())
                save_state(state_path, state)
                return Err(f"Context build failed for {next_id}: {ctx_result.error}")

            prompt = self._build_prompt(ctx_result.value, task_item)
            run_result = self._runner.run(prompt, mode)

            if not run_result.ok:
                state = mark_task_failed(state, next_id, run_result.error, ())
                save_state(state_path, state)
                return Err(f"Task {next_id} failed: {run_result.error}")

            changed_files = run_result.value
            if not changed_files:
                # Skipped task
                from dataclasses import replace as dc_replace
                idx = next(i for i, t in enumerate(state.tasks) if t.task_id == next_id)
                tasks_list = list(state.tasks)
                tasks_list[idx] = dc_replace(tasks_list[idx], status="skipped")
                state = dc_replace(state, tasks=tuple(tasks_list))
                save_state(state_path, state)
                continue

            qc_result = checker.check(changed_files)
            if qc_result.ok and qc_result.value.passed:
                sha = self._git_commit(service_slug, next_id, task_desc)
                state = mark_task_completed(state, next_id, sha or "no-sha")
                save_state(state_path, state)
            elif self._auto_fix is not None:
                fix_result = self._auto_fix.fix(
                    prompt, qc_result.value, changed_files, mode,
                )
                if fix_result.ok:
                    sha = self._git_commit(service_slug, next_id, task_desc)
                    state = mark_task_completed(state, next_id, sha or "no-sha")
                else:
                    state = mark_task_failed(
                        state, next_id, fix_result.error, (),
                    )
                    save_state(state_path, state)
                    return Err(f"Auto-fix exhausted for {next_id}")
                save_state(state_path, state)
            else:
                sha = self._git_commit(service_slug, next_id, task_desc)
                state = mark_task_completed(state, next_id, sha or "no-sha")
                save_state(state_path, state)

        # Post-task verification (microservice only)
        if arch == "microservice" and self._docker is not None:
            verification = self._run_verification(state_path, state)
            from dataclasses import replace as dc_replace
            state = dc_replace(state, verification=verification)
            save_state(state_path, state)

        return Ok(state)

    def _run_verification(self, state_path, state):
        """Run Docker verification for microservice services."""
        from specforge.core.executor_models import VerificationState

        errors: list[str] = []
        container_built = False
        health_ok = False
        contracts_ok = False
        compose_ok = False

        build_result = self._docker.build_image()
        if build_result.ok:
            container_built = True
        else:
            errors.append(f"Docker build: {build_result.error}")

        if container_built:
            hc_result = self._docker.health_check()
            if hc_result.ok:
                health_ok = True
            else:
                errors.append(f"Health check: {hc_result.error}")

            ct_result = self._docker.run_contract_tests()
            if ct_result.ok:
                contracts_ok = True
            else:
                errors.append(f"Contract tests: {ct_result.error}")

            reg_result = self._docker.register_in_compose()
            if reg_result.ok:
                compose_ok = True
            else:
                errors.append(f"Compose registration: {reg_result.error}")

        return VerificationState(
            container_built=container_built,
            health_check_passed=health_ok,
            contract_tests_passed=contracts_ok,
            compose_registered=compose_ok,
            errors=tuple(errors),
        )

    def _load_or_create_state(
        self, state_path, service_slug, arch, mode, task_ids, resume,
    ) -> ExecutionState:
        """Load existing state or create fresh."""
        from dataclasses import replace as dc_replace

        if resume:
            loaded = load_state(state_path)
            if loaded.ok and loaded.value is not None:
                state = validate_against_tasks(loaded.value, task_ids)
                # Reset in-progress tasks to pending (restart from scratch)
                tasks = tuple(
                    dc_replace(t, status="pending", attempt=1)
                    if t.status == "in-progress" else t
                    for t in state.tasks
                )
                return dc_replace(state, tasks=tasks)
        return create_initial_state(service_slug, arch, mode, task_ids)

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

    def _resolve_service(self, manifest, slug) -> Result:
        """Resolve service context from manifest."""
        from specforge.core.service_context import (
            FeatureInfo,
            ServiceContext,
            ServiceDependency,
        )

        services = manifest.get("services", [])
        svc_data = next((s for s in services if s["slug"] == slug), None)
        if svc_data is None:
            return Err(f"Service '{slug}' not found in manifest")

        deps = tuple(
            ServiceDependency(
                target_slug=c["target"],
                target_name=c.get("target", ""),
                pattern=c.get("pattern", "sync-rest"),
                required=c.get("required", True),
                description=c.get("description", ""),
            )
            for c in svc_data.get("communication", [])
        )

        features = tuple(
            FeatureInfo(
                id=f["id"],
                name=f.get("name", ""),
                display_name=f.get("name", ""),
                description=f.get("description", ""),
                priority=f.get("priority", "P1"),
                category=f.get("category", "core"),
            )
            for f in manifest.get("features", [])
            if f["id"] in svc_data.get("features", [])
        )

        return Ok(ServiceContext(
            service_slug=slug,
            service_name=svc_data.get("name", slug),
            architecture=manifest.get("architecture", "monolithic"),
            project_description=manifest.get("project_description", ""),
            domain=manifest.get("domain", ""),
            features=features,
            dependencies=deps,
            events=(),
            output_dir=self._root / "src" / slug,
        ))

    def _validate_artifacts(self, slug: str) -> Result:
        """Check that spec artifacts exist."""
        feature_dir = self._root / FEATURES_DIR / slug
        required = ("tasks.md",)
        for fname in required:
            if not (feature_dir / fname).exists():
                return Err(
                    f"Missing required artifact: {feature_dir / fname}. "
                    "Run the spec pipeline first.",
                )
        return Ok(True)

    def _make_task_item(self, task_id, desc, slug):
        """Create a minimal TaskItem for ContextBuilder."""
        from specforge.core.task_models import TaskItem

        return TaskItem(
            id=task_id,
            description=desc,
            phase=1,
            layer="service_layer",
            dependencies=(),
            parallel=False,
            effort="M",
            user_story="",
            file_paths=(),
            service_scope=slug,
            governance_rules=(),
            commit_message=f"feat({slug}): {desc}",
        )

    def _build_prompt(self, ctx, task_item) -> ImplementPrompt:
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

    def _git_commit(self, slug: str, task_id: str, desc: str) -> str | None:
        """Create a conventional commit for the task."""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self._root), capture_output=True, timeout=10,
            )
            msg = f"feat({slug}): {desc} [{task_id}]"
            result = subprocess.run(
                ["git", "commit", "-m", msg, "--allow-empty"],
                cwd=str(self._root), capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                sha_result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(self._root), capture_output=True, text=True, timeout=5,
                )
                return sha_result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Git commit failed: %s", exc)
        return None

    def _print_summary(self, state: ExecutionState) -> None:
        """Display Rich completion summary."""
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            completed = sum(1 for t in state.tasks if t.status == "completed")
            failed = sum(1 for t in state.tasks if t.status == "failed")
            skipped = sum(1 for t in state.tasks if t.status == "skipped")
            total = len(state.tasks)

            table = Table(title=f"Implementation: {state.service_slug}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Total tasks", str(total))
            table.add_row("Completed", str(completed))
            if failed:
                table.add_row("Failed", f"[red]{failed}[/red]")
            if skipped:
                table.add_row("Skipped", str(skipped))

            if state.verification:
                v = state.verification
                table.add_row("Docker build", "✓" if v.container_built else "✗")
                table.add_row("Health check", "✓" if v.health_check_passed else "✗")
                table.add_row("Contract tests", "✓" if v.contract_tests_passed else "✗")

            console.print(table)
        except ImportError:
            pass
