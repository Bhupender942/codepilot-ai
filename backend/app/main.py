from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (Alembic handles production migrations;
    # this is a convenience for local/test environments)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CodePilot API",
    version="1.0.0",
    description="AI-powered code intelligence platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — imported lazily so the app starts even if optional deps are absent
# ---------------------------------------------------------------------------
try:
    from app.routers import repos, index, query, diagnose, patch, sandbox, docs

    app.include_router(repos.router, prefix="/api")
    app.include_router(index.router, prefix="/api")
    app.include_router(query.router, prefix="/api")
    app.include_router(diagnose.router, prefix="/api")
    app.include_router(patch.router, prefix="/api")
    app.include_router(sandbox.router, prefix="/api")
    app.include_router(docs.router, prefix="/api")
except ImportError:
    # Routers not yet implemented — the core app still starts cleanly
    pass


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@app.get("/", tags=["system"])
def root():
    return {"message": "CodePilot API is running", "docs": "/docs"}
