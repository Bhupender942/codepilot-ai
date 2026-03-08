"""
Documentation Service for CodePilot.

This module provides functionality to generate documentation for code files
by reading repository files, filtering important files, chunking code, and
sending each chunk to the Groq LLM.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import git
from git.exc import GitCommandError

from app.services.llm_service import (
    check_api_key,
    generate_documentation_response,
    generate_response,
)

logger = logging.getLogger(__name__)

# Directories to ignore when analyzing repositories
IGNORED_DIRS = [
    "node_modules",
    ".git",
    "build",
    "dist",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "vendor",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".cache",
]

# File extensions to include in documentation
IMPORTANT_EXTENSIONS = {
    ".py",  # Python
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".jsx",  # React JSX
    ".tsx",  # React TypeScript
    ".java",  # Java
    ".go",  # Go
    ".rs",  # Rust
    ".cpp",  # C++
    ".c",  # C
    ".cs",  # C#
    ".rb",  # Ruby
    ".php",  # PHP
    ".swift",  # Swift
    ".kt",  # Kotlin
    ".scala",  # Scala
    ".sh",  # Shell
    ".bash",  # Bash
}

# Chunk size for large files (in lines)
CHUNK_SIZE = 150

# Threshold for chunking (files larger than this will be split)
LARGE_FILE_THRESHOLD = 200


def split_code_into_chunks(code: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    Split code into chunks of specified size.
    
    Args:
        code: The source code to split
        chunk_size: Maximum number of lines per chunk
        
    Returns:
        List of code chunks
    """
    lines = code.split("\n")
    chunks = []
    
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks


def should_ignore_path(path: Path) -> bool:
    """
    Check if a path should be ignored based on IGNORED_DIRS.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path should be ignored, False otherwise
    """
    path_str = str(path)
    
    # Check if any part of the path matches an ignored directory
    parts = path.parts
    for ignored in IGNORED_DIRS:
        if ignored in parts:
            return True
    
    return False


def is_important_file(path: Path) -> bool:
    """
    Check if a file is important based on its extension.
    
    Args:
        path: File path to check
        
    Returns:
        True if the file should be analyzed, False otherwise
    """
    return path.suffix in IMPORTANT_EXTENSIONS


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
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        destination = os.path.join(temp_dir, "repo")
    
    try:
        git.Repo.clone_from(repo_url, destination)
        logger.info("Successfully cloned repository to %s", destination)
        return destination
    except GitCommandError as e:
        logger.error("Failed to clone repository: %s", e)
        raise


def read_repository_files(repo_path: str) -> dict[str, str]:
    """
    Read all important files from a repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Dictionary mapping file paths to their content
    """
    files_content = {}
    repo_dir = Path(repo_path)
    
    for file_path in repo_dir.rglob("*"):
        # Skip ignored paths
        if should_ignore_path(file_path):
            continue
        
        # Skip non-files
        if not file_path.is_file():
            continue
        
        # Skip non-important files
        if not is_important_file(file_path):
            continue
        
        try:
            # Get relative path
            relative_path = file_path.relative_to(repo_dir)
            
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            files_content[str(relative_path)] = content
            
        except Exception as e:
            logger.warning("Failed to read file %s: %s", file_path, e)
            continue
    
    return files_content


def generate_file_documentation(
    file_path: str, code: str, language: str = "unknown"
) -> dict:
    """
    Generate documentation for a single file.
    
    Args:
        file_path: Path to the file
        code: Source code
        language: Programming language
        
    Returns:
        Dictionary with documentation
    """
    lines = code.split("\n")
    
    # Check if file needs to be chunked
    if len(lines) > LARGE_FILE_THRESHOLD:
        # Split into chunks
        chunks = split_code_into_chunks(code, CHUNK_SIZE)
        
        documentations = []
        for i, chunk in enumerate(chunks):
            logger.info(
                "Processing chunk %d of %d for file %s", 
                i + 1, len(chunks), file_path
            )
            
            chunk_doc = generate_documentation_response(chunk, language)
            documentations.append(
                {
                    "chunk_index": i,
                    "start_line": i * CHUNK_SIZE + 1,
                    "end_line": min((i + 1) * CHUNK_SIZE, len(lines)),
                    "documentation": chunk_doc,
                }
            )
        
        return {
            "file_path": file_path,
            "language": language,
            "total_lines": len(lines),
            "chunks": len(chunks),
            "documentations": documentations,
        }
    else:
        # Process as single chunk
        doc = generate_documentation_response(code, language)
        
        return {
            "file_path": file_path,
            "language": language,
            "total_lines": len(lines),
            "chunks": 1,
            "documentation": doc,
        }


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
        return {
            "error": "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable.",
            "repo_url": repo_url,
        }
    
    # Clone repository
    try:
        repo_path = clone_repository(repo_url)
    except GitCommandError as e:
        return {
            "error": f"Failed to clone repository: {str(e)}",
            "repo_url": repo_url,
        }
    
    # Read all files
    files_content = read_repository_files(repo_path)
    
    if not files_content:
        return {
            "error": "No important files found in repository",
            "repo_url": repo_url,
            "files_processed": 0,
        }
    
    # Generate documentation for each file
    results = []
    for file_path, content in files_content.items():
        # Determine language from extension
        ext = Path(file_path).suffix
        language = ext.lstrip(".")
        
        logger.info("Generating documentation for %s", file_path)
        
        doc = generate_file_documentation(file_path, content, language)
        results.append(doc)
    
    # Clean up temporary directory
    try:
        import shutil
        shutil.rmtree(Path(repo_path).parent)
    except Exception as e:
        logger.warning("Failed to clean up temporary directory: %s", e)
    
    return {
        "repo_url": repo_url,
        "files_processed": len(files_content),
        "files": results,
    }


def get_supported_languages() -> list[str]:
    """
    Get list of supported programming languages.
    
    Returns:
        List of supported language extensions
    """
    return sorted(list(IMPORTANT_EXTENSIONS))

