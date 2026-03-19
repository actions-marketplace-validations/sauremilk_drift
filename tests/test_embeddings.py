"""Tests for the embedding service (graceful degradation, caching, similarity)."""

from __future__ import annotations

import numpy as np
import pytest

from drift.embeddings import (  # noqa: E501
    _EMBEDDINGS_AVAILABLE,
    EmbeddingService,
    get_embedding_service,
)

# ---------------------------------------------------------------------------
# Graceful degradation without sentence-transformers
# ---------------------------------------------------------------------------


class TestEmbeddingServiceDegraded:
    """Tests that run with or without sentence-transformers installed."""

    def test_get_embedding_service_without_deps(self):
        if not _EMBEDDINGS_AVAILABLE:
            svc = get_embedding_service()
            assert svc is None
        else:
            svc = get_embedding_service()
            assert isinstance(svc, EmbeddingService)

    def test_cosine_similarity_identical(self):
        svc = EmbeddingService()
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert svc.cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-5)

    def test_cosine_similarity_orthogonal(self):
        svc = EmbeddingService()
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert svc.cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-5)

    def test_cosine_similarity_zero_vector(self):
        svc = EmbeddingService()
        a = np.array([1.0, 2.0], dtype=np.float32)
        z = np.array([0.0, 0.0], dtype=np.float32)
        assert svc.cosine_similarity(a, z) == 0.0

    def test_build_index_returns_none_without_vectors(self):
        svc = EmbeddingService()
        assert svc.build_index([]) is None

    def test_build_index_and_search(self):
        svc = EmbeddingService()
        vecs = [
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0, 0.0], dtype=np.float32),
            np.array([0.99, 0.1, 0.0], dtype=np.float32),
        ]
        index = svc.build_index(vecs)
        assert index is not None

        results = svc.search_index(index, vecs[0], top_k=2)
        indices = [r[0] for r in results]
        assert 0 in indices
        assert 2 in indices

    def test_embed_text_returns_none_without_model(self):
        if not _EMBEDDINGS_AVAILABLE:
            svc = EmbeddingService()
            result = svc.embed_text("hello world")
            assert result is None


# ---------------------------------------------------------------------------
# Integration tests (only run if sentence-transformers is installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _EMBEDDINGS_AVAILABLE,
    reason="sentence-transformers not installed",
)
class TestEmbeddingServiceWithModel:
    def test_embed_text_shape(self):
        svc = EmbeddingService(model_name="all-MiniLM-L6-v2")
        vec = svc.embed_text("test function that processes payments")
        assert vec is not None
        assert vec.shape == (384,)

    def test_embed_texts_batch(self):
        svc = EmbeddingService(model_name="all-MiniLM-L6-v2")
        texts = ["payment processing", "database query", "HTTP routing"]
        vecs = svc.embed_texts(texts)
        assert len(vecs) == 3
        for v in vecs:
            assert v is not None
            assert v.shape == (384,)

    def test_similar_texts_high_similarity(self):
        svc = EmbeddingService(model_name="all-MiniLM-L6-v2")
        a = svc.embed_text("process payment transaction")
        b = svc.embed_text("handle payment processing")
        c = svc.embed_text("create database migration")
        sim_ab = svc.cosine_similarity(a, b)
        sim_ac = svc.cosine_similarity(a, c)
        # Payment-related texts should be more similar to each other
        assert sim_ab > sim_ac
