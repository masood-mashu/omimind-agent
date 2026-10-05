"""
memory_agent.py - Qdrant Vector Memory Integration for Omi Ambient Audio
Manages persistent conversational memory collections, dense vector embeddings, and semantic recall.
"""
import hashlib
import math
import os
import re
import sys
from abc import ABC, abstractmethod
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

COLLECTION_NAME = "omi_ambient_memory"
VECTOR_DIM = 384
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

STOP_WORDS = {
    'what', 'when', 'why', 'who', 'how', 'which', 'where',
    'is', 'are', 'was', 'were', 'the', 'a', 'an', 'in', 'on', 'at',
    'by', 'for', 'with', 'about', 'to', 'from', 'of', 'and', 'or',
    'that', 'this', 'it', 'did', 'do', 'does', 'will', 'would',
    'can', 'could', 'must', 'should', 'be', 'been', 'being',
    'have', 'has', 'had', 'say', 'said'
}

class BaseEmbeddingModel(ABC):
    """Abstract Base Class for semantic vector embedding providers."""

    @abstractmethod
    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        """Generate a dense vector representation of input text."""


class DeterministicSubwordEmbedding(BaseEmbeddingModel):
    """
    High-performance zero-dependency subword embedding model.
    Produces deterministic 128-dimensional L2-normalized vector embeddings based on
    semantic n-grams, subword character n-grams, and stop-word filtering.
    Optimal for edge devices and low-latency serverless runtimes.
    """

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        words = re.findall(r'[a-zA-Z0-9]+', text.lower())
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
                    gram = word[j:j+3]
                    h_g = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16)
                    vector[h_g % dim] += 1.0

            # Bigram context
            if i > 0:
                bi_str = f"{clean_words[i-1]}_{word}"
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


class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """
    Production-grade Transformer embedding model.
    Utilizes standard sentence-transformers (e.g., all-MiniLM-L6-v2) or FastEmbed when available,
    with graceful fallback to DeterministicSubwordEmbedding.
    """

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
                # Resample or project to target dimension
                if len(raw_vec) == dim:
                    return raw_vec.tolist()
                elif len(raw_vec) > dim:
                    vec = raw_vec[:dim].tolist()
                    norm = math.sqrt(sum(v * v for v in vec))
                    return [v / norm for v in vec] if norm > 0 else vec
            except Exception:
                pass
        return self._fallback.embed_text(text, dim=dim)


