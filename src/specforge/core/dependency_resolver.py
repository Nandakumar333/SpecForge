"""DependencyResolver — DAG builder, topological sort, cycle detection."""

from __future__ import annotations

from collections import deque
from dataclasses import replace

from specforge.core.result import Err, Ok, Result
from specforge.core.task_models import DependencyGraph, TaskItem


def _is_external(dep_id: str) -> bool:
    """Check if a dependency ID is an external XDEP reference."""
    return "/" in dep_id


class DependencyResolver:
    """Builds task DAGs and computes topological ordering."""

    def build_graph(self, tasks: list[TaskItem]) -> Result:
        """Create a DependencyGraph from a list of tasks."""
        graph = DependencyGraph()
        task_ids = {t.id for t in tasks}
        for t in tasks:
            graph.tasks_by_id[t.id] = t
            local_deps = tuple(
                d for d in t.dependencies if not _is_external(d)
            )
            graph.adjacency[t.id] = local_deps
            graph.in_degree[t.id] = len(local_deps)
        # Validate references
        for tid, deps in graph.adjacency.items():
            for dep in deps:
                if dep not in task_ids:
                    return Err(
                        f"Task '{tid}' depends on '{dep}' "
                        "which does not exist"
                    )
        return Ok(graph)

    def topological_sort(
        self, graph: DependencyGraph,
    ) -> list[TaskItem]:
        """Kahn's algorithm with stable (phase, id) secondary sort."""
        in_deg = dict(graph.in_degree)
        queue: list[str] = sorted(
            (tid for tid, deg in in_deg.items() if deg == 0),
            key=lambda tid: (
                graph.tasks_by_id[tid].phase,
                tid,
            ),
        )
        result: list[TaskItem] = []
        while queue:
            current = queue.pop(0)
            result.append(graph.tasks_by_id[current])
            dependents = [
                tid for tid, deps in graph.adjacency.items()
                if current in deps
            ]
            for dep_tid in dependents:
                in_deg[dep_tid] -= 1
                if in_deg[dep_tid] == 0:
                    queue.append(dep_tid)
            queue.sort(
                key=lambda tid: (
                    graph.tasks_by_id[tid].phase,
                    tid,
                ),
            )
        self._compute_depths(graph)
        return result

    def mark_parallel(
        self,
        tasks: list[TaskItem],
        graph: DependencyGraph,
    ) -> list[TaskItem]:
        """Mark tasks as parallel when at same depth with disjoint paths."""
        self._compute_depths(graph)
        depth_groups: dict[int, list[TaskItem]] = {}
        for t in tasks:
            d = graph.depth_levels.get(t.id, 0)
            depth_groups.setdefault(d, []).append(t)

        result: list[TaskItem] = []
        for depth, group in sorted(depth_groups.items()):
            if len(group) <= 1:
                result.extend(group)
                continue
            marked = self._mark_group(group)
            result.extend(marked)
        return result

    def _compute_depths(self, graph: DependencyGraph) -> None:
        """BFS to compute topological depth for each task."""
        in_deg = dict(graph.in_degree)
        queue = deque(
            tid for tid, deg in in_deg.items() if deg == 0
        )
        for tid in queue:
            graph.depth_levels[tid] = 0
        while queue:
            current = queue.popleft()
            curr_depth = graph.depth_levels[current]
            dependents = [
                tid for tid, deps in graph.adjacency.items()
                if current in deps
            ]
            for dep_tid in dependents:
                in_deg[dep_tid] -= 1
                new_depth = curr_depth + 1
                prev = graph.depth_levels.get(dep_tid, 0)
                graph.depth_levels[dep_tid] = max(prev, new_depth)
                if in_deg[dep_tid] == 0:
                    queue.append(dep_tid)

    def _mark_group(
        self, group: list[TaskItem],
    ) -> list[TaskItem]:
        """Mark disjoint-path tasks as parallel within a group."""
        path_sets = [set(t.file_paths) for t in group]
        result: list[TaskItem] = []
        for i, task in enumerate(group):
            is_parallel = True
            if not task.file_paths:
                is_parallel = False
            else:
                for j, other in enumerate(group):
                    if i == j:
                        continue
                    if path_sets[i] & path_sets[j]:
                        is_parallel = False
                        break
            result.append(replace(task, parallel=is_parallel))
        return result
