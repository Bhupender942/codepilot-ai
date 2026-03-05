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
    """Return a (mock_session, mock_tokenizer) pair for the ONNX model."""
    mock_session = MagicMock()
    mock_tokenizer = MagicMock()

    def _run(output_names, feed):
        batch_size = feed["input_ids"].shape[0]
        seq_len = feed["input_ids"].shape[1]
        last_hidden_state = np.full((batch_size, seq_len, dims), 0.1, dtype=np.float32)
        return [last_hidden_state]

    mock_session.run.side_effect = _run

    def _encode_batch(texts):
        encodings = []
        for _ in texts:
            enc = MagicMock()
            enc.ids = [1] * 128
            enc.attention_mask = [1] * 128
            encodings.append(enc)
        return encodings

    mock_tokenizer.encode_batch.side_effect = _encode_batch
    return (mock_session, mock_tokenizer)


def _reset_model_singleton():
    """Clear the cached model singleton between tests."""
    embeddings_module._session = None
    embeddings_module._tokenizer = None


# ---------------------------------------------------------------------------
# embed_query tests
# ---------------------------------------------------------------------------


def test_embed_query_returns_vector():
    """embed_query returns a list of floats when model is available."""
    _reset_model_singleton()
    mock_model = _make_mock_model(384)

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
    """embed_query falls back to zero vector if encoding raises."""
    _reset_model_singleton()

    with patch("app.services.embeddings._encode_texts", side_effect=RuntimeError("ONNX error")):
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
    """embed_chunks falls back to zero vectors if encoding raises."""
    _reset_model_singleton()

    chunks = [{"id": "c1", "text": "def x(): pass"}]
    with patch("app.services.embeddings._encode_texts", side_effect=RuntimeError("encoding failed")):
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
    mock_session = MagicMock()
    mock_tokenizer = MagicMock()

    # Pre-populate the cache to simulate an already-loaded model
    embeddings_module._session = mock_session
    embeddings_module._tokenizer = mock_tokenizer

    first = embeddings_module.get_model()
    second = embeddings_module.get_model()

    assert first == second


def test_model_singleton_caches_after_load():
    """After the first successful load, subsequent calls skip re-loading."""
    _reset_model_singleton()
    mock_session = MagicMock()
    mock_tokenizer = MagicMock()
    embeddings_module._session = mock_session
    embeddings_module._tokenizer = mock_tokenizer

    result = embeddings_module.get_model()
    assert result == (mock_session, mock_tokenizer)
