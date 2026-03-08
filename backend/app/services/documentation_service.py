"""
Documentation Service for CodePilot.

This module provides functionality to generate documentation for code files
by reading repository files, filtering important files, chunking code, and
sending each chunk to the Groq LLM.

Features:
- File filtering (ignore directories and file types)
- File chunking (split large files into smaller chunks)
- Request throttling (delay between API calls to prevent rate limits)
- Exponential backoff for retries
"""

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import git
from git.exc import GitCommandError

from app.services.llm_service import check_api_key

logger = logging.getLogger(__name__)

# =============================================================================
# FILE FILTERING CONSTANTS
# =============================================================================

# Directories to ignore when analyzing repositories
IGNORED_DIRS = [
    "node_modules",
    ".git",
    "dist",
    "build",
    "venv",
    "__pycache__",
    "coverage",
    ".next",
    ".nuxt",
    ".cache",
    ".venv",
    "env",
    "vendor",
    "target",
]

# File extensions to ignore completely
IGNORED_EXTENSIONS = [
    ".json",
    ".lock",
    ".txt",
    ".md",
    ".log",
    ".env",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
]

# Only analyze these file extensions
ALLOWED_EXTENSIONS = [
    ".py",   # Python
    ".js",   # JavaScript
    ".jsx",  # React JSX
    ".ts",   # TypeScript
    ".tsx",  # React TypeScript
    ".go",   # Go
    ".java", # Java
    ".cpp",  # C++
    ".c",    # C
    ".rs",   # Rust
]

# =============================================================================
# CHUNKING CONSTANTS
# =============================================================================

# Threshold for chunking (files larger than this will be split)
LARGE_FILE_THRESHOLD = 200

# Chunk size for splitting large files (in lines)
DEFAULT_CHUNK_SIZE = 150

# =============================================================================
# REQUEST THROTTLING CONSTANTS
# =============================================================================

# Delay between API calls to prevent rate limits (in seconds)
REQUEST_DELAY = 1.2

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
RETRY_DELAY_MULTIPLIER = 2.0  # exponential backoff

# =============================================================================
# PERFORMANCE CONSTANTS
# =============================================================================

# Maximum number of files to analyze per repository
MAX_FILES = 80

# Priority order for file analysis (more important files first)
PRIORITY_EXTENSIONS = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java"]


def should_analyze_file(file_path: str) -> bool:
    """
    Check if a file should be analyzed based on filtering rules.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file should be analyzed, False otherwise
    """
    path = Path(file_path)
    
    # Check if any part of the path is in IGNORED_DIRS
    parts = path.parts
    for ignored_dir in IGNORED_DIRS:
        if ignored_dir in parts:
            logger.debug(f"Skipping file in ignored directory: {file_path}")
            return False
    
    # Check file extension
    extension = path.suffix.lower()
    
    # Skip if extension is in IGNORED_EXTENSIONS
    if extension in IGNORED_EXTENSIONS:
        logger.debug(f"Skipping file with ignored extension: {file_path}")
        return False
    
    # Skip if extension is not in ALLOWED_EXTENSIONS
    if extension not in ALLOWED_EXTENSIONS:
        logger.debug(f"Skipping file with non-allowed extension: {file_path}")
        return False
    
    return True


def split_code_into_chunks(code: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    """
    Split code into chunks of specified size.
    
    Args:
        code: The source code to split
        chunk_size: Maximum number of lines per chunk (default: 150)
        
    Returns:
        List of code chunks
    """
    lines = code.split("\n")
    chunks = []
    
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)
    
    logger.debug(f"Split code of {len(lines)} lines into {len(chunks)} chunks")
    return chunks


def get_file_priority(file_path: str) -> int:
    """
    Get priority score for a file (lower number = higher priority).
    
    Args:
        file_path: Path to the file
        
    Returns:
        Priority score (0 = highest priority)
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    for idx, ext in enumerate(PRIORITY_EXTENSIONS):
        if extension == ext:
            return idx
    
    return len(PRIORITY_EXTENSIONS)


def sort_files_by_priority(files: list[str]) -> list[str]:
    """
    Sort files by analysis priority.
    
    Args:
        files: List of file paths
        
    Returns:
        Sorted list of file paths
    """
    return sorted(files, key=get_file_priority)


def clone_repository(repo_url: str, destination: Optional[str] = None) -> str:
    """
    Clone a GitHub repository to a local directory.
    
    Args:
        repo_url: URL of the GitHub repository
        destination: Optional destination directory
        
    Returns:
        Path to the cloned repository
        
    Raises:
        GitCommandError: If cloning fails
    """
    if destination is None:
        temp_dir = tempfile.mkdtemp()
        destination = os.path.join(temp_dir, "repo")
    
    try:
        git.Repo.clone_from(repo_url, destination)
        logger.info("Successfully cloned repository to %s", destination)
        return destination
    except GitCommandError as e:
        logger.error("Failed to clone repository: %s", e)
        raise


def scan_repository_files(repo_path: str) -> list[str]:
    """
    Scan repository and return list of files to analyze.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        List of file paths to analyze
    """
    files_to_analyze = []
    repo_dir = Path(repo_path)
    
    for file_path in repo_dir.rglob("*"):
        # Skip non-files
        if not file_path.is_file():
            continue
        
        # Get relative path
        try:
            relative_path = file_path.relative_to(repo_dir)
        except ValueError:
            continue
        
        # Check if file should be analyzed
        if should_analyze_file(str(relative_path)):
            files_to_analyze.append(str(relative_path))
    
    # Sort by priority
    files_to_analyze = sort_files_by_priority(files_to_analyze)
    
    # Limit to MAX_FILES
    if len(files_to_analyze) > MAX_FILES:
        logger.warning(
            f"Repository has {len(files_to_analyze)} files, limiting to {MAX_FILES}"
        )
        files_to_analyze = files_to_analyze[:MAX_FILES]
    
    logger.info(f"Found {len(files_to_analyze)} files to analyze")
    return files_to_analyze


def read_file_content(repo_path: str, file_path: str) -> Optional[str]:
    """
    Read content of a file.
    
    Args:
        repo_path: Path to the repository
        file_path: Relative path to the file
        
    Returns:
        File content or None if reading fails
    """
    full_path = Path(repo_path) / file_path
    
    try:
        content = full_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        return None


def generate_chunk_documentation(
    code: str,
    language: str,
    file_path: str,
    chunk_index: int,
) -> dict:
    """
    Generate documentation for a single code chunk.
    
    Args:
        code: Code chunk to document
        language: Programming language
        file_path: Path to the source file
        chunk_index: Index of the chunk
        
    Returns:
        Dictionary with documentation
    """
    # Import here to avoid circular imports
    from app.services.llm_service import generate_ai_response
    
    system_prompt = """You are a senior software engineer and teacher.

