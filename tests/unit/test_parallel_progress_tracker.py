"""Unit tests for ProgressTracker thread safety (Feature 016)."""

from __future__ import annotations

import threading

from rich.console import Console

from specforge.core.parallel_progress_tracker import ProgressTracker


class TestProgressTracker:
    def _make_tracker(self, n: int = 3, state_path=None):
        console = Console(quiet=True)
        return ProgressTracker(
            console=console,
            total_services=n,
            state_path=state_path,
        )

    def test_phase_complete_increments(self):
        t = self._make_tracker()
        t.on_phase_start("auth", "spec")
        t.on_phase_complete("auth", "spec")
        t.on_phase_complete("auth", "research")
        summary = t.get_summary()
        auth = next(s for s in summary.services if s.slug == "auth")
        assert auth.phases_completed == 2

    def test_service_complete(self):
        t = self._make_tracker()
        t.on_phase_start("auth", "spec")
        t.on_service_complete("auth")
        summary = t.get_summary()
        auth = next(s for s in summary.services if s.slug == "auth")
        assert auth.status == "completed"

    def test_service_failed(self):
        t = self._make_tracker()
        t.on_service_failed("ledger", "timeout")
        summary = t.get_summary()
        ledger = next(s for s in summary.services if s.slug == "ledger")
        assert ledger.status == "failed"
        assert ledger.error == "timeout"

    def test_service_blocked(self):
        t = self._make_tracker()
        t.on_service_blocked("portfolio", "auth")
        summary = t.get_summary()
        p = next(s for s in summary.services if s.slug == "portfolio")
        assert p.status == "blocked"
        assert p.blocked_by == "auth"

    def test_service_cancelled(self):
        t = self._make_tracker()
        t.on_service_cancelled("admin")
        summary = t.get_summary()
        a = next(s for s in summary.services if s.slug == "admin")
        assert a.status == "cancelled"

    def test_overall_completed(self):
        t = self._make_tracker(2)
        t.on_service_complete("a")
        t.on_service_complete("b")
        summary = t.get_summary()
        assert summary.status == "completed"

    def test_overall_failed(self):
        t = self._make_tracker(2)
        t.on_service_complete("a")
        t.on_service_failed("b", "err")
        summary = t.get_summary()
        assert summary.status == "failed"

    def test_thread_safety(self):
        t = self._make_tracker(10)
        errors: list[str] = []

        def _worker(slug: str):
            try:
                t.on_phase_start(slug, "spec")
                for phase in ["spec", "research", "datamodel",
                              "edgecase", "plan", "checklist", "tasks"]:
                    t.on_phase_complete(slug, phase)
                t.on_service_complete(slug)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=_worker, args=(f"svc-{i}",))
            for i in range(10)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors
        summary = t.get_summary()
        assert len(summary.services) == 10
        for svc in summary.services:
            assert svc.status == "completed"
            assert svc.phases_completed == 7

    def test_persist_writes_state(self, tmp_path):
        path = tmp_path / "state.json"
        t = self._make_tracker(1, state_path=path)
        t.on_phase_start("x", "spec")
        t.on_phase_complete("x", "spec")
        assert path.exists()
