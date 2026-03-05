"""Tests for the retriever service (app/services/retriever.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.retriever import retrieve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vs_hit(chunk_id: str, file_path: str, score: float, language: str = "python") -> dict:
    """Return a dict that matches what VectorStore.search() returns."""
    return {
        "chunk_id": chunk_id,
        "file_path": file_path,
        "start_line": 1,
        "end_line": 10,
        "language": language,
        "score": score,
    }


def _patch_retrieve(hits: list[dict], query_vector: list[float] | None = None):
    """Return a context-manager tuple that mocks embed_query + get_vector_store."""
    if query_vector is None:
        query_vector = [0.1] * 384

    mock_vs = MagicMock()
    mock_vs.search.return_value = hits

    embed_patch = patch(
        "app.services.retriever.embeddings.embed_query",
        return_value=query_vector,
    )
    vs_patch = patch(
        "app.services.retriever.vector_store.get_vector_store",
        return_value=mock_vs,
    )
    return embed_patch, vs_patch


# ---------------------------------------------------------------------------
# Basic retrieval
# ---------------------------------------------------------------------------


def test_retrieve_returns_results():
    """Retriever returns up to top_k results when the vector store has hits."""
    hits = [_make_vs_hit(f"c{i}", f"file{i}.py", score=0.9 - i * 0.05) for i in range(6)]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("what does main do?", repo_id="repo-1", top_k=3)

    assert len(results) <= 3
    assert all("chunk_id" in r for r in results)


def test_retrieve_empty_query_returns_empty():
    """An empty / whitespace-only query returns an empty list immediately."""
    ep, vsp = _patch_retrieve([])

    with ep, vsp:
        results = retrieve("   ", repo_id="repo-1")

    assert results == []


def test_empty_vector_store_returns_empty():
    """If the vector store returns no candidates, retrieve returns []."""
    ep, vsp = _patch_retrieve([])

    with ep, vsp:
        results = retrieve("find the bug", repo_id="repo-1")

    assert results == []


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_reranking_by_score():
    """Chunks with higher combined score appear first in the result list."""
    hits = [
        _make_vs_hit("low", "low.py", score=0.3),
        _make_vs_hit("high", "high.py", score=0.95),
        _make_vs_hit("mid", "mid.py", score=0.6),
    ]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("query", repo_id="repo-1", top_k=3)

    # The highest-score chunk should come first
    assert results[0]["chunk_id"] == "high"


def test_keyword_boost():
    """A chunk whose text contains all query terms gets a higher combined score."""
    hits = [
        _make_vs_hit("no_match", "a.py", score=0.7),
        _make_vs_hit("full_match", "b.py", score=0.7),
    ]

    ep, vsp = _patch_retrieve(hits)
    with ep, vsp:
        mock_vs = MagicMock()
        mock_vs.search.return_value = hits

        # Provide a db_session that returns chunks with appropriate text
        db_session = MagicMock()
        no_match_chunk = MagicMock()
        no_match_chunk.text = "unrelated code here"
        no_match_chunk.file = MagicMock()
        no_match_chunk.file.path = "a.py"
        no_match_chunk.start_line = 1
        no_match_chunk.end_line = 10

        full_match_chunk = MagicMock()
        full_match_chunk.text = "authentication login password verify"
        full_match_chunk.file = MagicMock()
        full_match_chunk.file.path = "b.py"
        full_match_chunk.start_line = 1
        full_match_chunk.end_line = 10

        db_session.query.return_value.filter.return_value.all.return_value = [
            no_match_chunk,
            full_match_chunk,
        ]
        # Mimic dict-like access for chunk id lookup
        no_match_chunk.id = "no_match"
        full_match_chunk.id = "full_match"

        with patch(
            "app.services.retriever.embeddings.embed_query",
            return_value=[0.1] * 384,
        ):
            with patch(
                "app.services.retriever.vector_store.get_vector_store",
                return_value=mock_vs,
            ):
                results = retrieve(
                    "authentication login password verify",
                    repo_id="repo-1",
                    top_k=2,
                    db_session=db_session,
                )

    # full_match should score higher due to keyword boost
    assert results[0]["chunk_id"] == "full_match"


def test_top_k_limit():
    """retrieve never returns more results than top_k."""
    hits = [_make_vs_hit(f"c{i}", f"f{i}.py", score=0.9 - i * 0.01) for i in range(20)]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("query", repo_id="repo-1", top_k=5)

    assert len(results) <= 5


def test_retrieve_without_db_session():
    """retrieve works without a db_session (text is empty but no error raised)."""
    hits = [_make_vs_hit("c1", "main.py", score=0.8)]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("query", repo_id="repo-1", top_k=1, db_session=None)

    assert len(results) == 1
    assert results[0]["text"] == ""  # no DB to fetch text from


# ---------------------------------------------------------------------------
# Score fields
# ---------------------------------------------------------------------------


def test_result_contains_required_fields():
    """Each result dict has all required keys."""
    required = {"chunk_id", "file_path", "start_line", "end_line", "text", "score", "language"}
    hits = [_make_vs_hit("c1", "src/foo.py", score=0.75)]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("query", repo_id="repo-1", top_k=1, db_session=None)

    assert required.issubset(results[0].keys())


def test_score_is_float_in_range():
    """Combined score for every result is a finite float between 0 and 1."""
    hits = [
        _make_vs_hit(f"c{i}", f"f{i}.py", score=s)
        for i, s in enumerate([0.0, 0.5, 1.0])
    ]
    ep, vsp = _patch_retrieve(hits)

    with ep, vsp:
        results = retrieve("query", repo_id="repo-1", top_k=10, db_session=None)

    for r in results:
        assert 0.0 <= r["score"] <= 1.0
