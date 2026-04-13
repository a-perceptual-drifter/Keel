"""Deterministic hash-based MockEmbedder for tests."""
from __future__ import annotations

import hashlib

import numpy as np


class MockEmbedder:
    def __init__(self, dims: int = 32):
        self.dims = dims

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        out = []
        for t in texts:
            h = hashlib.sha256((t or "").encode()).digest()
            # expand to dims floats in [-1, 1]
            raw = np.frombuffer((h * ((self.dims // len(h)) + 1))[: self.dims], dtype=np.uint8)
            vec = (raw.astype(np.float32) / 127.5) - 1.0
            n = np.linalg.norm(vec)
            out.append(vec / n if n > 0 else vec)
        return out
