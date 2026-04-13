"""Quick throughput benchmark → optimized config values."""
from __future__ import annotations

import time

from core.models import HardwareProfile


def suggest_config(profile: HardwareProfile) -> dict:
    cfg: dict = {}
    # Pick LLM by VRAM / unified memory
    vram = profile.gpu_vram_gb or profile.unified_memory_gb or 0
    if vram >= 16:
        cfg["llm_model"] = "llama3.2"
    elif vram >= 8:
        cfg["llm_model"] = "llama3.2"
    else:
        cfg["llm_model"] = "llama3.2:3b"
    # Embedder
    if profile.ollama_installed and vram >= 4:
        cfg["embed_model"] = "nomic-embed-text"
    else:
        cfg["embed_model"] = "bge-small-en-v1.5"
    cfg["embed_chunk_size"] = 5 if vram < 8 else 10
    return cfg


def measure_embed_throughput(embedder, sample: list[str] | None = None) -> float:
    sample = sample or ["benchmark sentence"] * 20
    t = time.time()
    embedder.embed(sample)
    return len(sample) / max(time.time() - t, 1e-6)
