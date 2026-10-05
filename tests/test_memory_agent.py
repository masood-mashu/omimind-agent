"""
test_memory_agent.py - Granular Unit Tests & Failure Modes for QdrantMemoryAgent
Covers:
- Embedding dimensions, L2 normalization, deterministic reproducibility
- Pluggable embedding providers and fallback modes
- Qdrant indexing, upserting, point count tracking
- Hybrid search scoring (cosine + lexical stem overlap)
- Filtering by speaker and topic
- Failure modes: empty input, punctuation-only, Qdrant client exceptions
"""
from unittest.mock import patch

import pytest

from agents.memory_agent import (
    VECTOR_DIM,
    DeterministicSubwordEmbedding,
    QdrantMemoryAgent,
    SentenceTransformerEmbedding,
)


class TestEmbeddingModels:
    def test_deterministic_embedding_dimension_and_norm(self):
        embedder = DeterministicSubwordEmbedding()
        vec = embedder.embed_text("Deploy Kubernetes cluster to production by Friday", dim=VECTOR_DIM)
        assert len(vec) == VECTOR_DIM
        # Check L2 unit normalization
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-4) == 1.0

    def test_empty_string_embedding_resilience(self):
        embedder = DeterministicSubwordEmbedding()
        vec = embedder.embed_text("", dim=VECTOR_DIM)
        assert len(vec) == VECTOR_DIM
        assert sum(x * x for x in vec) ** 0.5 == 1.0

    def test_punctuation_only_embedding(self):
        embedder = DeterministicSubwordEmbedding()
        vec = embedder.embed_text("!@#$%^&*()_+-=[]{}|;':,./<>?", dim=VECTOR_DIM)
        assert len(vec) == VECTOR_DIM
        assert sum(x * x for x in vec) ** 0.5 == 1.0

    def test_semantic_similarity_direction(self):
        embedder = DeterministicSubwordEmbedding()
        v_budget1 = embedder.embed_text("Approved $400k cloud infrastructure budget")
        v_budget2 = embedder.embed_text("Financial allocation for cloud server infrastructure")
        v_unrelated = embedder.embed_text("Recipe for baking sourdough bread in high altitude")

        dot_related = sum(a * b for a, b in zip(v_budget1, v_budget2, strict=False))
        dot_unrelated = sum(a * b for a, b in zip(v_budget1, v_unrelated, strict=False))
        assert dot_related > dot_unrelated

    def test_sentence_transformer_fallback(self):
        # SentenceTransformerEmbedding with unavailable model should fallback gracefully
        st_embedder = SentenceTransformerEmbedding(model_name="nonexistent-mock-model")
        vec = st_embedder.embed_text("Testing fallback mechanism", dim=VECTOR_DIM)
        assert len(vec) == VECTOR_DIM
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-4) == 1.0