Explain the following code in simple English so that a beginner developer can understand it.

Return the explanation using this format:

Function Name
Description
Inputs
Outputs
Steps
Time Complexity
Space Complexity"""

    user_prompt = f"""Please explain this {language} code:

```{language}
{code}
```

Provide a clear and simple explanation."""

    # Retry logic with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            explanation = generate_ai_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            
            # Check for error response
            if "unavailable" in explanation.lower():
                raise Exception("AI service unavailable")
            
            # Add delay between requests to prevent rate limits
            time.sleep(REQUEST_DELAY)
            
            return {
                "file": file_path,
                "chunk": chunk_index + 1,
                "language": language,
                "explanation": explanation,
            }
            
        except Exception as e:
            logger.warning(f"Error generating documentation (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                wait_time = INITIAL_RETRY_DELAY * (RETRY_DELAY_MULTIPLIER ** attempt)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to generate documentation after {MAX_RETRIES} attempts")
                return {
                    "file": file_path,
                    "chunk": chunk_index + 1,
                    "language": language,
                    "explanation": "Failed to generate documentation. Please try again.",
                }


def generate_file_documentation(
    repo_path: str,
    file_path: str,
) -> dict:
    """
    Generate documentation for a single file.
    
    Args:
        repo_path: Path to the repository
        file_path: Relative path to the file
        
    Returns:
        Dictionary with documentation
    """
    # Read file content
    content = read_file_content(repo_path, file_path)
    
    if content is None:
        return {
            "file": file_path,
            "error": "Failed to read file",
            "chunks": [],
        }
    
    # Determine language from extension
    extension = Path(file_path).suffix.lower()
    language = extension.lstrip(".")
    
    lines = content.split("\n")
    results = {
        "file": file_path,
        "language": language,
        "total_lines": len(lines),
        "chunks": [],
    }
    
    # Check if file needs to be chunked
    if len(lines) > LARGE_FILE_THRESHOLD:
        # Split into chunks
        chunks = split_code_into_chunks(content, DEFAULT_CHUNK_SIZE)
        results["total_chunks"] = len(chunks)
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {idx + 1}/{len(chunks)} for {file_path}")
            chunk_doc = generate_chunk_documentation(chunk, language, file_path, idx)
            results["chunks"].append(chunk_doc)
    else:
        # Process as single chunk
        results["total_chunks"] = 1
        chunk_doc = generate_chunk_documentation(content, language, file_path, 0)
        results["chunks"].append(chunk_doc)
    
    return results


def generate_repo_documentation(repo_url: str) -> dict:
    """
    Generate documentation for an entire repository.
    
    Args:
        repo_url: URL of the GitHub repository
        
    Returns:
        Dictionary with documentation for all files
    """
    # Check API key
    if not check_api_key():
        logger.error("GROQ_API_KEY is not configured")
        return {
            "error": "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable.",
            "repo_url": repo_url,
        }
    
    # Clone repository
    try:
        repo_path = clone_repository(repo_url)
    except GitCommandError as e:
        logger.error(f"Failed to clone repository: {e}")
        return {
            "error": f"Failed to clone repository: {str(e)}",
            "repo_url": repo_url,
        }
    
    try:
        # Scan files to analyze
        files_to_analyze = scan_repository_files(repo_path)
        
        if not files_to_analyze:
            return {
                "error": "No analyzable files found in repository",
                "repo_url": repo_url,
                "files_processed": 0,
            }
        
        # Generate documentation for each file
        results = []
        for idx, file_path in enumerate(files_to_analyze):
            logger.info(f"Processing file {idx + 1}/{len(files_to_analyze)}: {file_path}")
            
            file_doc = generate_file_documentation(repo_path, file_path)
            results.append(file_doc)
        
        return {
            "repo_url": repo_url,
            "files_processed": len(files_to_analyze),
            "files": results,
        }
        
    finally:
        # Clean up temporary directory
        try:
            import shutil
            parent_dir = Path(repo_path).parent
            if parent_dir.exists():
                shutil.rmtree(parent_dir)
                logger.debug(f"Cleaned up temporary directory: {parent_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {e}")


def get_supported_languages() -> list[str]:
    """
    Get list of supported programming languages.
    
    Returns:
        List of supported language extensions
    """
    return sorted(ALLOWED_EXTENSIONS)

