import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chunk, File, Repo
from app.schemas import RepoConnect, RepoResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])


def _repo_response(repo: Repo, db: Session) -> RepoResponse:
    """Build a RepoResponse enriched with file_count and chunk_count."""
    file_count: int = (
        db.query(func.count(File.id))
        .filter(File.repo_id == repo.id)
        .scalar() or 0
    )
    chunk_count: int = (
        db.query(func.count(Chunk.id))
        .join(File, Chunk.file_id == File.id)
        .filter(File.repo_id == repo.id)
        .scalar() or 0
    )
    data = RepoResponse.model_validate(repo)
    data.file_count = file_count
    data.chunk_count = chunk_count
    return data


def _build_repo_responses(repos: list[Repo], db: Session) -> list[RepoResponse]:
    """Build RepoResponse list with file/chunk counts using batch queries."""
    if not repos:
        return []

    repo_ids = [r.id for r in repos]

    # Single query for all file counts
    file_counts_rows = (
        db.query(File.repo_id, func.count(File.id).label("cnt"))
        .filter(File.repo_id.in_(repo_ids))
        .group_by(File.repo_id)
        .all()
    )
    file_counts: dict[str, int] = {row.repo_id: row.cnt for row in file_counts_rows}

    # Single query for all chunk counts
    chunk_counts_rows = (
        db.query(File.repo_id, func.count(Chunk.id).label("cnt"))
        .join(Chunk, Chunk.file_id == File.id)
        .filter(File.repo_id.in_(repo_ids))
        .group_by(File.repo_id)
        .all()
    )
    chunk_counts: dict[str, int] = {row.repo_id: row.cnt for row in chunk_counts_rows}

    results: list[RepoResponse] = []
    for repo in repos:
        data = RepoResponse.model_validate(repo)
        data.file_count = file_counts.get(repo.id, 0)
        data.chunk_count = chunk_counts.get(repo.id, 0)
        results.append(data)
    return results


@router.post("/connect", response_model=RepoResponse, status_code=201)
def connect_repo(body: RepoConnect, db: Session = Depends(get_db)) -> RepoResponse:
    """Register a new repository."""
    existing = db.query(Repo).filter(Repo.git_url == body.git_url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Repository already registered")

    repo = Repo(
        name=body.name,
        git_url=body.git_url,
        default_branch=body.default_branch,
    )
    db.add(repo)
    try:
        db.commit()
        db.refresh(repo)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create repo: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create repository") from exc

    return _repo_response(repo, db)


@router.get("", response_model=list[RepoResponse], include_in_schema=False)
@router.get("/", response_model=list[RepoResponse])
def list_repos(db: Session = Depends(get_db)) -> list[RepoResponse]:
    """List all registered repositories."""
    repos = db.query(Repo).order_by(Repo.created_at.desc()).all()
    return _build_repo_responses(repos, db)


@router.delete("/{repo_id}")
def delete_repo(repo_id: str, db: Session = Depends(get_db)) -> dict:
    """Delete a repository and all related data."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        # Cascade delete handles files/chunks via relationship config.
        # Also remove any vector store data.
        from app.services.vector_store import get_vector_store
        try:
            get_vector_store().delete_repo(repo_id)
        except Exception as exc:
            logger.warning("Could not delete vectors for repo %s: %s", repo_id, exc)

        db.delete(repo)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to delete repo %s: %s", repo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete repository") from exc

    return {"deleted": repo_id}