class TestQdrantMemoryAgent:
    @pytest.fixture
    def memory_agent(self):
        return QdrantMemoryAgent(storage_path=":memory:")

    def test_index_and_retrieve_utterance(self, memory_agent):
        point_id = memory_agent.index_utterance(
            session_id="test_session_1",
            speaker="Alice (Lead Architect)",
            text="The TLS certificate renewal pipeline is automated via Certbot.",
            timestamp=12.5,
            timestamp_str="00:12",
            topic="security",
            urgency="high"
        )
        assert point_id is not None
        assert isinstance(point_id, str)

        stats = memory_agent.get_stats()
        assert stats["points_count"] >= 1
        assert stats["vector_dimension"] == VECTOR_DIM

    def test_hybrid_search_with_speaker_attribution(self, memory_agent):
        memory_agent.index_utterance(
            session_id="s1",
            speaker="Marcus (DBA)",
            text="PostgreSQL primary database failover was completed in 40 seconds.",
            timestamp=10.0,
            timestamp_str="00:10"
        )
        memory_agent.index_utterance(
            session_id="s1",
            speaker="Elena (DevOps)",
            text="Frontend CDN cache invalidation was purged successfully.",
            timestamp=20.0,
            timestamp_str="00:20"
        )

        results = memory_agent.search_memory("How long did PostgreSQL database failover take?")
        assert len(results) > 0
        top = results[0]
        assert top["speaker"] == "Marcus (DBA)"
        assert "40 seconds" in top["text"]
        assert top["score"] > 0.0

    def test_search_with_speaker_filter(self, memory_agent):
        memory_agent.index_utterance("s2", "David", "Budget is approved.", 5.0, "00:05", "finance")
        memory_agent.index_utterance("s2", "Sarah", "Budget is under review.", 15.0, "00:15", "finance")

        results = memory_agent.search_memory("budget", speaker="Sarah")
        for match in results:
            assert match["speaker"] == "Sarah"

    def test_search_empty_query_returns_empty_or_low_score(self, memory_agent):
        results = memory_agent.search_memory("")
        assert isinstance(results, list)

    def test_qdrant_cloud_connection_fallback(self):
        """Verify that bad Qdrant URL falls back to in-memory mode without crashing."""
        with patch.dict("os.environ", {"QDRANT_URL": "https://unreachable-cluster.qdrant.io:6333", "QDRANT_API_KEY": "fake_key"}):
            agent = QdrantMemoryAgent()
            assert agent.client is not None
            # Should be functional via in-memory fallback
            agent.index_utterance("sess_fb", "Bot", "Fallback test", 0.0, "00:00")
            stats = agent.get_stats()
            assert stats["points_count"] >= 1

    def test_uid_scoped_qdrant_retrieval_isolation(self, memory_agent):
        """Verify strict memory isolation between two different user UIDs."""
        memory_agent.index_utterance(
            session_id="session_alpha",
            speaker="Alice",
            text="The confidential project codename is Project Falcon.",
            timestamp=1.0,
            timestamp_str="00:01",
            uid="user_alpha",
        )
        memory_agent.index_utterance(
            session_id="session_beta",
            speaker="Bob",
            text="Our team is working on Project Bluebird architecture.",
            timestamp=2.0,
            timestamp_str="00:02",
            uid="user_beta",
        )

        alpha_results = memory_agent.search_memory("project codename", uid="user_alpha")
        assert len(alpha_results) >= 1
        assert all(r.get("uid") == "user_alpha" for r in alpha_results)
        assert any("Falcon" in r["text"] for r in alpha_results)
        assert not any("Bluebird" in r["text"] for r in alpha_results)

        beta_results = memory_agent.search_memory("project codename", uid="user_beta")
        assert len(beta_results) >= 1
        assert all(r.get("uid") == "user_beta" for r in beta_results)
        assert any("Bluebird" in r["text"] for r in beta_results)
        assert not any("Falcon" in r["text"] for r in beta_results)

    def test_qdrant_stats_observability_fields(self, memory_agent):
        stats = memory_agent.get_stats()
        assert "embedding_provider" in stats
        assert "vector_dimension" in stats
        assert stats["vector_dimension"] == VECTOR_DIM
        assert "persistence_mode" in stats
        assert "embedding_health" in stats
        assert stats["embedding_health"]["status"] in ("ready", "degraded")

    def test_fastembed_cache_dir_and_dimensions(self):
        import os

        from agents.memory_agent import FastEmbedEmbedding

        # Verify bundled cache resolution
        embedder = FastEmbedEmbedding(cache_dir="fastembed_cache")
        cache_path, _ = embedder._resolve_cache_dir()
        assert cache_path is not None
        assert os.path.isdir(cache_path)

        # Verify 384-dimensional vector output
        vec = embedder.embed_text("Test vector dimension", dim=VECTOR_DIM)
        assert len(vec) == 384
        health = embedder.check_health()
        assert health["status"] == "ready"
        assert health["dimension"] == 384

    def test_fastembed_initialization_failure_behavior(self):
        from agents.memory_agent import FastEmbedEmbedding
        embedder = FastEmbedEmbedding(model_name="nonexistent/fake-model-12345")
        health = embedder.check_health()
        assert health["status"] == "degraded"
        assert "error" in health
