"""
Docs Router for CodePilot.

This module provides the /generate-docs endpoint for generating
documentation for GitHub repositories using Groq API.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.documentation_service import (
    check_api_key,
    generate_repo_documentation,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/docs", tags=["documentation"])


# Request/Response models
class GenerateDocsRequest(BaseModel):
    """Request model for generating documentation."""
    repo_url: str


class GenerateDocsResponse(BaseModel):
    """Response model for documentation generation."""
    status: str
    message: str
    job_id: Optional[str] = None


class DocsResultResponse(BaseModel):
    """Response model for getting documentation results."""
    repo_url: str
    files_processed: int
    files: list
    error: Optional[str] = None


@router.post("/generate-docs", response_model=GenerateDocsResponse)
async def generate_docs(
    request: GenerateDocsRequest,
    background_tasks: BackgroundTasks,
) -> GenerateDocsResponse:
    """
    Generate documentation for a GitHub repository.
    
    This endpoint clones the repository, analyzes the code files,
    and generates documentation using Groq LLM.
    
    Args:
        request: Request containing the repository URL
        
    Returns:
        Response with status and message
    """
    # Validate API key
    if not check_api_key():
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
        )
    
    # Validate repo URL
    if not request.repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")
    
    # Basic URL validation
    if not request.repo_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid repository URL")
    
    logger.info("Starting documentation generation for: %s", request.repo_url)
    
    # Generate documentation synchronously for now
    # For production, you might want to use background tasks
    try:
        result = generate_repo_documentation(request.repo_url)
        
        if "error" in result:
            return GenerateDocsResponse(
                status="error",
                message=result.get("error", "Unknown error"),
            )
        
        return GenerateDocsResponse(
            status="success",
            message=f"Successfully generated documentation for {result['files_processed']} files",
        )
        
    except Exception as e:
        logger.error("Documentation generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Documentation generation failed: {str(e)}"
        )


@router.post("/generate-docs-async", response_model=GenerateDocsResponse)
async def generate_docs_async(
    request: GenerateDocsRequest,
    background_tasks: BackgroundTasks,
) -> GenerateDocsResponse:
    """
    Generate documentation for a GitHub repository asynchronously.
    
    This endpoint queues the documentation generation task and returns immediately.
    Use the returned job_id to poll for results.
    
    Args:
        request: Request containing the repository URL
        background_tasks: FastAPI background tasks
        
    Returns:
        Response with job_id
    """
    # Validate API key
    if not check_api_key():
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
        )
    
    # Validate repo URL
    if not request.repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")
    
    # Create a simple job ID (in production, use proper job tracking)
    import uuid
    job_id = str(uuid.uuid4())
    
    logger.info("Queuing documentation generation job %s for: %s", job_id, request.repo_url)
    
    # Add background task
    background_tasks.add_task(
        _run_doc_generation,
        job_id,
        request.repo_url,
    )
    
    return GenerateDocsResponse(
        status="queued",
        message="Documentation generation started",
        job_id=job_id,
    )


async def _run_doc_generation(job_id: str, repo_url: str) -> None:
    """
    Background task to run documentation generation.
    
    Args:
        job_id: Unique job identifier
        repo_url: URL of the repository
    """
    try:
        logger.info("Running documentation generation for job %s", job_id)
        result = generate_repo_documentation(repo_url)
        
        if "error" in result:
            logger.error("Job %s failed: %s", job_id, result.get("error"))
        else:
            logger.info(
                "Job %s completed: %d files processed",
                job_id,
                result.get("files_processed", 0)
            )
            
    except Exception as e:
        logger.error("Job %s failed with exception: %s", job_id, e, exc_info=True)


@router.get("/health")
async def docs_health_check() -> dict:
    """
    Health check endpoint for the documentation service.
    
    Returns:
        Status of the documentation service
    """
    api_key_configured = check_api_key()
    
    return {
        "status": "healthy" if api_key_configured else "degraded",
        "api_key_configured": api_key_configured,
        "service": "documentation",
    }

