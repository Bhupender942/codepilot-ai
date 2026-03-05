"""Tests for the ingestion service (app/services/ingestion.py)."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import File, Repo
from app.utils.language_detect import detect_language, is_binary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tree(base: Path, structure: dict) -> None:
    """Recursively create files/dirs from a dict.

    Keys are names; values are either str content (file) or a nested dict (dir).
    """
    for name, content in structure.items():
        path = base / name
        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            _make_tree(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# File-walking tests
# ---------------------------------------------------------------------------


def test_walk_files_basic(db_session: Session, test_repo: Repo):
    """Files in a plain directory tree are detected and returned."""
    from app.services.ingestion import _walk_and_upsert

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_tree(
            root,
            {
                "main.py": "def main(): pass\n",
                "utils.py": "def helper(): return 1\n",
                "README.md": "# Project\n",
            },
        )
        results = _walk_and_upsert(test_repo.id, root, db_session)

    paths = {r[1] for r in results}
    assert "main.py" in paths
    assert "utils.py" in paths
    assert "README.md" in paths
    assert len(results) == 3


def test_skip_ignored_patterns(db_session: Session, test_repo: Repo):
    """Directories like .git and node_modules are skipped entirely."""
    from app.services.ingestion import _walk_and_upsert

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_tree(
            root,
            {
                "app.py": "x = 1\n",
                ".git": {"HEAD": "ref: refs/heads/main\n"},
                "node_modules": {"lodash.js": "// lodash\n"},
                "__pycache__": {"app.cpython-312.pyc": ""},
                ".venv": {"activate": "# venv\n"},
                "build": {"output.min.js": "var a=1;\n"},
            },
        )
        results = _walk_and_upsert(test_repo.id, root, db_session)

    paths = {r[1] for r in results}
    assert paths == {"app.py"}


def test_skip_binary_extensions(db_session: Session, test_repo: Repo):
    """Files with binary extensions (.pyc, .png, .exe, etc.) are skipped."""
    from app.services.ingestion import _walk_and_upsert

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_tree(
            root,
            {
                "script.py": "pass\n",
                "icon.png": "fake-png",
                "lib.so": "fake-so",
                "archive.zip": "fake-zip",
                "bytecode.pyc": "fake-pyc",
            },
        )
        results = _walk_and_upsert(test_repo.id, root, db_session)

    paths = {r[1] for r in results}
    assert "script.py" in paths
    assert not any(p.endswith((".png", ".so", ".zip", ".pyc")) for p in paths)


def test_skip_true_binary_files(db_session: Session, test_repo: Repo):
    """Files containing null bytes are detected as binary and skipped."""
    from app.services.ingestion import _walk_and_upsert

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "binary_data.bin").write_bytes(b"some\x00binary\x00data")
        (root / "text_file.py").write_text("x = 1\n", encoding="utf-8")
        results = _walk_and_upsert(test_repo.id, root, db_session)

    paths = {r[1] for r in results}
    assert "text_file.py" in paths
    assert "binary_data.bin" not in paths


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected_language",
    [
        ("script.py", "python"),
        ("app.js", "javascript"),
        ("component.ts", "typescript"),
        ("Main.java", "java"),
        ("main.go", "go"),
        ("lib.rs", "rust"),
        ("prog.c", "c"),
        ("style.css", "css"),
        ("config.yaml", "yaml"),
        ("data.json", "json"),
    ],
)
def test_language_detection(filename: str, expected_language: str):
    """detect_language maps extensions to the correct language string."""
    assert detect_language(filename) == expected_language


# ---------------------------------------------------------------------------
# Checksum computation
# ---------------------------------------------------------------------------


def test_checksum_computation(db_session: Session, test_repo: Repo):
    """SHA-256 checksums are computed and stored on File records."""
    from app.services.ingestion import _walk_and_upsert

    content = "def foo(): pass\n"
    expected_checksum = hashlib.sha256(content.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "foo.py").write_text(content, encoding="utf-8")
        _walk_and_upsert(test_repo.id, root, db_session)

    file_record = db_session.query(File).filter(File.path == "foo.py").first()
    assert file_record is not None
    assert file_record.checksum == expected_checksum


def test_checksum_updates_on_re_ingest(db_session: Session, test_repo: Repo):
    """Re-ingesting a changed file updates the stored checksum."""
    from app.services.ingestion import _walk_and_upsert

    content_v1 = "x = 1\n"
    content_v2 = "x = 999\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        filepath = root / "foo.py"

        filepath.write_text(content_v1, encoding="utf-8")
        _walk_and_upsert(test_repo.id, root, db_session)
        # Expire the identity map so the next query fetches fresh data from DB
        db_session.expire_all()
        first_checksum = (
            db_session.query(File)
            .filter(File.repo_id == test_repo.id, File.path == "foo.py")
            .first()
            .checksum
        )

        filepath.write_text(content_v2, encoding="utf-8")
        _walk_and_upsert(test_repo.id, root, db_session)
        db_session.expire_all()
        second_checksum = (
            db_session.query(File)
            .filter(File.repo_id == test_repo.id, File.path == "foo.py")
            .first()
            .checksum
        )

    assert first_checksum != second_checksum


# ---------------------------------------------------------------------------
# Binary detection utility
# ---------------------------------------------------------------------------


def test_binary_detection_null_byte():
    """Files containing null bytes are flagged as binary."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
        f.write(b"hello\x00world")
        f.flush()
        assert is_binary(f.name) is True
    os.unlink(f.name)


def test_binary_detection_plain_text():
    """Plain UTF-8 text files are not flagged as binary."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".py", mode="w", encoding="utf-8"
    ) as f:
        f.write("def main(): pass\n")
        name = f.name
    assert is_binary(name) is False
    os.unlink(name)


def test_binary_detection_non_utf8():
    """Files with non-UTF-8 bytes but no null bytes are flagged as binary."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(bytes(range(128, 200)))  # Latin-1 range, not valid UTF-8
        name = f.name
    assert is_binary(name) is True
    os.unlink(name)


# ---------------------------------------------------------------------------
# ingest_repo integration (git clone mocked)
# ---------------------------------------------------------------------------


def test_ingest_repo_calls_clone_and_walk(db_session: Session, test_repo: Repo):
    """ingest_repo clones the repo and delegates to _walk_and_upsert."""
    from app.services import ingestion

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch.object(ingestion, "_clone_repo"),
            patch.object(
                ingestion,
                "_walk_and_upsert",
                return_value=[("fid", "main.py", "pass\n", "python")],
            ) as mock_walk,
            patch.dict(os.environ, {"REPOS_BASE_DIR": tmpdir}),
            patch.object(ingestion, "_REPOS_BASE_DIR", tmpdir),
        ):
            results = ingestion.ingest_repo(test_repo.id, "https://git.example.com/r.git", db_session)

    mock_walk.assert_called_once()
    assert results == [("fid", "main.py", "pass\n", "python")]
