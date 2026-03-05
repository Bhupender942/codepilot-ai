from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    git_url = Column(String, nullable=False)
    local_path = Column(String, nullable=True)
    default_branch = Column(String, default="main")
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("File", back_populates="repo", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    path = Column(String, nullable=False)
    language = Column(String, nullable=True)
    checksum = Column(String, nullable=True)

    repo = relationship("Repo", back_populates="files")
    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    file_id = Column(String, ForeignKey("files.id"), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)
    embedding_ref = Column(String, nullable=True)

    file = relationship("File", back_populates="chunks")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    type = Column(String, nullable=False)
    status = Column(String, default="pending")
    repo_id = Column(String, ForeignKey("repos.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
