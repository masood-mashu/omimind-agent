"""
test_embeddings.py - Comprehensive Unit Tests for Modular agents.embeddings Package
Covers:
- BaseEmbeddingModel interface, batch embedding, health checks
- DeterministicSubwordEmbedding text & batch encoding
- FastEmbedEmbedding cache resolution, batch embedding, dimension verification, error resilience
- SentenceTransformerEmbedding model loading, dimension projection, fallback mechanics
- Embedding provider factory environment dispatch
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from agents.embeddings import (
    generate_semantic_embedding,
    get_embedding_provider,
)
from agents.embeddings.base import VECTOR_DIM, BaseEmbeddingModel
from agents.embeddings.deterministic import DeterministicSubwordEmbedding
from agents.embeddings.fastembed import FastEmbedEmbedding
from agents.embeddings.sentence_transformer import SentenceTransformerEmbedding


class DummyCustomEmbedding(BaseEmbeddingModel):
    provider_name = "dummy"

    def embed_text(self, text: str, dim: int = VECTOR_DIM) -> list[float]:
        return [0.5] * dim


class TestBaseEmbeddingModel:
    def test_base_embedding_batch_and_health(self):
        model = DummyCustomEmbedding()
        assert model.provider_name == "dummy"
        health = model.check_health()
        assert health["status"] == "ready"
        assert health["dimension"] == VECTOR_DIM

        batch = model.embed_batch(["alpha", "beta"], dim=64)
        assert len(batch) == 2
        assert len(batch[0]) == 64
        assert len(batch[1]) == 64


class TestDeterministicEmbedding:
    def test_embed_batch_consistency(self):
        model = DeterministicSubwordEmbedding()
        texts = ["Sprint retrospective action item", "Customer churn analysis"]
        batch = model.embed_batch(texts, dim=VECTOR_DIM)
        assert len(batch) == 2
        assert len(batch[0]) == VECTOR_DIM
        assert len(batch[1]) == VECTOR_DIM
        # Check single vs batch equivalence
        single_0 = model.embed_text(texts[0], dim=VECTOR_DIM)
        assert batch[0] == single_0

    def test_health_check(self):
        model = DeterministicSubwordEmbedding()
        health = model.check_health()
        assert health["status"] == "ready"
        assert health["provider"] == "deterministic"

    def test_stop_words_fallback_when_all_stopwords(self):
        model = DeterministicSubwordEmbedding()
        # Sentence consisting entirely of stop words
        all_stop = "what when why who"
        vec = model.embed_text(all_stop, dim=VECTOR_DIM)
        assert len(vec) == VECTOR_DIM
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-4) == 1.0


class TestFastEmbedEmbedding:
    def test_embed_batch_empty_list(self):
        model = FastEmbedEmbedding()
        assert model.embed_batch([]) == []

    def test_embed_batch_with_mock_model(self):
        model = FastEmbedEmbedding()
        mock_text_model = MagicMock()
        mock_vec_1 = [0.1] * VECTOR_DIM
        mock_vec_2 = [0.2] * VECTOR_DIM
        mock_text_model.embed.return_value = [mock_vec_1, mock_vec_2]
        model._model = mock_text_model

        batch = model.embed_batch(["text 1", "text 2"])
        assert len(batch) == 2
        assert len(batch[0]) == VECTOR_DIM
        assert len(batch[1]) == VECTOR_DIM

    def test_dimension_mismatch_raises_value_error(self):
        model = FastEmbedEmbedding()
        mock_text_model = MagicMock()
        mock_text_model.embed.return_value = iter([[0.1] * 128])
        model._model = mock_text_model

        with pytest.raises(ValueError, match="dimensions"):
            model.embed_text("test", dim=384)

    def test_batch_dimension_mismatch_raises_value_error(self):
        model = FastEmbedEmbedding()
        mock_text_model = MagicMock()
        mock_text_model.embed.return_value = [[0.1] * 128]
        model._model = mock_text_model

        with pytest.raises(ValueError, match="dimensions"):
            model.embed_batch(["test"], dim=384)

    def test_health_check_ready_and_degraded(self):
        model = FastEmbedEmbedding()
        mock_text_model = MagicMock()
        model._model = mock_text_model

        health = model.check_health()
        assert health["status"] == "ready"
        assert health["provider"] == "fastembed"

        # Simulate exception during _get_model
        model._model = None
        with patch.object(model, "_get_model", side_effect=RuntimeError("Corrupt weights")):
            health_deg = model.check_health()
            assert health_deg["status"] == "degraded"
            assert "Corrupt weights" in health_deg["error"]

    def test_resolve_cache_dir_serverless(self):
        with patch.dict(os.environ, {"VERCEL": "1", "FASTEMBED_CACHE_DIR": ""}):
            model = FastEmbedEmbedding()
            cache_path, is_local = model._resolve_cache_dir()
            assert cache_path is not None
            assert "fastembed_cache" in cache_path


class TestSentenceTransformerEmbedding:
    def test_fallback_when_import_fails(self):
        model = SentenceTransformerEmbedding()
        with patch("importlib.import_module", side_effect=ImportError("No module sentence_transformers")):
            model._model = None
            vec = model.embed_text("Fallback test sentence", dim=VECTOR_DIM)
            assert len(vec) == VECTOR_DIM
            health = model.check_health()
            assert health["status"] == "degraded"

    def test_projection_when_dimension_larger_than_target(self):
        model = SentenceTransformerEmbedding()
        mock_st = MagicMock()
        # Return 768 dimensions when target is 384
        import numpy as np
        mock_st.encode.return_value = np.array([0.5] * 768)
        model._model = mock_st

        vec = model.embed_text("High dim sentence", dim=384)
        assert len(vec) == 384
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-4) == 1.0

    def test_embed_batch_with_mock_st(self):
        model = SentenceTransformerEmbedding()
        mock_st = MagicMock()
        import numpy as np
        mock_st.encode.return_value = [np.array([0.5] * 384), np.array([0.5] * 384)]
        model._model = mock_st

        batch = model.embed_batch(["Sentence A", "Sentence B"], dim=384)
        assert len(batch) == 2
        assert len(batch[0]) == 384
        assert len(batch[1]) == 384

    def test_embed_batch_fallback_on_exception(self):
        model = SentenceTransformerEmbedding()
        mock_st = MagicMock()
        mock_st.encode.side_effect = RuntimeError("CUDA OOM")
        model._model = mock_st

        batch = model.embed_batch(["Sentence A", "Sentence B"], dim=384)
        assert len(batch) == 2
        assert len(batch[0]) == 384


class TestProviderFactory:
    def test_get_embedding_provider_deterministic(self):
        provider = get_embedding_provider()
        assert isinstance(provider, DeterministicSubwordEmbedding)

    def test_get_embedding_provider_fastembed_env(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "fastembed"}):
            provider = get_embedding_provider()
            assert isinstance(provider, FastEmbedEmbedding)

    def test_get_embedding_provider_sentence_transformers_env(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "sentence_transformers"}):
            provider = get_embedding_provider()
            assert isinstance(provider, SentenceTransformerEmbedding)

    def test_generate_semantic_embedding_helper(self):
        vec = generate_semantic_embedding("Helper function test")
        assert len(vec) == VECTOR_DIM
