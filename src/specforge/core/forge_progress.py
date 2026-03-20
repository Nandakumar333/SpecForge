"""ForgeProgress — Rich Live dashboard for forge operations (Feature 017)."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class ProgressEvent:
    """Thread-safe progress event."""

    event_type: str
    slug: str = ""
    phase: str = ""
    status: str = ""


class ForgeProgress:
    """Live Rich dashboard for forge operations."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._stage = "Initializing"
        self._services: dict[str, dict[str, str]] = {}
        self._queue: queue.Queue[ProgressEvent] = queue.Queue()
        self._live: Live | None = None
        self._start_time = time.monotonic()
        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        )
        self._task_id = self._progress.add_task("Forge", total=100)

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._live = Live(
            self._render(), console=self._console, refresh_per_second=1,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def update_stage(self, name: str) -> None:
        self._stage = name
        self._drain_queue()
        self._refresh()

    def update_service(
        self, slug: str, phase: str, status: str,
    ) -> None:
        self._services[slug] = {"phase": phase, "status": status}
        self._refresh()

    def advance_progress(self, amount: float) -> None:
        self._progress.update(self._task_id, advance=amount)
        self._refresh()

    def enqueue(self, event: ProgressEvent) -> None:
        """Thread-safe: workers enqueue events for dashboard consumption."""
        self._queue.put(event)

    def _drain_queue(self) -> None:
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                self._apply_event(event)
            except queue.Empty:
                break

    def _apply_event(self, event: ProgressEvent) -> None:
        if event.event_type == "service_update":
            self._services[event.slug] = {
                "phase": event.phase, "status": event.status,
            }
        elif event.event_type == "stage":
            self._stage = event.status

    def _refresh(self) -> None:
        self._drain_queue()
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Panel:
        table = Table(title="Services")
        table.add_column("Service", style="cyan")
        table.add_column("Phase", style="magenta")
        table.add_column("Status", style="green")
        for slug, info in self._services.items():
            table.add_row(slug, info["phase"], info["status"])
        elapsed = time.monotonic() - self._start_time
        mins, secs = divmod(int(elapsed), 60)
        layout = Layout()
        layout.split_column(
            Layout(self._progress, size=3),
            Layout(table),
        )
        return Panel(
            layout,
            title=f"[bold]{self._stage}[/bold] ({mins:02d}:{secs:02d})",
        )
