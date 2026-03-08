"""
Groq LLM Service for CodePilot.

This module provides a reusable LLM service using the Groq API.
It loads the API key from the GROQ_API_KEY environment variable.
"""

import logging
import os
import time
from typing import Optional

from groq import Groq

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Get or create the Groq client singleton."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# Default model
DEFAULT_MODEL = "llama-3.1-70b-versatile"

# Retry configuration
MAX_RETRIES = 3
INITIAL_DELAY = 1.0  # seconds
DELAY_MULTIPLIER = 2.0  # exponential backoff

# Delay between API calls to prevent rate limits (in seconds)
API_CALL_DELAY = 1.0


def generate_ai_response(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Generate an AI response using the Groq API.
    
    This is the main function for generating responses with Groq.
    It includes retry logic for rate limits and connection errors.
    
    Args:
        prompt: The user prompt/question
        system_prompt: Optional system prompt to set context
        model: The Groq model to use (default: llama-3.1-70b-versatile)
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens in the response
        
    Returns:
        The generated response text, or error message if failed
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not configured")
        return "AI temporarily unavailable. Please try again."
    
    for attempt in range(MAX_RETRIES):
        try:
            client = get_groq_client()
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Make API call
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Add delay between successful calls to prevent rate limits
            time.sleep(API_CALL_DELAY)
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "rate limit" in error_str or "429" in error_str
            is_connection_error = "connection" in error_str or "timeout" in error_str
            
            if is_rate_limit or is_connection_error:
                logger.warning(f"Retryable error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = INITIAL_DELAY * (DELAY_MULTIPLIER ** attempt)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries ({MAX_RETRIES}) reached")
                    return "AI temporarily unavailable. Please try again."
            else:
                logger.error(f"Unexpected error during Groq API call: {e}")
                return "AI temporarily unavailable. Please try again."
    
    return "AI temporarily unavailable. Please try again."


def generate_response(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Generate a response using the Groq API.
    
    This is an alias for generate_ai_response for backward compatibility.
    
    Args:
        prompt: The user prompt/question
        system_prompt: Optional system prompt to set context
        model: The Groq model to use (default: llama-3.1-70b-versatile)
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens in the response
        
    Returns:
        The generated response text
    """
    return generate_ai_response(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def generate_documentation_response(code: str, language: str = "unknown") -> str:
    """
    Generate documentation for the given code using Groq.
    
    Args:
        code: The code to document
        language: The programming language of the code
        
    Returns:
        Generated documentation
    """
    system_prompt = """You are a senior software engineer and teacher.

Explain the following code in simple English for a beginner developer.

Return the result in this format:

Function Name:
Description:
Inputs:
Outputs:
Steps:
Time Complexity:
Space Complexity:"""

    user_prompt = f"""Please explain the following {language} code:

```{language}
{code}
```

Provide a clear and simple explanation."""

    return generate_ai_response(user_prompt, system_prompt=system_prompt)


def generate_code_explanation(code: str) -> str:
    """
    Generate a simple explanation of the given code.
    
    Args:
        code: The code to explain
        
    Returns:
        Simple explanation of the code
    """
    system_prompt = """You are a helpful code assistant. 
Explain the following code in simple, clear language that a beginner can understand.
Focus on what the code does, not how it does it."""

    user_prompt = f"""Explain this code simply:

{code}"""

    return generate_ai_response(user_prompt, system_prompt=system_prompt)


def check_api_key() -> bool:
    """
    Check if the Groq API key is configured.
    
    Returns:
        True if API key is set, False otherwise
    """
    return bool(GROQ_API_KEY)

