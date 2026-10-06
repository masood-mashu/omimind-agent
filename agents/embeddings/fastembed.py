"""
fastembed.py - FastEmbed semantic dense vector embedding engine.
Integrates BAAI/bge-small-en-v1.5 with automated local/serverless cache resolution.
"""
import os
from typing import Any

from agents.embeddings.base import VECTOR_DIM, BaseEmbeddingModel

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"


class FastEmbedEmbedding(BaseEmbeddingModel):
    """The hackathon guide's semantic embedding provider."""

    provider_name: str = "fastembed"

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, cache_dir: str | None = None):
        self.model_name = model_name
        self.cache_dir = cache_dir or os.environ.get("FASTEMBED_CACHE_DIR")
        self._model = None
        self.initialization_error: str | None = None

    def _resolve_cache_dir(self) -> tuple[str | None, bool]:
        bundled_candidates = [
            os.path.abspath("fastembed_cache"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fastembed_cache")),
            os.path.join(os.environ.get("LAMBDA_TASK_ROOT", ""), "fastembed_cache"),
        ]

        is_serverless = bool(
            os.environ.get("VERCEL")
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or os.environ.get("LAMBDA_TASK_ROOT")
        )

        for candidate in bundled_candidates:
            if candidate and os.path.isdir(candidate):
                if is_serverless:
                    tmp_cache = "/tmp/fastembed_cache"
                    if not os.path.exists(tmp_cache):
                        import shutil
                        try:
                            shutil.copytree(candidate, tmp_cache)
                            return tmp_cache, True
                        except Exception:
                            return candidate, True
                    return tmp_cache, True
                return candidate, True

        if self.cache_dir:
            return self.cache_dir, False

        if is_serverless:
            tmp_cache = "/tmp/fastembed_cache"
            os.makedirs(tmp_cache, exist_ok=True)
            return tmp_cache, False
        return None, False

    def _get_model(self):
        if self._model is None:
            is_serverless = bool(
                os.environ.get("VERCEL")
                or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
                or os.environ.get("LAMBDA_TASK_ROOT")
            )
            if is_serverless:
                os.environ.setdefault("HF_HOME", "/tmp/huggingface")
                os.environ.setdefault("TORCH_HOME", "/tmp/torch")

            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                self.initialization_error = "fastembed package is not installed"
                raise RuntimeError("FastEmbed library not available in runtime environment") from exc

            cache_path, local_only = self._resolve_cache_dir()
            kwargs: dict[str, Any] = {}
            if cache_path:
                kwargs["cache_dir"] = cache_path
            if local_only:
                kwargs["local_files_only"] = True

            try:
                self._model = TextEmbedding(self.model_name, **kwargs)
                self.initialization_error = None
            except Exception as exc:
                self.initialization_error = f"Model load failed: {str(exc)}"
                raise RuntimeError(f"Failed to initialize FastEmbed model '{self.model_name}'") from exc
        return self._model

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        model = self._get_model()
        vector = next(iter(model.embed([text])))
        values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        if len(values) != dim:
            raise ValueError(f"Embedding model returned {len(values)} dimensions; expected {dim}")
        return values

    def embed_batch(self, texts: list[str], dim: int = VECTOR_DIM) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.embed(texts)
        results = []
        for v in vectors:
            values = v.tolist() if hasattr(v, "tolist") else list(v)
            if len(values) != dim:
                raise ValueError(f"Embedding model returned {len(values)} dimensions; expected {dim}")
            results.append(values)
        return results

    def check_health(self) -> dict[str, Any]:
        try:
            self._get_model()
            return {
                "status": "ready",
                "provider": self.provider_name,
                "dimension": VECTOR_DIM,
                "model": self.model_name,
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "provider": self.provider_name,
                "dimension": VECTOR_DIM,
                "model": self.model_name,
                "error": self.initialization_error or str(exc),
            }
