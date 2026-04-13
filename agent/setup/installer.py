"""Ollama installer / model pull. Shell-based and safe to no-op."""
from __future__ import annotations

import shutil
import subprocess


def ensure_ollama_models(llm_model: str = "llama3.2", embed_model: str = "nomic-embed-text") -> bool:
    if shutil.which("ollama") is None:
        return False
    for m in (llm_model, embed_model):
        try:
            subprocess.run(["ollama", "pull", m], check=True, timeout=600)
        except Exception:
            return False
    return True
