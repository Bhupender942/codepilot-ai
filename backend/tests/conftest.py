"""
Shared pytest fixtures for the CodePilot backend test suite.

Bootstrap order (all at module level, before any test is collected):
1.  Create an in-memory SQLite engine (StaticPool – single shared connection).
2.  Import ``app.database`` – this internally creates a PostgreSQL engine object
    (no TCP connection is attempted at construction time, so no error is raised
    even when Postgres is unavailable).
3.  Swap ``app.database.engine`` and ``app.database.SessionLocal`` for the
    SQLite equivalents so that all subsequent ``from app.database import …``
    statements in routers and services pick up the test engine.
4.  Create all ORM tables in SQLite.
5.  Import the FastAPI ``app`` – at this point ``from app.database import engine``
    in ``main.py`` resolves to the test SQLite engine.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# 1. Test SQLite engine – created before any app module is imported
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# 2 & 3. Import app.database and immediately replace its module-level engine
# ---------------------------------------------------------------------------
import app.database as _db_module  # noqa: E402

_db_module.engine = TEST_ENGINE
_db_module.SessionLocal = TestSessionLocal

# ---------------------------------------------------------------------------
# 4. Register all models and create tables
# ---------------------------------------------------------------------------
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 – registers Repo, File, Chunk, Job with Base

Base.metadata.create_all(bind=TEST_ENGINE)

# ---------------------------------------------------------------------------
# 5. Import the FastAPI app (after engine swap; main.py's `from app.database
#    import engine` now resolves to TEST_ENGINE)
# ---------------------------------------------------------------------------
from app.main import app  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models import Repo, File, Chunk, Job  # noqa: E402


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def db_session() -> Session:
    """In-memory SQLite session for unit tests that interact with the ORM."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_repo(db_session: Session) -> Repo:
    """A persisted Repo instance available to tests that need DB data."""
    repo = Repo(
        name="test-repo",
        git_url="https://github.com/example/test-repo.git",
        default_branch="main",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Three representative chunk dicts usable as retriever / embedder input."""
    return [
        {
            "id": "chunk-1",
            "file_id": "file-1",
            "file_path": "src/main.py",
            "start_line": 1,
            "end_line": 20,
            "text": "def main():\n    pass",
            "tokens": 10,
            "language": "python",
        },
        {
            "id": "chunk-2",
            "file_id": "file-1",
            "file_path": "src/main.py",
            "start_line": 21,
            "end_line": 40,
            "text": "def helper():\n    return True",
            "tokens": 8,
            "language": "python",
        },
        {
            "id": "chunk-3",
            "file_id": "file-2",
            "file_path": "src/utils.py",
            "start_line": 1,
            "end_line": 15,
            "text": "class Utils:\n    pass",
            "tokens": 6,
            "language": "python",
        },
    ]


@pytest.fixture
def mock_embeddings():
    """
    A callable that matches ``SentenceTransformer.encode()``'s signature and
    returns deterministic 384-dimensional unit vectors (all components = 0.1).
    """
    import numpy as np

    fixed_vector = [0.1] * 384

    def _encode(texts, show_progress_bar: bool = False, **kwargs):
        return np.array([fixed_vector for _ in texts])

    return _encode


@pytest.fixture
def client():
    """
    FastAPI TestClient backed by in-memory SQLite with external services mocked.

    Overrides:
    * ``get_db``                                   → TestSessionLocal (SQLite)
    * ``_vector_store_instance`` singleton         → MagicMock (no Qdrant/FAISS)
    """

    def _override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db

    mock_vs = MagicMock()
    mock_vs.search.return_value = []
    mock_vs.upsert.return_value = None
    mock_vs.delete_repo.return_value = None

    with patch("app.services.vector_store._vector_store_instance", mock_vs):
        with TestClient(app, raise_server_exceptions=True) as tc:
            yield tc

    app.dependency_overrides.clear()
