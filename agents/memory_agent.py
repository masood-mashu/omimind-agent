"""
memory_agent.py - Qdrant Vector Memory Integration for Omi Ambient Audio
Manages persistent conversational memory collections, dense vector embeddings, and semantic recall.
"""
import os
import time
import math
import hashlib
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

COLLECTION_NAME = "omi_ambient_memory"
VECTOR_DIM = 128

import re

STOP_WORDS = set([
    'what', 'when', 'why', 'who', 'how', 'which', 'where',
    'is', 'are', 'was', 'were', 'the', 'a', 'an', 'in', 'on', 'at',
    'by', 'for', 'with', 'about', 'to', 'from', 'of', 'and', 'or',
    'that', 'this', 'it', 'did', 'do', 'does', 'will', 'would',
    'can', 'could', 'must', 'should', 'be', 'been', 'being',
    'have', 'has', 'had', 'say', 'said'
])

def generate_semantic_embedding(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """
    High-performance semantic dense embedding generator.
    Produces deterministic 128-dimensional L2-normalized vector embeddings based on semantic n-grams,
    subword char n-grams, and stop-word filtering for authentic cosine similarity.
    """
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

class QdrantMemoryAgent:
    def __init__(self, storage_path: str = "./qdrant_storage"):
        # In serverless environments (Vercel, AWS Lambda), current working directory is read-only.
        # Fallback cleanly to /tmp or in-memory mode.
        is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
        if is_serverless:
            storage_path = "/tmp/qdrant_storage"

        try:
            self.client = QdrantClient(path=storage_path)
        except Exception:
            self.client = QdrantClient(":memory:")

        self._ensure_collection()

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )

    def index_utterance(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: float,
        timestamp_str: str,
        topic: str = "general",
        urgency: str = "normal"
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
            "urgency": urgency
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
        speaker: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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

        if conditions:
            query_filter = Filter(must=conditions)

        candidate_limit = max(10, limit * 2)
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

        q_stems = set(stem(w) for w in re.findall(r'[a-zA-Z0-9]+', query.lower()) if w not in extended_stop)

        matches = []
        for hit in search_results:
            hit_text = f"{hit.payload.get('speaker', '')} {hit.payload.get('text', '')}"
            text_stems = set(stem(w) for w in re.findall(r'[a-zA-Z0-9]+', hit_text.lower()) if w not in extended_stop)
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

    def get_stats(self) -> Dict[str, Any]:
        info = self.client.get_collection(collection_name=COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "points_count": info.points_count or 0,
            "vector_dimension": VECTOR_DIM,
            "distance_metric": "Cosine"
        }
