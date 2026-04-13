"""MockLLM — canned responses for challenge classification and nuance."""
from __future__ import annotations


class MockLLM:
    def __init__(self, responses: dict[str, str] | None = None, default: str = "neither"):
        self.responses = responses or {}
        self.default = default
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str, max_tokens: int = 80) -> str:
        self.calls.append((system, prompt))
        for k, v in self.responses.items():
            if k in prompt:
                return v
        return self.default
