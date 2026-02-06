"""
LLM client using Google Gemini with retry logic
"""
import logging
from typing import Optional
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os

logger = logging.getLogger(__name__)

# Configure Gemini
_gemini_configured = False


def configure_gemini(api_key: str = None):
    """Configure Gemini API"""
    global _gemini_configured
    
    if not _gemini_configured:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if key:
            genai.configure(api_key=key)
            _gemini_configured = True
            logger.info("Gemini API configured")
        else:
            logger.warning("No Gemini API key provided")


class GeminiRateLimitError(Exception):
    """Custom exception for rate limit errors"""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((GeminiRateLimitError, ConnectionError)),
    reraise=True
)
async def call_llm(
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.7,
    model_name: str = "gemini-1.5-flash"
) -> str:
    """
    Call Gemini LLM with exponential backoff retry
    
    Args:
        prompt: The prompt to send
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0-1)
        model_name: Gemini model to use
    
    Returns:
        Generated text response
    """
    try:
        configure_gemini()
        
        model = genai.GenerativeModel(model_name)
        
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response.text:
            return response.text
        else:
            logger.warning("Empty response from Gemini")
            return ""
            
    except Exception as e:
        error_str = str(e).lower()
        
        if "rate" in error_str or "quota" in error_str:
            logger.warning(f"Rate limit hit, will retry: {e}")
            raise GeminiRateLimitError(str(e))
        
        logger.error(f"LLM call failed: {e}")
        raise


def call_llm_sync(
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.7,
    model_name: str = "gemini-1.5-flash"
) -> str:
    """
    Synchronous version of call_llm
    """
    try:
        configure_gemini()
        
        model = genai.GenerativeModel(model_name)
        
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response.text:
            return response.text
        else:
            return ""
            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""
