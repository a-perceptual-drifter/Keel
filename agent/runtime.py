"""Shared runtime — event queue + shutdown signal between scheduler and REPL."""
from __future__ import annotations

import queue
import threading
from datetime import datetime

from core.models import KeelEvent


class Runtime:
    def __init__(self, max_events: int = 100):
        self.events: queue.Queue[KeelEvent] = queue.Queue(maxsize=max_events)
        self.shutdown = threading.Event()

    def emit(self, event_type: str, payload: dict | None = None) -> None:
        try:
            self.events.put_nowait(
                KeelEvent(type=event_type, payload=payload or {}, timestamp=datetime.now())
            )
        except queue.Full:
            pass

    def drain(self) -> list[KeelEvent]:
        out: list[KeelEvent] = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                break
        return out
