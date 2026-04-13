"""Priority-aware lock for Ollama access."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager


class OllamaResourceManager:
    FOREGROUND = 0
    BACKGROUND = 1

    def __init__(self):
        self._lock = threading.Lock()
        self._foreground_waiting = threading.Event()

    @contextmanager
    def acquire(self, model: str = "", priority: int = BACKGROUND):
        if priority == self.FOREGROUND:
            self._foreground_waiting.set()
            with self._lock:
                self._foreground_waiting.clear()
                yield
        else:
            while self._foreground_waiting.is_set():
                time.sleep(0.1)
            with self._lock:
                yield
