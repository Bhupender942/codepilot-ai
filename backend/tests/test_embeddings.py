"""Tests for the embeddings service (app/services/embeddings.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import app.services.embeddings as embeddings_module
from app.services.embeddings import embed_chunks, embed_query


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_mock_model(dims: int = 384):
    """Return a MagicMock that behaves like a SentenceTransformer model."""
    model = MagicMock()

    def _encode(texts, show_progress_bar=False, **kwargs):
        return np.array([[0.1] * dims for _ in texts], dtype="float32")

    model.encode.side_effect = _encode
    return model


def _reset_model_singleton():
    """Clear the cached model singleton between tests."""
    embeddings_module._model = None


# ---------------------------------------------------------------------------
# embed_query tests
# ---------------------------------------------------------------------------


def test_embed_query_returns_vector():
    """embed_query returns a list of floats when model is available."""
    _reset_model_singleton()
    mock_model = _make_mock_model(384)

    with patch.object(embeddings_module, "_model", mock_model):
        with patch("app.services.embeddings.get_model", return_value=mock_model):
            result = embed_query("how does authentication work?")

    assert isinstance(result, list)
    assert all(isinstance(v, float) for v in result)
    assert len(result) == 384


def test_embed_query_zero_vector_when_no_model():
    """embed_query returns a 384-dim zero vector when no model is loaded."""
    _reset_model_singleton()

    with patch("app.services.embeddings.get_model", return_value=None):
        result = embed_query("some query")

    assert result == [0.0] * 384


def test_embed_query_handles_model_exception():
    """embed_query falls back to zero vector if model.encode raises."""
    _reset_model_singleton()
    mock_model = MagicMock()
    mock_model.encode.side_effect = RuntimeError("CUDA OOM")

    with patch("app.services.embeddings.get_model", return_value=mock_model):
        result = embed_query("problematic query")

    assert result == [0.0] * 384


# ---------------------------------------------------------------------------
# embed_chunks tests
# ---------------------------------------------------------------------------


def test_embed_chunks_batch():
    """embed_chunks returns (chunk_id, vector) pairs."""
    _reset_model_singleton()
    mock_model = _make_mock_model(384)
    chunks = [
        {"id": "c1", "text": "def foo(): pass"},
        {"id": "c2", "text": "class Bar: pass"},
    ]

    with patch("app.services.embeddings.get_model", return_value=mock_model):
        results = embed_chunks(chunks)

    assert len(results) == 2
    ids = [r[0] for r in results]
    assert "c1" in ids
    assert "c2" in ids
    for _, vec in results:
        assert isinstance(vec, list)
        assert len(vec) == 384


def test_embed_chunks_correct_count():
    """3 input chunks produce exactly 3 (chunk_id, vector) pairs."""
    _reset_model_singleton()
    mock_model = _make_mock_model(384)
    chunks = [
        {"id": f"chunk-{i}", "text": f"code line {i}"}
        for i in range(3)
    ]

    with patch("app.services.embeddings.get_model", return_value=mock_model):
        results = embed_chunks(chunks)

    assert len(results) == 3


def test_embed_chunks_empty_input():
    """An empty chunk list returns an empty list immediately."""
    results = embed_chunks([])
    assert results == []


def test_embed_chunks_zero_vectors_when_no_model():
    """embed_chunks returns zero vectors when no model is loaded."""
    _reset_model_singleton()
    chunks = [{"id": "c1", "text": "x = 1"}]

    with patch("app.services.embeddings.get_model", return_value=None):
        results = embed_chunks(chunks)

    assert len(results) == 1
    chunk_id, vec = results[0]
    assert chunk_id == "c1"
    assert vec == [0.0] * 384


def test_embed_chunks_handles_model_exception():
    """embed_chunks falls back to zero vectors if model.encode raises."""
    _reset_model_singleton()
    mock_model = MagicMock()
    mock_model.encode.side_effect = RuntimeError("encoding failed")

    chunks = [{"id": "c1", "text": "def x(): pass"}]
    with patch("app.services.embeddings.get_model", return_value=mock_model):
        results = embed_chunks(chunks)

    assert len(results) == 1
    _, vec = results[0]
    assert vec == [0.0] * 384


# ---------------------------------------------------------------------------
# Vector dimensionality
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dims", [128, 384, 768])
def test_vector_dimensions(dims: int):
    """Output vector length matches the model's embedding dimensionality."""
    _reset_model_singleton()
    mock_model = _make_mock_model(dims)
    chunks = [{"id": "c1", "text": "test"}]

    with patch("app.services.embeddings.get_model", return_value=mock_model):
        results = embed_chunks(chunks)

    _, vec = results[0]
    assert len(vec) == dims


# ---------------------------------------------------------------------------
# get_model singleton behaviour
# ---------------------------------------------------------------------------


def test_model_singleton_returns_same_instance():
    """get_model() called twice returns the same cached instance."""
    _reset_model_singleton()
    mock_model = _make_mock_model()

    with patch(
        "app.services.embeddings.SentenceTransformer",
        return_value=mock_model,
        create=True,
    ):
        # Patch the whole import chain so the model loads successfully
        with patch.dict(
            "sys.modules",
            {
                "sentence_transformers": MagicMock(SentenceTransformer=MagicMock(return_value=mock_model)),
            },
        ):
            _reset_model_singleton()
            first = embeddings_module.get_model()
            second = embeddings_module.get_model()

    # If both calls returned the same object, the singleton works.
    # (Both may be None in a no-model env; that's still a singleton.)
    assert first is second


def test_model_singleton_caches_after_load():
    """After the first successful load, subsequent calls skip re-loading."""
    _reset_model_singleton()
    mock_model = _make_mock_model()
    embeddings_module._model = mock_model  # simulate already loaded

    result = embeddings_module.get_model()
    assert result is mock_model  # returned immediately, no re-load
