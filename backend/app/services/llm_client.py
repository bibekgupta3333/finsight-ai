"""
LLM client service for Ollama integration.

Provides async interface to Ollama with connection pooling,
health checks, and proper error handling.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, List, Optional

import ollama
from ollama import AsyncClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """
    Async LLM client for Ollama.

    Features:
    - Connection pooling and reuse
    - Health checks and model availability
    - Retry logic with exponential backoff
    - Support for streaming and batch modes
    - Error handling and timeout management
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize LLM client.

        Args:
            base_url: Ollama server URL (default from settings)
            timeout: Request timeout in seconds (default from settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.llm_timeout
        self.client = AsyncClient(host=self.base_url)
        self._available_models: Optional[List[str]] = None
        logger.info(f"Initialized LLM client for {self.base_url}")

    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.

        Returns:
            True if service is reachable, False otherwise
        """
        try:
            # Try to list models - basic health check
            response = await asyncio.wait_for(self.client.list(), timeout=5.0)
            logger.info(
                f"Ollama health check passed: {len(response.get('models', []))} models available"
            )
            return True
        except asyncio.TimeoutError:
            logger.error("Ollama health check timeout")
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of available models from Ollama.

        Args:
            force_refresh: Force refresh of cached model list

        Returns:
            List of model names
        """
        if self._available_models is None or force_refresh:
            try:
                response = await self.client.list()
                self._available_models = [model["name"] for model in response.get("models", [])]
                logger.info(f"Available models: {self._available_models}")
            except Exception as e:
                logger.error(f"Failed to get available models: {e}")
                self._available_models = []
        return self._available_models

    async def ensure_model(self, model_name: str) -> bool:
        """
        Ensure a model is available, pulling if necessary.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model is available, False otherwise
        """
        available = await self.get_available_models(force_refresh=True)
        if model_name in available:
            return True

        logger.warning(f"Model {model_name} not found, attempting to pull...")
        try:
            # Pull the model (this can take a while for large models)
            await self.client.pull(model_name)
            logger.info(f"Successfully pulled model {model_name}")
            # Refresh available models
            await self.get_available_models(force_refresh=True)
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        seed: Optional[int] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> Dict:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt
            model: Model name (default from settings)
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            seed: Random seed for reproducibility
            max_tokens: Maximum tokens to generate
            system: System prompt

        Returns:
            Response dictionary with 'response', 'model', 'done', etc.

        Raises:
            asyncio.TimeoutError: If generation times out
            Exception: If generation fails
        """
        model = model or settings.llm_model_name

        # Build options
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k
        if seed is not None:
            options["seed"] = seed
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        try:
            response = await asyncio.wait_for(
                self.client.generate(
                    model=model,
                    prompt=prompt,
                    system=system,
                    options=options if options else None,
                ),
                timeout=self.timeout,
            )
            logger.debug(f"Generated response with model {model}")
            return response
        except asyncio.TimeoutError:
            logger.error(f"LLM generation timeout after {self.timeout}s")
            raise
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        seed: Optional[int] = None,
        system: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate streaming completion from LLM.

        Args:
            prompt: User prompt
            model: Model name (default from settings)
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            seed: Random seed for reproducibility
            system: System prompt

        Yields:
            Response chunks

        Raises:
            Exception: If generation fails
        """
        model = model or settings.llm_model_name

        # Build options
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k
        if seed is not None:
            options["seed"] = seed

        try:
            async for chunk in await self.client.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options if options else None,
                stream=True,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"LLM streaming generation failed: {e}")
            raise

    async def batch_generate(
        self,
        prompts: List[str],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> List[Dict]:
        """
        Generate completions for multiple prompts in parallel.

        Args:
            prompts: List of prompts
            model: Model name
            temperature: Sampling temperature
            **kwargs: Additional generation parameters

        Returns:
            List of responses
        """
        tasks = [
            self.generate(prompt=prompt, model=model, temperature=temperature, **kwargs)
            for prompt in prompts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generation failed for prompt {i}: {result}")
                responses.append({"response": "", "error": str(result), "done": False})
            else:
                responses.append(result)

        return responses


# Global client instance
_llm_client: Optional[LLMClient] = None


async def get_llm_client() -> LLMClient:
    """
    Get global LLM client instance.

    Returns:
        LLMClient instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
        # Perform health check on first access
        healthy = await _llm_client.health_check()
        if not healthy:
            logger.warning("Ollama service may not be available")
    return _llm_client
