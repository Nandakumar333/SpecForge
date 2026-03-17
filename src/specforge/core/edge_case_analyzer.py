"""MicroserviceEdgeCaseAnalyzer — topology-aware edge case generation (Feature 007)."""

from __future__ import annotations

from specforge.core.config import (
    SEVERITY_DATA_OWNERSHIP,
    SEVERITY_DEFAULT_OPTIONAL,
    SEVERITY_DEFAULT_REQUIRED,
    SEVERITY_INTERFACE_CONTRACT,
    SEVERITY_MATRIX_MICROSERVICE,
    SEVERITY_MATRIX_MONOLITH,
    STANDARD_EDGE_CASE_CATEGORIES,
)
from specforge.core.edge_case_budget import EdgeCaseBudget
from specforge.core.edge_case_filter import ArchitectureEdgeCaseFilter
from specforge.core.edge_case_models import (
    EdgeCase,
    EdgeCasePattern,
    EdgeCaseReport,
    make_edge_case_id,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.service_context import (
    EventInfo,
    ServiceContext,
    ServiceDependency,
)


class EdgeCaseAnalyzer:
    """Generates architecture-aware edge cases from service topology."""

    def __init__(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        arch_filter: ArchitectureEdgeCaseFilter,
        budget: EdgeCaseBudget,
    ) -> None:
        self._patterns = patterns
        self._filter = arch_filter
        self._budget = budget

    def analyze(
        self,
        service_ctx: ServiceContext,
        manifest: dict | None = None,
    ) -> Result[EdgeCaseReport, str]:
        """Generate edge cases for a service based on its topology."""
        try:
            cases = self._generate_cases(service_ctx, manifest)
            numbered = self._apply_budget_and_number(
                cases, service_ctx,
            )
            return Ok(self._build_report(service_ctx, numbered))
        except Exception as e:
            return Err(f"Edge case analysis failed: {e}")

    def _generate_cases(
        self,
        ctx: ServiceContext,
        manifest: dict | None,
    ) -> list[EdgeCase]:
        """Dispatch to architecture-specific generation."""
        filtered = self._filter.filter_patterns(self._patterns)
        cases: list[EdgeCase] = []
        cases.extend(self._standard_cases(filtered, ctx))
        if ctx.architecture == "microservice":
            cases.extend(self._dependency_cases(filtered, ctx))
            cases.extend(self._event_cases(filtered, ctx))
            cases.extend(self._data_ownership_cases(ctx, manifest))
        elif ctx.architecture == "modular-monolith":
            cases.extend(self._interface_cases(filtered, ctx))
        cases.extend(self._feature_interaction_cases(ctx))
        return cases

    def _standard_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
    ) -> list[EdgeCase]:
        """Generate one edge case per standard category."""
        cases: list[EdgeCase] = []
        seen: set[str] = set()
        for p in patterns:
            if p.category not in STANDARD_EDGE_CASE_CATEGORIES:
                continue
            if p.category in seen:
                continue
            seen.add(p.category)
            severity = self._monolith_severity(p.category)
            cases.append(self._instantiate_standard(p, ctx, severity))
        return cases

    def _instantiate_standard(
        self,
        pattern: EdgeCasePattern,
        ctx: ServiceContext,
        severity: str,
    ) -> EdgeCase:
        """Create an EdgeCase from a standard-category pattern."""
        replacements = {
            "service": ctx.service_name,
            "resource": f"{ctx.domain} data",
            "feature_a": self._feature_name(ctx, 0),
            "feature_b": self._feature_name(ctx, 1),
        }
        return EdgeCase(
            id="",
            category=pattern.category,
            severity=severity,
            scenario=self._fill(pattern.scenario_template, replacements),
            trigger=self._fill(pattern.trigger_template, replacements),
            affected_services=(ctx.service_slug,),
            handling_strategy=", ".join(pattern.handling_strategies),
            test_suggestion=self._fill(
                pattern.test_template, replacements,
            ),
        )

    def _dependency_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
    ) -> list[EdgeCase]:
        """Generate edge cases per communication[] dependency."""
        cases: list[EdgeCase] = []
        seen_targets: set[str] = set()
        for dep in ctx.dependencies:
            if dep.target_slug in seen_targets:
                self._add_circular_dep_case(cases, ctx, dep.target_slug)
                continue
            seen_targets.add(dep.target_slug)
            cases.extend(self._cases_for_dep(patterns, ctx, dep))
        return cases

    def _cases_for_dep(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
        dep: ServiceDependency,
    ) -> list[EdgeCase]:
        """Generate matching pattern cases for a single dependency."""
        cases: list[EdgeCase] = []
        severity = self._dep_severity(dep.required, dep.pattern)
        replacements = self._dep_replacements(ctx, dep)
        dangling = self._is_dangling(dep, ctx)
        for p in patterns:
            if not self._pattern_applies(p, dep.pattern):
                continue
            if p.category in STANDARD_EDGE_CASE_CATEGORIES:
                continue
            if p.category in (
                "data_ownership",
                "interface_contract_violation",
            ):
                continue
            cases.append(
                self._instantiate_dep(p, replacements, severity, dangling),
            )
        return cases

    def _instantiate_dep(
        self,
        pattern: EdgeCasePattern,
        replacements: dict[str, str],
        severity: str,
        dangling: bool,
    ) -> EdgeCase:
        """Create an EdgeCase from a dep-specific pattern."""
        scenario = self._fill(pattern.scenario_template, replacements)
        if dangling:
            scenario += " (service not found in manifest)"
        return EdgeCase(
            id="",
            category=pattern.category,
            severity=severity,
            scenario=scenario,
            trigger=self._fill(pattern.trigger_template, replacements),
            affected_services=(
                replacements["source_service"],
                replacements["target_service"],
            ),
            handling_strategy=", ".join(pattern.handling_strategies),
            test_suggestion=self._fill(
                pattern.test_template, replacements,
            ),
        )

    def _event_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
    ) -> list[EdgeCase]:
        """Generate edge cases from events[] entries."""
        cases: list[EdgeCase] = []
        for event in ctx.events:
            if event.producer == ctx.service_slug:
                cases.extend(
                    self._producer_event_cases(patterns, ctx, event),
                )
            if ctx.service_slug in event.consumers:
                cases.extend(
                    self._consumer_event_cases(patterns, ctx, event),
                )
        return cases

    def _producer_event_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
        event: EventInfo,
    ) -> list[EdgeCase]:
        """Producer gets eventual_consistency per consumer + distributed_transaction."""
        cases: list[EdgeCase] = []
        ec_patterns = [
            p for p in patterns if p.category == "eventual_consistency"
        ]
        for consumer in event.consumers:
            if not ec_patterns:
                continue
            p = ec_patterns[0]
            repl = self._event_replacements(ctx, event, consumer)
            cases.append(self._instantiate_event(p, repl, "high"))
        if len(event.consumers) >= 2:
            dt_patterns = [
                p for p in patterns
                if p.category == "distributed_transaction"
            ]
            if dt_patterns:
                repl = self._event_replacements(
                    ctx, event, ", ".join(event.consumers),
                )
                cases.append(
                    self._instantiate_event(dt_patterns[0], repl, "high"),
                )
        return cases

    def _consumer_event_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
        event: EventInfo,
    ) -> list[EdgeCase]:
        """Consumer gets stale-data eventual_consistency case."""
        ec_patterns = [
            p for p in patterns if p.category == "eventual_consistency"
        ]
        if not ec_patterns or len(ec_patterns) < 2:
            return []
        p = ec_patterns[1] if len(ec_patterns) > 1 else ec_patterns[0]
        repl = self._event_replacements(ctx, event, ctx.service_slug)
        return [self._instantiate_event(p, repl, "medium")]

    def _instantiate_event(
        self,
        pattern: EdgeCasePattern,
        replacements: dict[str, str],
        severity: str,
    ) -> EdgeCase:
        """Create an EdgeCase from an event-specific pattern."""
        return EdgeCase(
            id="",
            category=pattern.category,
            severity=severity,
            scenario=self._fill(pattern.scenario_template, replacements),
            trigger=self._fill(pattern.trigger_template, replacements),
            affected_services=(
                replacements.get("producer_service", ""),
                replacements.get("consumer_service", ""),
            ),
            handling_strategy=", ".join(pattern.handling_strategies),
            test_suggestion=self._fill(
                pattern.test_template, replacements,
            ),
        )

    def _data_ownership_cases(
        self,
        ctx: ServiceContext,
        manifest: dict | None,
    ) -> list[EdgeCase]:
        """Generate data ownership conflict cases via BoundaryAnalyzer."""
        if manifest is None:
            return []
        try:
            from specforge.core.boundary_analyzer import BoundaryAnalyzer

            analyzer = BoundaryAnalyzer(manifest)
            matches = analyzer.analyze(ctx.service_slug)
            return [
                self._ownership_case(ctx, m.text) for m in matches
            ]
        except Exception:
            return []

    def _ownership_case(
        self,
        ctx: ServiceContext,
        entity: str,
    ) -> EdgeCase:
        """Create a data ownership edge case for a shared entity."""
        return EdgeCase(
            id="",
            category="data_ownership",
            severity=SEVERITY_DATA_OWNERSHIP,
            scenario=(
                f"Conflicting updates to shared entity '{entity}' "
                f"involving {ctx.service_slug}"
            ),
            trigger=f"Multiple services modify '{entity}' without clear ownership",
            affected_services=(ctx.service_slug,),
            handling_strategy="single_source_of_truth, event_sourcing",
            test_suggestion=(
                f"Integration test: concurrent update to '{entity}', "
                "verify conflict resolution"
            ),
        )

    def _interface_cases(
        self,
        patterns: tuple[EdgeCasePattern, ...],
        ctx: ServiceContext,
    ) -> list[EdgeCase]:
        """Generate interface_contract_violation cases for modular-monolith."""
        ic_patterns = [
            p for p in patterns
            if p.category == "interface_contract_violation"
        ]
        if not ic_patterns:
            return []
        p = ic_patterns[0]
        repl = {
            "source_service": ctx.service_name,
            "target_service": "dependent module",
        }
        return [
            EdgeCase(
                id="",
                category="interface_contract_violation",
                severity=SEVERITY_INTERFACE_CONTRACT,
                scenario=self._fill(p.scenario_template, repl),
                trigger=self._fill(p.trigger_template, repl),
                affected_services=(ctx.service_slug,),
                handling_strategy=", ".join(p.handling_strategies),
                test_suggestion=self._fill(p.test_template, repl),
            ),
        ]

    def _feature_interaction_cases(
        self,
        ctx: ServiceContext,
    ) -> list[EdgeCase]:
        """Generate cases for feature-interaction conflicts."""
        if len(ctx.features) <= 1:
            return []
        cases: list[EdgeCase] = []
        for i in range(1, len(ctx.features)):
            f1 = ctx.features[0]
            f2 = ctx.features[i]
            cases.append(
                EdgeCase(
                    id="",
                    category="concurrency",
                    severity="medium",
                    scenario=(
                        f"{f1.display_name} and {f2.display_name} "
                        f"compete for shared resources in {ctx.service_name}"
                    ),
                    trigger=(
                        f"Concurrent {f1.name} and {f2.name} operations "
                        "on overlapping data"
                    ),
                    affected_services=(ctx.service_slug,),
                    handling_strategy="lock_ordering, resource_partitioning",
                    test_suggestion=(
                        f"Integration test: trigger {f1.name} and "
                        f"{f2.name} simultaneously, verify no deadlock"
                    ),
                ),
            )
        return cases

    def _apply_budget_and_number(
        self,
        cases: list[EdgeCase],
        ctx: ServiceContext,
    ) -> tuple[EdgeCase, ...]:
        """Apply budget cap and assign sequential IDs."""
        events_count = self._count_event_roles(ctx)
        budget = self._budget.allocate(
            len(ctx.dependencies), events_count, len(ctx.features),
        )
        prioritized = self._budget.prioritize(tuple(cases), budget)
        return tuple(
            EdgeCase(
                id=make_edge_case_id(i + 1),
                category=c.category,
                severity=c.severity,
                scenario=c.scenario,
                trigger=c.trigger,
                affected_services=c.affected_services,
                handling_strategy=c.handling_strategy,
                test_suggestion=c.test_suggestion,
            )
            for i, c in enumerate(prioritized)
        )

    @staticmethod
    def _count_event_roles(ctx: ServiceContext) -> int:
        """Count event roles: producer roles + consumer roles."""
        count = 0
        for event in ctx.events:
            if event.producer == ctx.service_slug:
                count += 1
            if ctx.service_slug in event.consumers:
                count += 1
        return count

    @staticmethod
    def _build_report(
        ctx: ServiceContext,
        cases: tuple[EdgeCase, ...],
    ) -> EdgeCaseReport:
        """Build the final EdgeCaseReport."""
        return EdgeCaseReport(
            service_slug=ctx.service_slug,
            architecture=ctx.architecture,
            edge_cases=cases,
            total_count=len(cases),
        )

    @staticmethod
    def _dep_severity(required: bool, pattern: str) -> str:
        """Resolve severity from the microservice matrix."""
        key = (required, pattern)
        if key in SEVERITY_MATRIX_MICROSERVICE:
            return SEVERITY_MATRIX_MICROSERVICE[key]
        return SEVERITY_DEFAULT_REQUIRED if required else SEVERITY_DEFAULT_OPTIONAL

    @staticmethod
    def _monolith_severity(category: str) -> str:
        """Resolve severity from the monolith matrix."""
        return SEVERITY_MATRIX_MONOLITH.get(category, "medium")

    @staticmethod
    def _pattern_applies(
        pattern: EdgeCasePattern, comm_pattern: str,
    ) -> bool:
        """Check if a pattern applies to a communication pattern."""
        if not pattern.applicable_patterns:
            return True
        return comm_pattern in pattern.applicable_patterns

    @staticmethod
    def _is_dangling(dep: ServiceDependency, ctx: ServiceContext) -> bool:
        """Check if dependency target is not in known services."""
        # We detect dangling by checking if target_name equals target_slug
        # (name_map falls back to slug for unknown services)
        return dep.target_name == dep.target_slug

    @staticmethod
    def _fill(template: str, replacements: dict[str, str]) -> str:
        """Replace {{key}} placeholders in a template string."""
        result = template
        for key, value in replacements.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    @staticmethod
    def _dep_replacements(
        ctx: ServiceContext, dep: ServiceDependency,
    ) -> dict[str, str]:
        """Build template replacements for a dependency."""
        return {
            "source_service": ctx.service_name,
            "target_service": dep.target_name,
            "operation": dep.description,
        }

    @staticmethod
    def _event_replacements(
        ctx: ServiceContext, event: EventInfo, consumer: str,
    ) -> dict[str, str]:
        """Build template replacements for an event."""
        return {
            "producer_service": event.producer,
            "consumer_service": consumer,
            "event_name": event.name,
        }

    @staticmethod
    def _feature_name(ctx: ServiceContext, idx: int) -> str:
        """Safely get a feature display name by index."""
        if idx < len(ctx.features):
            return ctx.features[idx].display_name
        return f"feature-{idx + 1}"

    @staticmethod
    def _add_circular_dep_case(
        cases: list[EdgeCase],
        ctx: ServiceContext,
        target: str,
    ) -> None:
        """Add a circular dependency edge case."""
        cases.append(
            EdgeCase(
                id="",
                category="service_unavailability",
                severity="high",
                scenario=(
                    f"Circular dependency detected: "
                    f"{ctx.service_slug} ↔ {target}"
                ),
                trigger="Both services depend on each other",
                affected_services=(ctx.service_slug, target),
                handling_strategy="dependency_inversion, async_decoupling",
                test_suggestion=(
                    "Architecture test: verify no circular "
                    "dependency in service graph"
                ),
            ),
        )