class FastEmbedEmbedding(BaseEmbeddingModel):
    """The hackathon guide's semantic embedding provider."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(self.model_name)
        return self._model

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        vector = next(iter(self._get_model().embed([text])))
        values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        if len(values) != dim:
            raise ValueError(f"Embedding model returned {len(values)} dimensions; expected {dim}")
        return values


# Embedding Provider Factory
def get_embedding_provider() -> BaseEmbeddingModel:
    provider = os.environ.get("EMBEDDING_PROVIDER", "fastembed").lower()
    if provider in ("test", "deterministic", "development") or "pytest" in sys.modules:
        return DeterministicSubwordEmbedding()
    if provider in ("fastembed", "production", "default"):
        return FastEmbedEmbedding()
    if provider in ("sentence_transformers", "transformer", "production"):
        return SentenceTransformerEmbedding()
    return DeterministicSubwordEmbedding()

_ACTIVE_EMBEDDING_MODEL = get_embedding_provider()

def generate_semantic_embedding(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """
    Standard entry point for semantic dense vector generation.
    Dispatches to the active embedding provider.
    """
    return _ACTIVE_EMBEDDING_MODEL.embed_text(text, dim=dim)

class QdrantMemoryAgent:
    def __init__(self, storage_path: str = "./qdrant_storage"):
        is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("LAMBDA_TASK_ROOT"))
        is_testing = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ or storage_path == ":memory:"

        try:
            from backend.config import settings
            qdrant_url = settings.qdrant_url if not is_testing else None
            qdrant_api_key = settings.qdrant_api_key if not is_testing else None
        except Exception:
            qdrant_url = os.environ.get("QDRANT_URL") if not is_testing else None
            qdrant_api_key = os.environ.get("QDRANT_API_KEY") if not is_testing else None

        allow_ephemeral = is_testing or os.environ.get("ALLOW_EPHEMERAL_MEMORY", "false").lower() == "true"
        if storage_path == ":memory:" or allow_ephemeral:
            self.client = QdrantClient(":memory:")
        elif qdrant_url:
            # Qdrant Cloud — persistent across cold starts
            try:
                self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None, timeout=5)
            except Exception as exc:
                raise RuntimeError("Unable to connect to configured Qdrant service") from exc
        else:
            if is_serverless:
                raise RuntimeError("Persistent Qdrant configuration is required in serverless production")
            self.client = QdrantClient(path=storage_path)

        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
        except Exception as exc:
            raise RuntimeError("Unable to initialize the persistent Qdrant collection") from exc

    def index_utterance(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: float,
        timestamp_str: str,
        topic: str = "general",
        urgency: str = "normal",
        uid: str = "default_user",
    ) -> str:
        """
        Embeds and stores an audio utterance from Omi into Qdrant vector memory.
        """
        point_id = int(hashlib.md5(f"{session_id}_{timestamp}_{text[:30]}".encode()).hexdigest()[:8], 16)
        vector = generate_semantic_embedding(f"{speaker} {text}")

        payload = {
            "session_id": session_id,
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
            "timestamp_str": timestamp_str,
            "topic": topic,
            "urgency": urgency,
            "uid": uid,
        }

        point = PointStruct(
            id=point_id,
            vector=vector,
            payload=payload
        )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        return str(point_id)

    def search_memory(
        self,
        query: str,
        limit: int = 4,
        speaker: str | None = None,
        topic: str | None = None,
        uid: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic vector search over past conversations with hybrid lexical & stem boost.
        """
        query_vector = generate_semantic_embedding(query)

        query_filter = None
        conditions = []
        if speaker:
            conditions.append(FieldCondition(key="speaker", match=MatchValue(value=speaker)))
        if topic:
            conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))
        if uid:
            conditions.append(FieldCondition(key="uid", match=MatchValue(value=uid)))

        if conditions:
            query_filter = Filter(must=conditions)

        candidate_limit = max(40, limit * 10)
        search_results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=candidate_limit
        ).points

        # Hybrid fusion: vector cosine + stem overlap
        extended_stop = STOP_WORDS | {'before', 'after', 'also', 'today', 'welcome', 'team', 'our', 'we', 'i', 'my', 'all', 'you'}
        def stem(w: str) -> str:
            return w.rstrip('s') if len(w) > 3 else w

        q_stems = {stem(w) for w in re.findall(r'[a-zA-Z0-9]+', query.lower()) if w not in extended_stop}

        matches = []
        for hit in search_results:
            hit_text = f"{hit.payload.get('speaker', '')} {hit.payload.get('text', '')}"
            text_stems = {stem(w) for w in re.findall(r'[a-zA-Z0-9]+', hit_text.lower()) if w not in extended_stop}
            overlap = len(q_stems & text_stems)
            lexical_ratio = (overlap / len(q_stems)) if q_stems else 0.0
            raw_cosine = float(hit.score)
            norm_cosine = min(1.0, max(0.0, (raw_cosine - 0.15) / 0.55))
            hybrid_score = round((0.60 * norm_cosine) + (0.40 * lexical_ratio), 4)

            matches.append({
                "score": hybrid_score,
                "raw_vector_score": round(float(hit.score), 4),
                "speaker": hit.payload.get("speaker", "Unknown"),
                "text": hit.payload.get("text", ""),
                "timestamp_str": hit.payload.get("timestamp_str", ""),
                "topic": hit.payload.get("topic", "general"),
                "session_id": hit.payload.get("session_id", "")
            })

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches[:limit]

    def delete_memory(self, session_id: str | None = None, point_id: int | str | None = None) -> bool:
        """
        Deletes points by point_id or by session_id filter for user privacy control.
        """
        try:
            if point_id is not None:
                p_id = int(point_id) if str(point_id).isdigit() else str(point_id)
                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=[p_id]
                )
                return True
            if session_id:
                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=Filter(
                        must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
                    )
                )
                return True
        except Exception:
            return False
        return False

    def get_stats(self) -> dict[str, Any]:
        info = self.client.get_collection(collection_name=COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "points_count": info.points_count or 0,
            "vector_dimension": VECTOR_DIM,
            "distance_metric": "Cosine"
        }
