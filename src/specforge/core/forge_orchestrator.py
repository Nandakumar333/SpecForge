"""ForgeOrchestrator — coordinates all forge stages (Feature 017)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import (
    FEATURES_DIR,
    FORGE_ARTIFACTS,
    FORGE_DEFAULT_WORKERS,
    FORGE_MAX_RETRIES,
    FORGE_PHASE_TO_FILENAME,
    FORGE_REPORT_DIR,
    FORGE_REPORT_FILE,
    FORGE_STATE_FILE,
    PIPELINE_PHASES,
)
from specforge.core.forge_state import ForgeState, ServiceForgeStatus
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.artifact_extractor import ArtifactExtractor
    from specforge.core.enriched_prompts import EnrichedPromptBuilder
    from specforge.core.forge_progress import ForgeProgress
    from specforge.core.llm_provider import LLMProvider
    from specforge.core.prompt_assembler import PromptAssembler

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceResult:
    """Result for a single service in the forge run."""

    slug: str
    status: str
    artifacts: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    error: str | None = None
    elapsed: float = 0.0


@dataclass(frozen=True)
class ForgeReport:
    """Complete forge run report data."""

    description: str
    architecture: str
    services: tuple[ServiceResult, ...] = ()
    total_elapsed: float = 0.0
    stage_timings: dict[str, float] = field(default_factory=dict)
    dry_run: bool = False
    prompt_files: tuple[str, ...] = ()
    estimated_tokens: int = 0

    @property
    def exit_code(self) -> int:
        if all(s.status == "complete" for s in self.services):
            return 0
        if all(s.status in ("failed", "permanently_failed") for s in self.services):
            return 2
        return 1


# Sentinel for state-exists detection
STATE_EXISTS = "STATE_EXISTS"


class ForgeOrchestrator:
    """Coordinates the full forge pipeline."""

    def __init__(
        self,
        project_dir: Path,
        llm_provider: LLMProvider,
        progress: ForgeProgress | None = None,
        enriched_builder: EnrichedPromptBuilder | None = None,
        artifact_extractor: ArtifactExtractor | None = None,
        assembler: PromptAssembler | None = None,
    ) -> None:
        self._project_dir = project_dir
        self._provider = llm_provider
        self._progress = progress
        self._enriched_builder = enriched_builder
        self._extractor = artifact_extractor
        self._assembler = assembler
        self._state_path = project_dir / ".specforge" / FORGE_STATE_FILE

    def run_forge(
        self,
        description: str,
        arch_type: str = "monolithic",
        stack: str = "auto",
        max_parallel: int = FORGE_DEFAULT_WORKERS,
        dry_run: bool = False,
        resume: bool = False,
        force: bool = False,
        skip_init: bool = False,
    ) -> Result[ForgeReport, str]:
        """Execute the full forge pipeline."""
        start = time.monotonic()
        timings: dict[str, float] = {}

        state = self._load_or_create_state(resume, force)
        if isinstance(state, str) and state == STATE_EXISTS:
            return Err(STATE_EXISTS)
        if isinstance(state, str):
            return Err(state)

        # Check skip_init before saving state (save creates .specforge/)
        if skip_init and not (self._project_dir / ".specforge").exists():
            return Err(
                "Project not initialized. Run 'specforge init' first "
                "or remove --skip-init."
            )

        state.description = description
        state.architecture = arch_type
        state.acquire_lock()
        state.save(self._state_path)

        try:
            return self._run_stages(
                state, description, arch_type, stack,
                max_parallel, dry_run, resume, skip_init,
                start, timings,
            )
        except KeyboardInterrupt:
            return self._handle_interrupt(state)
        finally:
            state.release_lock()
            state.save(self._state_path)

    def _run_stages(
        self,
        state: ForgeState,
        description: str,
        arch_type: str,
        stack: str,
        max_parallel: int,
        dry_run: bool,
        resume: bool,
        skip_init: bool,
        start: float,
        timings: dict[str, float],
    ) -> Result[ForgeReport, str]:
        """Execute stages in order, skipping completed ones on resume."""
        # Stage 1: Init
        if not resume or state.stage == "init":
            t0 = time.monotonic()
            result = self._init_stage(skip_init)
            if not result.ok:
                return Err(result.error)
            timings["init"] = time.monotonic() - t0
            state.update_stage("decompose")
            state.save(self._state_path)

        # Stage 2: Decompose
        if not resume or state.stage in ("init", "decompose"):
            t0 = time.monotonic()
            result = self._decompose_stage(description, arch_type)
            if not result.ok:
                return Err(result.error)
            service_slugs = result.value
            timings["decompose"] = time.monotonic() - t0
            self._register_services(state, service_slugs)
            state.update_stage("spec_generation")
            state.save(self._state_path)
        else:
            service_slugs = list(state.services.keys())

        if not service_slugs:
            return Err(
                "No services could be identified from the provided description."
            )

        # Stage 3: Spec generation (or dry-run prompt generation)
        t0 = time.monotonic()
        if dry_run:
            result = self._dry_run_stage(
                state, service_slugs, arch_type,
            )
        else:
            slugs_to_run = (
                state.incomplete_services() if resume else service_slugs
            )
            result = self._spec_generation_stage(
                state, slugs_to_run, arch_type, max_parallel,
            )
        if not result.ok:
            return Err(result.error)
        timings["spec_generation"] = time.monotonic() - t0
        state.update_stage("validation")
        state.save(self._state_path)

        # Stage 4: Validation
        if not dry_run:
            t0 = time.monotonic()
            self._validation_stage(service_slugs)
            timings["validation"] = time.monotonic() - t0

        # Stage 5: Report
        t0 = time.monotonic()
        total_elapsed = time.monotonic() - start
        report = self._report_stage(
            state, description, arch_type, total_elapsed, timings,
            dry_run,
        )
        timings["report"] = time.monotonic() - t0
        state.update_stage("report")
        state.save(self._state_path)
        return Ok(report)

    def _load_or_create_state(
        self, resume: bool, force: bool,
    ) -> ForgeState | str:
        """Load existing or create fresh state."""
        if not self._state_path.exists():
            return ForgeState.create()
        if force:
            return ForgeState.create()
        if resume:
            result = ForgeState.load(self._state_path)
            if result.ok:
                state = result.value
                for svc in state.services.values():
                    if svc.status == "failed":
                        svc.retry_count = 0
                        svc.status = "pending"
                return state
            return ForgeState.create()
        # State exists, no flags → signal caller
        return STATE_EXISTS

    def _init_stage(self, skip_init: bool) -> Result[None, str]:
        """Auto-initialize project if needed."""
        if self._progress:
            self._progress.update_stage("Initializing")
        specforge_dir = self._project_dir / ".specforge"
        if specforge_dir.exists():
            return Ok(None)
        if skip_init:
            return Err(
                "Project not initialized. Run 'specforge init' first "
                "or remove --skip-init."
            )
        return self._auto_init()

    def _auto_init(self) -> Result[None, str]:
        """Non-interactive init using auto-detected agent and stack."""
        try:
            from specforge.core.agent_detector import detect_agent
            from specforge.core.project import ProjectConfig
            from specforge.core.scaffold_builder import (
                build_scaffold_plan,
                generate_governance_files,
            )
            from specforge.core.scaffold_writer import write_scaffold
            from specforge.core.stack_detector import StackDetector

            detection = detect_agent()
            stack = StackDetector.detect(self._project_dir)
            config_result = ProjectConfig.create(
                name=self._project_dir.name,
                target_dir=self._project_dir,
                here=True,
                agent=detection.agent,
                stack=stack,
            )
            if not config_result.ok:
                return Err(config_result.error)
            plan_result = build_scaffold_plan(config_result.value)
            if not plan_result.ok:
                return Err(plan_result.error)
            write_result = write_scaffold(plan_result.value)
            if not write_result.ok:
                return Err(write_result.error)
            generate_governance_files(config_result.value)
            return Ok(None)
        except Exception as exc:
            return Err(f"Auto-init failed: {exc}")

    def _decompose_stage(
        self, description: str, arch_type: str,
    ) -> Result[list[str], str]:
        """LLM decompose → parse manifest → fallback to DomainAnalyzer."""
        if self._progress:
            self._progress.update_stage("Decomposing")

        manifest_path = self._project_dir / ".specforge" / "manifest.json"
        if manifest_path.exists():
            return self._load_existing_manifest(manifest_path)

        return self._llm_decompose(description, arch_type, manifest_path)

    def _load_existing_manifest(
        self, manifest_path: Path,
    ) -> Result[list[str], str]:
        """Load service slugs from existing manifest."""
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            slugs = [s["slug"] for s in data.get("services", [])]
            return Ok(slugs)
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            return Err(f"Invalid manifest.json: {exc}")

    def _llm_decompose(
        self,
        description: str,
        arch_type: str,
        manifest_path: Path,
    ) -> Result[list[str], str]:
        """Call LLM for decomposition, retry up to 3 times, fallback."""
        from specforge.core.phase_prompts import DECOMPOSE_PROMPT

        system = (
            f"{DECOMPOSE_PROMPT.clean_markdown_instruction}\n"
            f"{DECOMPOSE_PROMPT.system_instructions}\n"
            f"Architecture type: {arch_type}\n"
            f"{DECOMPOSE_PROMPT.skeleton}"
        )
        user = f"Decompose this application: {description}"

        for _attempt in range(FORGE_MAX_RETRIES):
            result = self._provider.call(system, user)
            if not result.ok:
                continue
            parsed = self._parse_decompose(result.value, arch_type)
            if parsed.ok:
                self._write_manifest(parsed.value, manifest_path)
                slugs = [s["slug"] for s in parsed.value.get("services", [])]
                self._ensure_feature_dirs(slugs)
                return Ok(slugs)

        return self._fallback_decompose(description, arch_type, manifest_path)

    def _parse_decompose(
        self, text: str, arch_type: str,
    ) -> Result[dict, str]:
        """Parse LLM decompose output as JSON, enforce arch_type."""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start < 0 or end <= start:
                return Err("No JSON object found in response")
            data = json.loads(text[start:end])
            data["architecture"] = arch_type
            return Ok(data)
        except json.JSONDecodeError as exc:
            return Err(f"Invalid JSON: {exc}")

    def _fallback_decompose(
        self,
        description: str,
        arch_type: str,
        manifest_path: Path,
    ) -> Result[list[str], str]:
        """Use DomainAnalyzer as fallback."""
        try:
            from specforge.core.domain_analyzer import DomainAnalyzer
            from specforge.core.domain_patterns import (
                DOMAIN_PATTERNS,
                GENERIC_PATTERN,
            )

            analyzer = DomainAnalyzer(DOMAIN_PATTERNS, GENERIC_PATTERN)
            domain_result = analyzer.analyze(description)
            if not domain_result.ok:
                return Err("Decompose failed: no services identified")
            features = analyzer.decompose(description, domain_result.value)
            if not features.ok or not features.value:
                return Err("Decompose failed: no features generated")
            manifest = self._features_to_manifest(
                features.value, arch_type, description,
            )
            self._write_manifest(manifest, manifest_path)
            slugs = [s["slug"] for s in manifest.get("services", [])]
            self._ensure_feature_dirs(slugs)
            return Ok(slugs)
        except Exception as exc:
            return Err(f"Fallback decompose failed: {exc}")

    def _features_to_manifest(
        self, features: list, arch_type: str, description: str,
    ) -> dict:
        """Convert DomainAnalyzer features to manifest format."""
        svc_map: dict[str, list] = {}
        feature_list = []
        for f in features:
            fdict = {
                "id": f.id, "name": f.name,
                "display_name": f.display_name,
                "description": f.description,
                "priority": f.priority, "category": f.category,
            }
            slug = f.name
            fdict["service"] = slug
            feature_list.append(fdict)
            svc_map.setdefault(slug, []).append(f.id)

        services = [
            {"name": slug.replace("-", " ").title(), "slug": slug,
             "features": ids, "rationale": "Auto-generated", "communication": []}
            for slug, ids in svc_map.items()
        ]
        return {
            "architecture": arch_type,
            "project_description": description,
            "features": feature_list,
            "services": services,
        }

    def _write_manifest(self, data: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _ensure_feature_dirs(self, slugs: list[str]) -> None:
        for slug in slugs:
            d = self._project_dir / FEATURES_DIR / slug
            d.mkdir(parents=True, exist_ok=True)

    def _register_services(
        self, state: ForgeState, slugs: list[str],
    ) -> None:
        for slug in slugs:
            if slug not in state.services:
                state.services[slug] = ServiceForgeStatus(slug=slug)

    def _spec_generation_stage(
        self,
        state: ForgeState,
        slugs: list[str],
        arch_type: str,
        max_parallel: int,
    ) -> Result[None, str]:
        """Run 7-phase pipeline for each service."""
        if self._progress:
            self._progress.update_stage("Generating Specs")
        total = len(slugs) * 7
        completed = 0
        for slug in slugs:
            svc = state.services.get(slug)
            if not svc or svc.status in ("complete", "permanently_failed"):
                continue
            result = self._run_service_pipeline(state, slug, arch_type)
            if result.ok:
                state.mark_service_complete(slug)
            else:
                state.mark_service_failed(slug, result.error)
                if svc.retry_count >= FORGE_MAX_RETRIES:
                    state.mark_service_permanently_failed(slug)
            completed += 7
            if self._progress:
                self._progress.advance_progress(
                    (7 / total) * 100 if total else 0,
                )
            state.save(self._state_path)
        return Ok(None)

    def _run_service_pipeline(
        self, state: ForgeState, slug: str, arch_type: str,
    ) -> Result[None, str]:
        """Run the 7-phase pipeline for a single service."""
        service_dir = self._project_dir / FEATURES_DIR / slug
        service_dir.mkdir(parents=True, exist_ok=True)
        svc = state.services[slug]
        start_phase = svc.last_completed_phase

        for i, phase in enumerate(PIPELINE_PHASES):
            if i < start_phase:
                continue
            if self._progress:
                self._progress.update_service(
                    slug, f"{phase} ({i+1}/7)", "running",
                )
            result = self._run_single_phase(
                slug, phase, service_dir, arch_type,
            )
            if not result.ok:
                if self._progress:
                    self._progress.update_service(slug, phase, "failed")
                return Err(result.error)
            state.mark_service_phase_complete(slug)
            state.save(self._state_path)

        if self._progress:
            self._progress.update_service(slug, "7/7", "complete")
        return Ok(None)

    def _run_single_phase(
        self, slug: str, phase: str, service_dir: Path, arch_type: str,
    ) -> Result[None, str]:
        """Generate a single artifact via LLM."""
        from specforge.core.architecture_adapter import create_adapter
        from specforge.core.phase_prompts import PHASE_PROMPTS
        from specforge.core.service_context import load_service_context

        phase_prompt = PHASE_PROMPTS.get(phase)
        if not phase_prompt:
            return Err(f"Unknown phase: {phase}")

        ctx_result = load_service_context(slug, self._project_dir)
        if not ctx_result.ok:
            return Err(ctx_result.error)
        service_ctx = ctx_result.value
        adapter = create_adapter(arch_type)

        prior = self._load_prior_artifacts(service_dir, phase)

        if self._assembler:
            asm_result = self._assembler.assemble(
                phase_prompt, service_ctx, adapter, prior,
            )
            if not asm_result.ok:
                return Err(asm_result.error)
            system_prompt, user_prompt = asm_result.value
        else:
            system_prompt = (
                f"{phase_prompt.clean_markdown_instruction}\n"
                f"{phase_prompt.system_instructions}\n"
                f"{phase_prompt.skeleton}"
            )
            user_prompt = (
                f"Generate {phase}.md for service: {slug}\n"
                f"Architecture: {arch_type}"
            )

        result = self._provider.call(system_prompt, user_prompt)
        if not result.ok:
            return Err(result.error)

        filename = FORGE_PHASE_TO_FILENAME.get(phase, f"{phase}.md")
        output_path = service_dir / filename
        output_path.write_text(result.value, encoding="utf-8")
        return Ok(None)

    def _load_prior_artifacts(
        self, service_dir: Path, current_phase: str,
    ) -> dict[str, str]:
        """Load completed artifacts as context for current phase."""
        artifacts: dict[str, str] = {}
        for phase in PIPELINE_PHASES:
            if phase == current_phase:
                break
            filename = FORGE_PHASE_TO_FILENAME.get(phase, f"{phase}.md")
            path = service_dir / filename
            if path.exists():
                artifacts[phase] = path.read_text(encoding="utf-8")
        return artifacts

    def _dry_run_stage(
        self,
        state: ForgeState,
        slugs: list[str],
        arch_type: str,
    ) -> Result[None, str]:
        """Generate .prompt.md files without LLM calls."""
        if self._progress:
            self._progress.update_stage("Dry Run — Generating Prompts")

        from specforge.core.architecture_adapter import create_adapter
        from specforge.core.config import FORGE_PROMPT_SUFFIX
        from specforge.core.phase_prompts import PHASE_PROMPTS
        from specforge.core.service_context import load_service_context

        prompt_files: list[str] = []
        total_tokens = 0

        for slug in slugs:
            service_dir = self._project_dir / FEATURES_DIR / slug
            service_dir.mkdir(parents=True, exist_ok=True)
            ctx_result = load_service_context(slug, self._project_dir)
            adapter = create_adapter(arch_type)
            prior: dict[str, str] = {}

            for phase in PIPELINE_PHASES:
                phase_prompt = PHASE_PROMPTS.get(phase)
                if not phase_prompt:
                    continue
                if self._assembler and ctx_result.ok:
                    asm_result = self._assembler.assemble(
                        phase_prompt, ctx_result.value, adapter, prior,
                    )
                    if asm_result.ok:
                        sys_p, user_p = asm_result.value
                        content = (
                            f"# System Prompt\n\n{sys_p}"
                            f"\n\n# User Prompt\n\n{user_p}"
                        )
                    else:
                        content = f"# {phase}\n\nAssembly failed: {asm_result.error}"
                else:
                    content = (
                        f"# {phase}\n\n"
                        f"{phase_prompt.system_instructions}\n\n"
                        f"{phase_prompt.skeleton}"
                    )
                filename = f"{phase}{FORGE_PROMPT_SUFFIX}"
                path = service_dir / filename
                path.write_text(content, encoding="utf-8")
                prompt_files.append(str(path))
                total_tokens += len(content) // 4

                if self._progress:
                    self._progress.update_service(slug, phase, "prompt")

        state.update_stage("report")
        return Ok(None)

    def _validation_stage(
        self, slugs: list[str],
    ) -> dict[str, list[str]]:
        """Verify all 7 artifacts exist per service."""
        if self._progress:
            self._progress.update_stage("Validating")
        missing_map: dict[str, list[str]] = {}
        for slug in slugs:
            service_dir = self._project_dir / FEATURES_DIR / slug
            missing = [
                a for a in FORGE_ARTIFACTS
                if not (service_dir / a).exists()
            ]
            if missing:
                missing_map[slug] = missing
        return missing_map

    def _report_stage(
        self,
        state: ForgeState,
        description: str,
        arch_type: str,
        total_elapsed: float,
        timings: dict[str, float],
        dry_run: bool = False,
    ) -> ForgeReport:
        """Generate forge report."""
        if self._progress:
            self._progress.update_stage("Generating Report")

        svc_results = []
        for slug, svc in state.services.items():
            service_dir = self._project_dir / FEATURES_DIR / slug
            found = tuple(
                a for a in FORGE_ARTIFACTS
                if (service_dir / a).exists()
            )
            missing = tuple(
                a for a in FORGE_ARTIFACTS
                if not (service_dir / a).exists()
            )
            svc_results.append(ServiceResult(
                slug=slug,
                status=svc.status,
                artifacts=found,
                missing=missing,
                error=svc.error,
            ))

        report = ForgeReport(
            description=description,
            architecture=arch_type,
            services=tuple(svc_results),
            total_elapsed=total_elapsed,
            stage_timings=timings,
            dry_run=dry_run,
        )

        self._write_report(report)
        return report

    def _write_report(self, report: ForgeReport) -> None:
        """Write forge-report.md."""
        report_dir = self._project_dir / ".specforge" / FORGE_REPORT_DIR
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / FORGE_REPORT_FILE

        lines = [
            "# Forge Report",
            "",
            f"**Description**: {report.description}",
            f"**Architecture**: {report.architecture}",
            f"**Total Time**: {report.total_elapsed:.1f}s",
            f"**Dry Run**: {report.dry_run}",
            "",
            "## Services",
            "",
            "| Service | Status | Artifacts | Missing |",
            "|---------|--------|-----------|---------|",
        ]
        for svc in report.services:
            lines.append(
                f"| {svc.slug} | {svc.status} | "
                f"{len(svc.artifacts)}/7 | "
                f"{', '.join(svc.missing) or 'none'} |"
            )

        failed = [s for s in report.services if s.error]
        if failed:
            lines.extend(["", "## Failed Services", ""])
            for svc in failed:
                lines.append(f"### {svc.slug}")
                lines.append(f"**Error**: {svc.error}")
                lines.append("")

        lines.extend(["", "## Timing", ""])
        for stage, duration in report.stage_timings.items():
            lines.append(f"- **{stage}**: {duration:.1f}s")

        path.write_text("\n".join(lines), encoding="utf-8")

    def _handle_interrupt(self, state: ForgeState) -> Result[ForgeReport, str]:
        """Handle Ctrl+C gracefully."""
        logger.info("Forge interrupted — saving state")
        state.release_lock()
        state.save(self._state_path)
        return Err("Forge interrupted. Resume with: specforge forge --resume")
