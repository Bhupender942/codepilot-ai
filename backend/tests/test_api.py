"""API endpoint tests using FastAPI TestClient with mocked services.

All external I/O (vector store, embeddings, LLM, sandbox runner) is replaced
with lightweight mocks so tests remain fast and network-free.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(i: int = 1) -> dict:
    return {
        "chunk_id": f"chunk-{i}",
        "file_path": f"src/file{i}.py",
        "start_line": 1,
        "end_line": 20,
        "text": f"def func_{i}(): pass",
        "score": 0.9,
        "language": "python",
    }


def _connect_repo(client: TestClient, suffix: str = "") -> dict:
    """POST /api/repos/connect and return the response JSON."""
    resp = client.post(
        "/api/repos/connect",
        json={
            "name": f"test-repo{suffix}",
            "git_url": f"https://github.com/example/repo{suffix}.git",
            "default_branch": "main",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# System endpoints
# ===========================================================================


def test_health_endpoint(client: TestClient):
    """GET /health returns 200 and {"status": "ok"}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient):
    """GET / returns 200 and a message containing 'CodePilot'."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "CodePilot" in data["message"]


# ===========================================================================
# Repos endpoints
# ===========================================================================


def test_connect_repo(client: TestClient):
    """POST /api/repos/connect with a valid body returns 201 and a repo id."""
    resp = client.post(
        "/api/repos/connect",
        json={
            "name": "my-repo",
            "git_url": "https://github.com/acme/my-repo.git",
            "default_branch": "main",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "my-repo"
    assert data["git_url"] == "https://github.com/acme/my-repo.git"


def test_connect_repo_duplicate_returns_409(client: TestClient):
    """Registering the same git_url twice returns 409 Conflict."""
    payload = {
        "name": "dup-repo",
        "git_url": "https://github.com/acme/dup-repo.git",
        "default_branch": "main",
    }
    client.post("/api/repos/connect", json=payload)
    resp = client.post("/api/repos/connect", json=payload)
    assert resp.status_code == 409


def test_list_repos(client: TestClient):
    """GET /api/repos/ returns 200 and a JSON list."""
    _connect_repo(client, suffix="-list-1")
    _connect_repo(client, suffix="-list-2")

    resp = client.get("/api/repos/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_list_repos_empty(client: TestClient):
    """GET /api/repos/ returns an empty list when no repos are registered."""
    resp = client.get("/api/repos/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_delete_repo(client: TestClient):
    """DELETE /api/repos/{id} returns 200 and confirms deletion."""
    repo = _connect_repo(client, suffix="-delete")
    repo_id = repo["id"]

    resp = client.delete(f"/api/repos/{repo_id}")
    assert resp.status_code == 200
    assert resp.json().get("deleted") == repo_id


def test_delete_nonexistent_repo_returns_404(client: TestClient):
    """DELETE /api/repos/{id} with an unknown id returns 404."""
    resp = client.delete("/api/repos/nonexistent-id")
    assert resp.status_code == 404


# ===========================================================================
# Index endpoints
# ===========================================================================


def test_index_start(client: TestClient):
    """POST /api/index/start returns a job_id."""
    repo = _connect_repo(client, suffix="-idx")

    with (
        patch("app.routers.index._run_indexing"),
    ):
        resp = client.post("/api/index/start", json={"repo_id": repo["id"]})

    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["job_id"]


def test_index_start_unknown_repo(client: TestClient):
    """POST /api/index/start with unknown repo_id returns 404."""
    resp = client.post("/api/index/start", json={"repo_id": "does-not-exist"})
    assert resp.status_code == 404


def test_index_status(client: TestClient):
    """GET /api/index/status/{job_id} returns status for a known job."""
    repo = _connect_repo(client, suffix="-status")

    with patch("app.routers.index._run_indexing"):
        start_resp = client.post("/api/index/start", json={"repo_id": repo["id"]})

    job_id = start_resp.json()["job_id"]
    status_resp = client.get(f"/api/index/status/{job_id}")

    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["job_id"] == job_id
    assert "status" in data


def test_index_status_unknown_job(client: TestClient):
    """GET /api/index/status/{job_id} with unknown id returns 404."""
    resp = client.get("/api/index/status/unknown-job-id")
    assert resp.status_code == 404


# ===========================================================================
# Query endpoint
# ===========================================================================


def test_query(client: TestClient):
    """POST /api/query/ returns an answer and citations list."""
    repo = _connect_repo(client, suffix="-query")

    mock_orchestrator = MagicMock()
    mock_orchestrator.assemble_prompt.return_value = ("system msg", "user msg")
    mock_orchestrator.generate = AsyncMock(return_value="The answer is 42.")

    with (
        patch("app.routers.query.retriever.retrieve", return_value=[_make_chunk()]),
        patch("app.routers.query.get_orchestrator", return_value=mock_orchestrator),
    ):
        resp = client.post(
            "/api/query/",
            json={"repo_id": repo["id"], "question": "What does main do?", "top_k": 5},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["answer"] == "The answer is 42."
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) == 1


def test_query_no_results(client: TestClient):
    """POST /api/query/ with no relevant chunks returns a graceful message."""
    repo = _connect_repo(client, suffix="-query-empty")

    with patch("app.routers.query.retriever.retrieve", return_value=[]):
        resp = client.post(
            "/api/query/",
            json={"repo_id": repo["id"], "question": "unknown question"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["citations"] == []


def test_query_empty_question(client: TestClient):
    """POST /api/query/ with an empty question returns 422."""
    repo = _connect_repo(client, suffix="-query-empty-q")
    resp = client.post(
        "/api/query/",
        json={"repo_id": repo["id"], "question": "   "},
    )
    assert resp.status_code == 422


# ===========================================================================
# Diagnose endpoint
# ===========================================================================


def test_diagnose(client: TestClient):
    """POST /api/diagnose/ returns a suspects list."""
    repo = _connect_repo(client, suffix="-diag")

    mock_orchestrator = MagicMock()
    mock_orchestrator.assemble_prompt.return_value = ("system", "user")
    mock_orchestrator.generate = AsyncMock(
        return_value=(
            "SUSPECT: src/auth.py:10-20 PROBABILITY:0.9 REASON:Missing null check\n"
        )
    )

    with (
        patch("app.routers.diagnose.retriever.retrieve", return_value=[_make_chunk()]),
        patch("app.routers.diagnose.get_orchestrator", return_value=mock_orchestrator),
    ):
        resp = client.post(
            "/api/diagnose/",
            json={
                "repo_id": repo["id"],
                "error_text": "NullPointerException in auth",
                "stacktrace": "at src/auth.py:15",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "suspects" in data
    assert isinstance(data["suspects"], list)
    assert len(data["suspects"]) >= 1


def test_diagnose_no_chunks(client: TestClient):
    """POST /api/diagnose/ with no matching chunks returns empty suspects."""
    repo = _connect_repo(client, suffix="-diag-empty")

    with patch("app.routers.diagnose.retriever.retrieve", return_value=[]):
        resp = client.post(
            "/api/diagnose/",
            json={"repo_id": repo["id"], "error_text": "some error"},
        )

    assert resp.status_code == 200
    assert resp.json()["suspects"] == []


# ===========================================================================
# Patch propose endpoint
# ===========================================================================


def test_patch_propose(client: TestClient):
    """POST /api/patch/propose returns a patch with raw_diff and explanation."""
    repo = _connect_repo(client, suffix="-patch")

    raw_diff = (
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,3 +1,4 @@\n"
        " def foo():\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.assemble_prompt.return_value = ("system", "user")
    mock_orchestrator.generate = AsyncMock(
        return_value=f"This fixes the return value.\n\n{raw_diff}"
    )

    with (
        patch("app.routers.patch.retriever.retrieve", return_value=[_make_chunk()]),
        patch("app.routers.patch.get_orchestrator", return_value=mock_orchestrator),
    ):
        resp = client.post(
            "/api/patch/propose",
            json={
                "repo_id": repo["id"],
                "issue_description": "foo returns wrong value",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "patch_id" in data
    assert "raw_diff" in data
    assert "explanation" in data
    assert isinstance(data["hunks"], list)
    assert 0.0 <= data["confidence"] <= 1.0


def test_patch_propose_empty_description(client: TestClient):
    """POST /api/patch/propose with empty issue_description returns 422."""
    repo = _connect_repo(client, suffix="-patch-empty")
    resp = client.post(
        "/api/patch/propose",
        json={"repo_id": repo["id"], "issue_description": "   "},
    )
    assert resp.status_code == 422


def test_patch_propose_unknown_repo(client: TestClient):
    """POST /api/patch/propose with unknown repo_id returns 404."""
    resp = client.post(
        "/api/patch/propose",
        json={"repo_id": "no-such-repo", "issue_description": "fix it"},
    )
    assert resp.status_code == 404


# ===========================================================================
# Sandbox endpoint
# ===========================================================================


def test_sandbox_run(client: TestClient):
    """POST /api/sandbox/run returns a job_id."""
    repo = _connect_repo(client, suffix="-sandbox")

    with patch("app.routers.sandbox._run_sandbox_task"):
        resp = client.post(
            "/api/sandbox/run",
            json={"patch_id": "some-patch-id", "repo_id": repo["id"]},
        )

    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_sandbox_run_unknown_repo(client: TestClient):
    """POST /api/sandbox/run with unknown repo_id returns 404."""
    resp = client.post(
        "/api/sandbox/run",
        json={"patch_id": "p1", "repo_id": "no-such-repo"},
    )
    assert resp.status_code == 404


# ===========================================================================
# Docs generation endpoint
# ===========================================================================


def test_docs_generate(client: TestClient):
    """POST /api/docs_gen/generate returns a job_id with 202 status."""
    with patch("app.routers.docs._run_doc_generation"):
        resp = client.post(
            "/api/docs_gen/generate",
            json={"repo_id": "any-repo-id", "file_path": None},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert "status" in data
