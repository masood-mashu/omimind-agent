"""
memory_agent.py - Qdrant Vector Memory Integration for Omi Ambient Audio.
Manages persistent conversational memory collections, point indexing, and hybrid semantic recall.
Embeddings are delegated to the modular agents.embeddings engine.
"""
import hashlib
import os
import re
import sys
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from agents.embeddings import (
    _ACTIVE_EMBEDDING_MODEL,
    EMBEDDING_MODEL_NAME,
    STOP_WORDS,
    VECTOR_DIM,
    BaseEmbeddingModel,
    DeterministicSubwordEmbedding,
    FastEmbedEmbedding,
    SentenceTransformerEmbedding,
    generate_semantic_embedding,
    get_embedding_provider,
)

COLLECTION_NAME = "omi_ambient_memory"


class QdrantMemoryAgent:
    """
    Manages persistent conversational memory collections in Qdrant,
    indexing audio utterances with dense embeddings and querying with hybrid fusion.
    """

    def __init__(self, storage_path: str = "./qdrant_storage"):
        is_serverless = bool(
            os.environ.get("VERCEL")
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or os.environ.get("LAMBDA_TASK_ROOT")
        )
        is_testing = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ or storage_path == ":memory:"

        try:
            from backend.config import settings
            qdrant_url = settings.qdrant_url if not is_testing else None
            qdrant_api_key = settings.qdrant_api_key if not is_testing else None
        except Exception:
            qdrant_url = os.environ.get("QDRANT_URL") if not is_testing else None
            qdrant_api_key = os.environ.get("QDRANT_API_KEY") if not is_testing else None

        allow_ephemeral = is_testing or os.environ.get("ALLOW_EPHEMERAL_MEMORY", "false").lower() == "true"
        self.storage_path = storage_path
        self.qdrant_url = qdrant_url
        self.embedding_model = _ACTIVE_EMBEDDING_MODEL

        if storage_path == ":memory:" or allow_ephemeral:
            self.client = QdrantClient(":memory:")
            self.persistence_mode = "in_memory"
        elif qdrant_url:
            # Qdrant Cloud — persistent across cold starts
            try:
                self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None, timeout=5)
                self.persistence_mode = "cloud"
            except Exception as exc:
                raise RuntimeError("Unable to connect to configured Qdrant service") from exc
        else:
            if is_serverless:
                raise RuntimeError("Persistent Qdrant configuration is required in serverless production")
            self.client = QdrantClient(path=storage_path)
            self.persistence_mode = "local_persistent"

        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)
            if exists:
                info = self.client.get_collection(COLLECTION_NAME)
                current_dim = getattr(info.config.params.vectors, "size", None)
                if current_dim and current_dim != VECTOR_DIM:
                    self.client.delete_collection(COLLECTION_NAME)
                    exists = False

            if not exists:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            if getattr(self, "persistence_mode", None) != "in_memory":
                for field in ["uid", "session_id", "speaker", "topic"]:
                    try:
                        self.client.create_payload_index(
                            collection_name=COLLECTION_NAME,
                            field_name=field,
                            field_schema=PayloadSchemaType.KEYWORD,
                        )
                    except Exception:
                        pass
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
            payload=payload,
        )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point],
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
            limit=candidate_limit,
        ).points

        # Hybrid fusion: vector cosine + stem overlap
        extended_stop = STOP_WORDS | {
            "before", "after", "also", "today", "welcome", "team", "our", "we", "i", "my", "all", "you",
        }

        def stem(w: str) -> str:
            return w.rstrip("s") if len(w) > 3 else w

        q_stems = {stem(w) for w in re.findall(r"[a-zA-Z0-9]+", query.lower()) if w not in extended_stop}

        matches = []
        for hit in search_results:
            hit_text = f"{hit.payload.get('speaker', '')} {hit.payload.get('text', '')}"
            text_stems = {stem(w) for w in re.findall(r"[a-zA-Z0-9]+", hit_text.lower()) if w not in extended_stop}
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
                "session_id": hit.payload.get("session_id", ""),
                "uid": hit.payload.get("uid", ""),
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
                    points_selector=[p_id],
                )
                return True
            if session_id:
                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=Filter(
                        must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))],
                    ),
                )
                return True
        except Exception:
            return False
        return False

    def get_stats(self) -> dict[str, Any]:
        info = self.client.get_collection(collection_name=COLLECTION_NAME)
        provider_name = getattr(self.embedding_model, "provider_name", type(self.embedding_model).__name__)
        health_info = getattr(self.embedding_model, "check_health", lambda: {"status": "ready"})()
        return {
            "collection": COLLECTION_NAME,
            "points_count": info.points_count or 0,
            "vector_dimension": VECTOR_DIM,
            "distance_metric": "Cosine",
            "embedding_provider": provider_name,
            "embedding_health": health_info,
            "persistence_mode": self.persistence_mode,
        }


# Alias for clean naming
MemoryAgent = QdrantMemoryAgent

__all__ = [
    "COLLECTION_NAME",
    "EMBEDDING_MODEL_NAME",
    "STOP_WORDS",
    "VECTOR_DIM",
    "_ACTIVE_EMBEDDING_MODEL",
    "BaseEmbeddingModel",
    "DeterministicSubwordEmbedding",
    "FastEmbedEmbedding",
    "MemoryAgent",
    "QdrantMemoryAgent",
    "SentenceTransformerEmbedding",
    "generate_semantic_embedding",
    "get_embedding_provider",
]
