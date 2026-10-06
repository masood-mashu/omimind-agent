"""
sentence_transformer.py - Sentence Transformers embedding engine.
Utilizes standard sentence-transformers (e.g., all-MiniLM-L6-v2) with
graceful fallback to DeterministicSubwordEmbedding.
"""
import math
from typing import Any

from agents.embeddings.base import VECTOR_DIM, BaseEmbeddingModel
from agents.embeddings.deterministic import DeterministicSubwordEmbedding


class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """
    Production-grade Transformer embedding model.
    Utilizes standard sentence-transformers (e.g., all-MiniLM-L6-v2),
    with graceful fallback to DeterministicSubwordEmbedding.
    """

    provider_name: str = "sentence_transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._fallback = DeterministicSubwordEmbedding()

    def _get_model(self):
        if self._model is None:
            try:
                import importlib
                st_mod = importlib.import_module("sentence_transformers")
                SentenceTransformer = st_mod.SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self._model = False
        return self._model

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        model = self._get_model()
        if model:
            try:
                raw_vec = model.encode(text, normalize_embeddings=True)
                if len(raw_vec) == dim:
                    return raw_vec.tolist()
                elif len(raw_vec) > dim:
                    vec = raw_vec[:dim].tolist()
                    norm = math.sqrt(sum(v * v for v in vec))
                    return [v / norm for v in vec] if norm > 0 else vec
            except Exception:
                pass
        return self._fallback.embed_text(text, dim=dim)

    def embed_batch(self, texts: list[str], dim: int = VECTOR_DIM) -> list[list[float]]:
        model = self._get_model()
        if model:
            try:
                raw_vecs = model.encode(texts, normalize_embeddings=True)
                results = []
                for raw_vec in raw_vecs:
                    if len(raw_vec) == dim:
                        results.append(raw_vec.tolist())
                    elif len(raw_vec) > dim:
                        vec = raw_vec[:dim].tolist()
                        norm = math.sqrt(sum(v * v for v in vec))
                        results.append([v / norm for v in vec] if norm > 0 else vec)
                    else:
                        results.append(self._fallback.embed_text(str(raw_vec), dim=dim))
                return results
            except Exception:
                pass
        return [self._fallback.embed_text(t, dim=dim) for t in texts]

    def check_health(self) -> dict[str, Any]:
        return {
            "status": "ready" if self._get_model() else "degraded",
            "provider": self.provider_name,
            "dimension": VECTOR_DIM,
            "model": self.model_name,
        }
