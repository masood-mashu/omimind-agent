"""
memory_agent.py - Qdrant Vector Memory Integration for Omi Ambient Audio.
Manages persistent conversational memory collections, point indexing, and hybrid semantic recall.
Embeddings are delegated to the modular agents.embeddings engine.
"""
import hashlib
import os
import re
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
from backend.config import is_testing, settings

COLLECTION_NAME = settings.collection_name


class QdrantDimensionMismatchError(RuntimeError):
    """Raised when an existing Qdrant collection dimension does not match the configured VECTOR_DIM."""
    pass


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
        testing_env = is_testing() or storage_path == ":memory:"

        qdrant_url = settings.qdrant_url if not testing_env else None
        qdrant_api_key = settings.qdrant_api_key if not testing_env else None

        # Never silently fall back from production Qdrant to ephemeral memory
        allow_ephemeral = testing_env or (
            settings.environment.lower() != "production"
            and os.environ.get("ALLOW_EPHEMERAL_MEMORY", "false").lower() == "true"
        )
        self.storage_path = storage_path
        self.qdrant_url = qdrant_url
        self.collection_name = settings.collection_name
        self.embedding_model = _ACTIVE_EMBEDDING_MODEL

        if storage_path == ":memory:":
            self.client = QdrantClient(":memory:")
            self.persistence_mode = "in_memory"
        elif allow_ephemeral and not qdrant_url:
            self.client = QdrantClient(":memory:")
            self.persistence_mode = "in_memory"
        elif qdrant_url:
            # Qdrant Cloud — persistent across cold starts
            try:
                qdrant_timeout = float(os.environ.get("QDRANT_TIMEOUT", "25"))
                self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None, timeout=qdrant_timeout)
                self.persistence_mode = "cloud"
            except Exception as exc:
                raise RuntimeError("Unable to connect to configured Qdrant service") from exc
        else:
            if settings.environment.lower() == "production" or is_serverless:
                raise RuntimeError("Persistent Qdrant Cloud configuration is required in production mode.")
            self.client = QdrantClient(path=storage_path)
            self.persistence_mode = "local_persistent"

        self._ensure_collection()

    def _ensure_collection(self, allow_rebuild: bool = False):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if exists:
                info = self.client.get_collection(self.collection_name)
                current_dim = getattr(info.config.params.vectors, "size", None)
                if current_dim and current_dim != VECTOR_DIM:
                    if allow_rebuild:
                        self.client.delete_collection(self.collection_name)
                        exists = False
                    else:
                        raise QdrantDimensionMismatchError(
                            f"Qdrant collection '{self.collection_name}' dimension mismatch: "
                            f"existing dimension is {current_dim}, but expected dimension is {VECTOR_DIM}. "
                            f"Existing collections are preserved and never automatically deleted. "
                            f"Recommended migration action: update COLLECTION_NAME to a new name (e.g. '{self.collection_name}_v2') "
                            f"to re-index into a fresh collection, or run an explicit migration with allow_rebuild=True."
                        )

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            if getattr(self, "persistence_mode", None) != "in_memory":
                for field in ["uid", "session_id", "speaker", "topic"]:
                    try:
                        self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name=field,
                            field_schema=PayloadSchemaType.KEYWORD,
                        )
                    except Exception:
                        pass
        except QdrantDimensionMismatchError:
            raise
        except Exception as exc:
            raise RuntimeError("Unable to initialize the persistent Qdrant collection") from exc

    def rebuild_collection(self, confirm: bool = False) -> None:
        """Explicit administrative rebuild path to delete and recreate the collection."""
        if not confirm:
            raise ValueError("Explicit confirmation (confirm=True) is required to rebuild the collection.")
        self._ensure_collection(allow_rebuild=True)


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
        # Stable, idempotent identity for the full utterance. Including the
        # tenant and speaker prevents truncation-based collisions while still
        # allowing safe upserts when a webhook is retried.
        point_key = f"{uid}\x1f{session_id}\x1f{speaker}\x1f{timestamp}\x1f{text}\x1f{topic}"
        point_id = int(hashlib.sha256(point_key.encode("utf-8")).hexdigest()[:16], 16)
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
            collection_name=self.collection_name,
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

        should_conditions = None
        if uid and uid not in ("all", "*"):
            if uid == "default_user":
                wearable_uids = ["default_user", "uoCU1OLVdUaEU9IxVSICTbakkiD3"]
                if hasattr(settings, "default_user_id") and settings.default_user_id not in wearable_uids:
                    wearable_uids.append(settings.default_user_id)
                should_conditions = [
                    FieldCondition(key="uid", match=MatchValue(value=u)) for u in wearable_uids
                ]
            else:
                conditions.append(FieldCondition(key="uid", match=MatchValue(value=uid)))

        if conditions or should_conditions:
            query_filter = Filter(must=conditions if conditions else None, should=should_conditions)

        candidate_limit = max(40, limit * 10)
        search_results = self.client.query_points(
            collection_name=self.collection_name,
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
                "id": str(hit.id),
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

    def _delete_by_point_id(self, point_id: int | str, uid: str | None) -> bool:
        p_id = int(point_id) if str(point_id).isdigit() else str(point_id)
        try:
            retrieved = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[p_id],
                with_payload=True,
            )
        except Exception:
            retrieved = []
        if not retrieved:
            return False
        point_uid = (retrieved[0].payload or {}).get("uid")
        if uid is not None and point_uid != uid:
            raise PermissionError("Point belongs to another user")
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[p_id],
            )
            return True
        except Exception:
            return False

    def _delete_by_session_id(self, session_id: str, uid: str | None) -> bool:
        try:
            scroll_res, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
                ),
                limit=10,
                with_payload=True,
            )
        except Exception:
            scroll_res = []
        if not scroll_res:
            return False
        if uid is not None:
            user_points = [p for p in scroll_res if (p.payload or {}).get("uid") == uid]
            if not user_points:
                raise PermissionError("Session belongs to another user")
        conditions = [FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        if uid is not None:
            conditions.append(FieldCondition(key="uid", match=MatchValue(value=uid)))
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=conditions),
            )
            return True
        except Exception:
            return False

    def delete_memory(
        self,
        session_id: str | None = None,
        point_id: int | str | None = None,
        uid: str | None = None,
    ) -> bool:
        """
        Deletes points by point_id or by session_id filter for user privacy control.
        Enforces tenant isolation by verifying ownership against the authenticated UID.
        Raises PermissionError if target exists but belongs to another user.
        """
        if point_id is not None:
            return self._delete_by_point_id(point_id, uid)
        if session_id:
            return self._delete_by_session_id(session_id, uid)
        return False


    def get_stats(self) -> dict[str, Any]:
        info = self.client.get_collection(collection_name=self.collection_name)
        provider_name = getattr(self.embedding_model, "provider_name", type(self.embedding_model).__name__)
        health_info = getattr(self.embedding_model, "check_health", lambda: {"status": "ready"})()
        return {
            "collection": self.collection_name,
            "points_count": info.points_count or 0,
            "vector_dimension": VECTOR_DIM,
            "distance_metric": "Cosine",
            "embedding_provider": provider_name,
            "embedding_health": health_info,
            "persistence_mode": self.persistence_mode,
        }

    def get_recent_memories(self, limit: int = 30, uid: str | None = None) -> list[dict[str, Any]]:
        """
        Scrolls recent indexed memory utterances from Qdrant with optional UID filtering.
        """
        try:
            scroll_filter = None
            if uid and uid not in ("all", "*"):
                if uid == "default_user":
                    wearable_uids = ["default_user", "uoCU1OLVdUaEU9IxVSICTbakkiD3"]
                    if hasattr(settings, "default_user_id") and settings.default_user_id not in wearable_uids:
                        wearable_uids.append(settings.default_user_id)
                    scroll_filter = Filter(should=[
                        FieldCondition(key="uid", match=MatchValue(value=u)) for u in wearable_uids
                    ])
                else:
                    scroll_filter = Filter(must=[FieldCondition(key="uid", match=MatchValue(value=uid))])
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            memories = []

            for p in points:
                payload = p.payload or {}
                memories.append({
                    "id": str(p.id),
                    "speaker": payload.get("speaker", "Unknown"),
                    "text": payload.get("text", ""),
                    "timestamp": payload.get("timestamp", 0.0),
                    "timestamp_str": payload.get("timestamp_str", ""),
                    "topic": payload.get("topic", "general"),
                    "session_id": payload.get("session_id", ""),
                    "uid": payload.get("uid", ""),
                })
            return memories
        except Exception:
            return []


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
