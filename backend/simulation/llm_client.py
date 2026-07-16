"""
LLM client using Ollama Cloud chat API with a Ray actor pool.

Architecture:
- Each Ray actor makes HTTP requests to the Ollama endpoint
- Actor pool distributes requests with round-robin
- Robust retry with exponential backoff
"""
import os
import random
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional
from multiprocessing import cpu_count

import ray
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
env_paths = [
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
    Path.cwd() / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

logger = logging.getLogger(__name__)

# Default Ollama Cloud API configuration
DEFAULT_OLLAMA_API_URL = "https://ollama.com/api/chat"
DEFAULT_OLLAMA_MODEL = "gemma4:31b-cloud"


def _clean_env(name: str, default: str = "") -> str:
    """Read env var and trim surrounding whitespace/newlines."""
    return (os.getenv(name, default) or default).strip()


@ray.remote
class OllamaActor:
    """
    Ray actor that sends requests to Ollama's chat API.

    QwenActor is kept as a backward-compatible alias below.
    """

    def __init__(self):
        """Initialize with API config from environment."""
        self._api_url = _clean_env(
            "OLLAMA_API_URL",
            DEFAULT_OLLAMA_API_URL,
        )
        self._model_name = _clean_env(
            "OLLAMA_MODEL_NAME",
            DEFAULT_OLLAMA_MODEL,
        )
        self._api_key = (
            _clean_env("OLLAMA_API_KEY", "")
            or _clean_env("OLLAMA_KEY", "")
        )
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if self._api_key:
            self._session.headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            print("[OllamaActor] Warning: OLLAMA_API_KEY is not set")

        print(
            f"[OllamaActor] Initialized - endpoint: {self._api_url}, "
            f"model: {self._model_name}"
        )

    def call(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        model_name: str = None,
        retries: int = 5,
    ) -> str:
        """
        Send a request to Ollama with retry and exponential backoff.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model_name: Override model name (uses env default if None)
            retries: Number of retries on failure

        Returns:
            Generated text response
        """
        model = model_name or self._model_name
        last_error = None

        for attempt in range(retries):
            try:
                print(f"[OllamaActor] Attempt {attempt + 1}/{retries} calling {model}...")

                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                }

                response = self._session.post(
                    self._api_url,
                    json=payload,
                    timeout=180,
                )

                if response.status_code != 200:
                    raise Exception(
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )

                data = response.json()
                content = self._extract_chat_content(data)

                if content:
                    print(
                        f"[OllamaActor] Success! Response: {len(content)} chars"
                    )
                    return content

                print("[OllamaActor] Empty response from model")
                return ""

            except Exception as e:
                last_error = e
                wait_time = min(60, (2 ** attempt) + random.random() * 2)
                print(
                    f"[OllamaActor] Error (attempt {attempt + 1}/{retries}), "
                    f"waiting {wait_time:.1f}s: {e}"
                )
                if attempt < retries - 1:
                    time.sleep(wait_time)
                else:
                    raise e

        # All retries exhausted
        if last_error:
            raise last_error
        return ""

    @staticmethod
    def _extract_chat_content(data: dict) -> str:
        """Extract assistant content from an Ollama chat response."""
        # Native Ollama: {"message": {"role": "assistant", "content": "..."}}
        message = data.get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()

        # OpenAI-compatible fallback: {"choices": [{"message": {"content": "..."}}]}
        choices = data.get("choices") or []
        if choices:
            choice_message = choices[0].get("message") or {}
            choice_content = choice_message.get("content", "")
            if isinstance(choice_content, str):
                return choice_content.strip()
            if isinstance(choice_content, list):
                parts = []
                for item in choice_content:
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("content")
                        if text:
                            parts.append(str(text))
                    elif item:
                        parts.append(str(item))
                return "".join(parts).strip()

        # /api/generate style fallback
        response_text = data.get("response", "")
        if isinstance(response_text, str) and response_text.strip():
            return response_text.strip()

        return str(content).strip() if content else ""


class OllamaLLM:
    """
    Manages a pool of Ollama Ray actors for parallel LLM requests.

    Usage:
        llm = OllamaLLM(num_actors=2)
        result = await llm.atext_request("Hello world")
        # or synchronously:
        result = llm.text_request("Hello world")
    """

    def __init__(self, num_actors: int = None):
        """
        Initialize the actor pool.

        Args:
            num_actors: Number of Ray actors to spawn.
                        Defaults to min(cpu_count(), 4).
        """
        if num_actors is None:
            num_actors = min(cpu_count(), 4)

        self._actors = [OllamaActor.remote() for _ in range(num_actors)]
        self._next_index = 0
        logger.info(f"OllamaLLM initialized with {num_actors} actors")

    def _get_next_actor(self):
        """Round-robin actor selection"""
        actor = self._actors[self._next_index % len(self._actors)]
        self._next_index += 1
        return actor

    async def atext_request(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        model_name: str = None,
        retries: int = 5,
    ) -> str:
        """
        Async request to the LLM actor pool.

        Selects an actor via round-robin and sends the request.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model_name: Model override (uses env default if None)
            retries: Number of retries

        Returns:
            Generated text response
        """
        actor = self._get_next_actor()

        actor_idx = self._actors.index(actor) if actor in self._actors else '?'
        logger.info(f"LLM request dispatched to actor {actor_idx}")

        try:
            import time as _time
            _t0 = _time.time()
            result = await actor.call.remote(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model_name=model_name,
                retries=retries,
            )
            _elapsed = _time.time() - _t0
            logger.info(f"LLM actor {actor_idx} responded in {_elapsed:.1f}s")
            return result
        except Exception as e:
            logger.error(f"LLM request failed on actor {actor_idx}: {e}")
            return ""

    def text_request(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7,
        model_name: str = None,
        retries: int = 5,
    ) -> str:
        """
        Synchronous wrapper for atext_request.
        Uses ray.get() to block until the result is ready.
        """
        actor = self._get_next_actor()
        try:
            result = ray.get(
                actor.call.remote(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model_name=model_name,
                    retries=retries,
                )
            )
            return result
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return ""

    def shutdown(self):
        """Kill all actor handles"""
        for actor in self._actors:
            try:
                ray.kill(actor)
            except Exception:
                pass
        self._actors = []


# ---------------------------------------------------------------------------
# Backward-compatible convenience functions
# ---------------------------------------------------------------------------
QwenActor = OllamaActor
QwenLLM = OllamaLLM


_llm_pool: Optional[OllamaLLM] = None


def get_llm_pool(num_actors: int = None) -> OllamaLLM:
    """Get or create the global LLM actor pool"""
    global _llm_pool
    if _llm_pool is None:
        _llm_pool = OllamaLLM(num_actors=num_actors)
    return _llm_pool


def shutdown_llm_pool():
    """Shutdown the global LLM pool"""
    global _llm_pool
    if _llm_pool is not None:
        _llm_pool.shutdown()
        _llm_pool = None


def call_llm_sync(
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.7,
    model_name: str = None,
) -> str:
    """
    Legacy synchronous LLM call — delegates to the actor pool.
    """
    pool = get_llm_pool()
    return pool.text_request(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        model_name=model_name,
    )
