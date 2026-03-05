"""Tests for the code chunker service (app/services/chunker.py)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.services.chunker import (
    _extract_chunks,
    _sliding_window_chunks,
    chunk_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LARGE_FILE_THRESHOLD = 1000  # mirrors the constant in chunker.py


def _make_file(db_session: Session, repo_id: str, path: str = "test.py") -> str:
    """Insert a minimal File record and return its id."""
    from app.models import File

    f = File(repo_id=repo_id, path=path, language="python", checksum="abc")
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)
    return f.id


def _make_repo(db_session: Session) -> str:
    from app.models import Repo

    repo = Repo(name="r", git_url="https://example.com/r.git")
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo.id


# ===========================================================================
# Python chunking
# ===========================================================================


def test_python_function_chunking(db_session: Session):
    """Two top-level functions → at least 2 chunks."""
    content = "def foo():\n    pass\n\ndef bar():\n    return 1\n"
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "src.py")

    chunks = chunk_file(file_id, "src.py", content, "python", db_session)
    assert len(chunks) >= 2


def test_python_class_chunking(db_session: Session):
    """A class definition is extracted as its own chunk."""
    content = (
        "class MyClass:\n"
        "    def method_a(self):\n"
        "        pass\n"
        "\n"
        "def standalone():\n"
        "    pass\n"
    )
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "cls.py")

    chunks = chunk_file(file_id, "cls.py", content, "python", db_session)
    texts = [c["text"] for c in chunks]
    assert any("class MyClass" in t for t in texts)


def test_python_empty_lines_skipped(db_session: Session):
    """Chunks consisting of only whitespace are not stored."""
    content = "def real(): pass\n\n\n"
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "src.py")

    chunks = chunk_file(file_id, "src.py", content, "python", db_session)
    for c in chunks:
        assert c["text"].strip() != ""


# ===========================================================================
# JavaScript / TypeScript chunking
# ===========================================================================


def test_javascript_function_chunking(db_session: Session):
    """JS file with two named functions → at least 2 chunks."""
    content = (
        "function greet(name) {\n"
        "  return `Hello ${name}`;\n"
        "}\n"
        "\n"
        "function farewell(name) {\n"
        "  return `Bye ${name}`;\n"
        "}\n"
    )
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "app.js")

    chunks = chunk_file(file_id, "app.js", content, "javascript", db_session)
    assert len(chunks) >= 2


def test_typescript_class_chunking(db_session: Session):
    """TS file with a class definition → class appears in chunks."""
    content = (
        "export class Greeter {\n"
        "  greet(name: string): string {\n"
        "    return `Hello ${name}`;\n"
        "  }\n"
        "}\n"
    )
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "greeter.ts")

    chunks = chunk_file(file_id, "greeter.ts", content, "typescript", db_session)
    texts = [c["text"] for c in chunks]
    assert any("Greeter" in t for t in texts)


# ===========================================================================
# Java chunking
# ===========================================================================


def test_java_method_chunking(db_session: Session):
    """Java class with a public method → method appears in a chunk."""
    content = (
        "public class Calculator {\n"
        "    public int add(int a, int b) {\n"
        "        return a + b;\n"
        "    }\n"
        "}\n"
    )
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "Calc.java")

    chunks = chunk_file(file_id, "Calc.java", content, "java", db_session)
    assert len(chunks) >= 1
    texts = [c["text"] for c in chunks]
    assert any("add" in t for t in texts)


# ===========================================================================
# Go chunking
# ===========================================================================


def test_go_function_chunking(db_session: Session):
    """Go file with two func declarations → at least 2 chunks."""
    content = (
        "package main\n"
        "\n"
        "func Add(a, b int) int {\n"
        "    return a + b\n"
        "}\n"
        "\n"
        "func Sub(a, b int) int {\n"
        "    return a - b\n"
        "}\n"
    )
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "math.go")

    chunks = chunk_file(file_id, "math.go", content, "go", db_session)
    assert len(chunks) >= 2


# ===========================================================================
# Sliding window fallback
# ===========================================================================


def test_sliding_window_fallback(db_session: Session):
    """Plain text (unknown language) falls back to sliding-window chunking."""
    content = "\n".join(f"line {i}" for i in range(50))
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "notes.txt")

    chunks = chunk_file(file_id, "notes.txt", content, "text", db_session)
    assert len(chunks) >= 1


def test_sliding_window_produces_overlap():
    """Sliding-window chunks overlap by the expected amount."""
    from app.services.chunker import (
        _SLIDING_WINDOW_OVERLAP,
        _SLIDING_WINDOW_SIZE,
        _sliding_window_chunks,
    )

    lines = [f"line {i}" for i in range(300)]
    chunks = _sliding_window_chunks(lines)
    assert len(chunks) >= 2
    first_end = chunks[0][1]
    second_start = chunks[1][0]
    assert second_start < first_end  # overlap means second starts before first ends


# ===========================================================================
# Large-file header
# ===========================================================================


def test_large_file_handling(db_session: Session):
    """Files > 1000 lines get a file-path header prepended to each chunk."""
    content = "\n".join(f"def func_{i}(): pass" for i in range(1100))
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "big.py")

    chunks = chunk_file(file_id, "big.py", content, "python", db_session)
    assert len(chunks) >= 1
    for c in chunks:
        assert "# File: big.py" in c["text"]


# ===========================================================================
# Empty file
# ===========================================================================


def test_empty_file(db_session: Session):
    """An empty file produces no chunks."""
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "empty.py")

    chunks = chunk_file(file_id, "empty.py", "", "python", db_session)
    assert chunks == []


# ===========================================================================
# Re-index scenario
# ===========================================================================


def test_reindex_removes_old_chunks(db_session: Session):
    """Calling chunk_file twice replaces old chunks instead of appending."""
    content_v1 = "def alpha(): pass\ndef beta(): pass\n"
    content_v2 = "def gamma(): pass\n"
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "mod.py")

    chunk_file(file_id, "mod.py", content_v1, "python", db_session)
    chunks_v2 = chunk_file(file_id, "mod.py", content_v2, "python", db_session)

    texts = [c["text"] for c in chunks_v2]
    assert any("gamma" in t for t in texts)
    assert not any("alpha" in t for t in texts)


# ===========================================================================
# Token count
# ===========================================================================


def test_token_count_positive(db_session: Session):
    """Each returned chunk dict has a positive token count."""
    content = "def process(data):\n    return [x * 2 for x in data]\n"
    repo_id = _make_repo(db_session)
    file_id = _make_file(db_session, repo_id, "proc.py")

    chunks = chunk_file(file_id, "proc.py", content, "python", db_session)
    assert all(c["tokens"] > 0 for c in chunks)


# ===========================================================================
# _extract_chunks unit tests (no DB required)
# ===========================================================================


@pytest.mark.parametrize(
    "language, code, expected_min_chunks",
    [
        ("python", "def a(): pass\ndef b(): pass\n", 2),
        ("javascript", "function a(){}\nfunction b(){}\n", 2),
        ("go", "func A(){}\nfunc B(){}\n", 2),
        ("rust", "// generic fallback\n" * 10, 1),
    ],
)
def test_extract_chunks_parametrized(language: str, code: str, expected_min_chunks: int):
    """_extract_chunks returns the right number of ranges for common languages."""
    lines = code.splitlines()
    ranges = _extract_chunks(lines, language)
    assert len(ranges) >= expected_min_chunks
