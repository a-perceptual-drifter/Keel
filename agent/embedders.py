"""Concrete embedders. Heavy deps imported lazily."""
from __future__ import annotations

import numpy as np


class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        import requests
        out = []
        for t in texts:
            r = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": t},
                timeout=60,
            )
            r.raise_for_status()
            out.append(np.asarray(r.json()["embedding"], dtype=np.float32))
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from sentence_transformers import SentenceTransformer  # lazy
        self._model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        vecs = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [np.asarray(v, dtype=np.float32) for v in vecs]
