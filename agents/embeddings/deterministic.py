"""
deterministic.py - Zero-dependency deterministic subword embedding engine.
Produces deterministic L2-normalized vector embeddings based on
semantic n-grams, subword character n-grams, and stop-word filtering.
"""
import hashlib
import math
import re
from typing import Any

from agents.embeddings.base import VECTOR_DIM, BaseEmbeddingModel

STOP_WORDS = {
    "what", "when", "why", "who", "how", "which", "where",
    "is", "are", "was", "were", "the", "a", "an", "in", "on", "at",
    "by", "for", "with", "about", "to", "from", "of", "and", "or",
    "that", "this", "it", "did", "do", "does", "will", "would",
    "can", "could", "must", "should", "be", "been", "being",
    "have", "has", "had", "say", "said",
}


class DeterministicSubwordEmbedding(BaseEmbeddingModel):
    """
    High-performance zero-dependency subword embedding model.
    Produces deterministic 384-dimensional (or custom dim) L2-normalized vector embeddings based on
    semantic n-grams, subword character n-grams, and stop-word filtering.
    Optimal for edge devices and low-latency serverless runtimes.
    """

    provider_name: str = "deterministic"

    def check_health(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "provider": self.provider_name,
            "dimension": VECTOR_DIM,
            "model": "deterministic-subword-hash",
        }

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        clean_words = [w for w in words if w not in STOP_WORDS]
        if not clean_words:
            clean_words = words

        vector = [0.0] * dim

        for i, word in enumerate(clean_words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            vector[h % dim] += 3.0
            vector[(h >> 4) % dim] += 1.5

            # Subword 3-character n-grams for morphological resilience
            if len(word) >= 3:
                for j in range(len(word) - 2):
                    gram = word[j:j + 3]
                    h_g = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16)
                    vector[h_g % dim] += 1.0

            # Bigram context
            if i > 0:
                bi_str = f"{clean_words[i - 1]}_{word}"
                h_bi = int(hashlib.md5(bi_str.encode("utf-8")).hexdigest()[:8], 16)
                vector[h_bi % dim] += 3.5

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        else:
            vector = [0.0] * dim
            vector[0] = 1.0

        return vector

    def embed_batch(self, texts: list[str], dim: int = VECTOR_DIM) -> list[list[float]]:
        return [self.embed_text(t, dim=dim) for t in texts]
