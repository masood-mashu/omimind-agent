"""
base.py - Abstract Base Class and common configuration for semantic vector embeddings.
"""
from abc import ABC, abstractmethod
from typing import Any

VECTOR_DIM = 384


class BaseEmbeddingModel(ABC):
    """Abstract Base Class for semantic vector embedding providers."""

    provider_name: str = "base"

    @abstractmethod
    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        """Generate a dense vector representation of input text."""

    def embed_batch(self, texts: list[str], dim: int = VECTOR_DIM) -> list[list[float]]:
        """Generate dense vector representations for a batch of text inputs."""
        return [self.embed_text(t, dim=dim) for t in texts]

    def check_health(self) -> dict[str, Any]:
        """Check provider operational status and readiness."""
        return {
            "status": "ready",
            "provider": self.provider_name,
            "dimension": VECTOR_DIM,
            "model": "base",
        }
