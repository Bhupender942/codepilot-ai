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

# Delay between API calls to prevent rate limits (in seconds)
API_CALL_DELAY = 1.0


def generate_response(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Generate a response using the Groq API.
    
    Args:
        prompt: The user prompt/question
        system_prompt: Optional system prompt to set context
        model: The Groq model to use (default: llama-3.1-70b-versatile)
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens in the response
        
    Returns:
        The generated response text
        
    Raises:
        ValueError: If GROQ_API_KEY is not configured
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not configured")
        return "Error: GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
    
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
        
        # Add delay to prevent rate limits
        time.sleep(API_CALL_DELAY)
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error("Groq API call failed: %s", e)
        time.sleep(2)
        return f"AI temporarily unavailable. Please try again. Error: {str(e)}"


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

Explain the following code in simple English so that a beginner developer can understand it.

Return format:

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
    
    return generate_response(user_prompt, system_prompt=system_prompt)


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

    return generate_response(user_prompt, system_prompt=system_prompt)


def check_api_key() -> bool:
    """
    Check if the Groq API key is configured.
    
    Returns:
        True if API key is set, False otherwise
    """
    return bool(GROQ_API_KEY)

