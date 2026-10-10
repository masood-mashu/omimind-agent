"""
agents.embeddings - Pluggable semantic vector embedding engines.
Exports:
- BaseEmbeddingModel: ABC for embedding engines.
- DeterministicSubwordEmbedding: Lightweight edge/test subword hashing.
- FastEmbedEmbedding: FastEmbed bge-small-en-v1.5 embeddings.
- SentenceTransformerEmbedding: HuggingFace sentence-transformers.
- get_embedding_provider: Factory returning active embedding instance based on environment.
- generate_semantic_embedding: Convenient helper to embed text using active provider.
"""
import os
import sys

from agents.embeddings.base import VECTOR_DIM, BaseEmbeddingModel
from agents.embeddings.deterministic import STOP_WORDS, DeterministicSubwordEmbedding
from agents.embeddings.fastembed import EMBEDDING_MODEL_NAME, FastEmbedEmbedding
from agents.embeddings.sentence_transformer import SentenceTransformerEmbedding


def get_embedding_provider() -> BaseEmbeddingModel:
    """Factory returning configured semantic embedding provider."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "").lower()
    if provider == "fastembed":
        return FastEmbedEmbedding()
    if provider in ("sentence_transformers", "transformer"):
        return SentenceTransformerEmbedding()
    if provider in ("test", "deterministic", "development"):
        return DeterministicSubwordEmbedding()
    if "pytest" in sys.modules or os.environ.get("VERCEL"):
        return DeterministicSubwordEmbedding()
    return FastEmbedEmbedding()


_ACTIVE_EMBEDDING_MODEL = get_embedding_provider()


def generate_semantic_embedding(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """
    Standard entry point for semantic dense vector generation.
    Dispatches to the active embedding provider.
    """
    return _ACTIVE_EMBEDDING_MODEL.embed_text(text, dim=dim)


__all__ = [
    "EMBEDDING_MODEL_NAME",
    "STOP_WORDS",
    "VECTOR_DIM",
    "_ACTIVE_EMBEDDING_MODEL",
    "BaseEmbeddingModel",
    "DeterministicSubwordEmbedding",
    "FastEmbedEmbedding",
    "SentenceTransformerEmbedding",
    "generate_semantic_embedding",
    "get_embedding_provider",
]
