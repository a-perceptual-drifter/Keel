"""Concrete LLM clients. Lazy imports."""
from __future__ import annotations


class OllamaLLM:
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434", resource_manager=None):
        self.model = model
        self.base_url = base_url
        self.rm = resource_manager

    def complete(self, system: str, prompt: str, max_tokens: int = 80) -> str:
        import requests
        def _do():
            r = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": system,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=120,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        if self.rm is not None:
            with self.rm.acquire(self.model):
                return _do()
        return _do()


class AnthropicLLM:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        from anthropic import Anthropic  # lazy
        self._client = Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, prompt: str, max_tokens: int = 80) -> str:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class OpenAILLM:
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # lazy
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def complete(self, system: str, prompt: str, max_tokens: int = 80) -> str:
        r = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content or ""
