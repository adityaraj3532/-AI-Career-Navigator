import abc
import asyncio
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel

from app.core.config import get_settings


class BaseLLMProvider(abc.ABC):
    """Abstract base class for all LLM providers."""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        timeout: float = 15.0,
    ) -> str:
        """Generate response text from prompt with an enforced per-call timeout."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider utilizing the official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not configured.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        timeout: float = 15.0,
    ) -> str:
        client = self._get_client()
        from google.genai import types

        config_kwargs: Dict[str, Any] = {}
        if schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        async def _call() -> str:
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""

        return await asyncio.wait_for(_call(), timeout=timeout)


class MockLLMProvider(BaseLLMProvider):
    """In-memory mock provider for deterministic tests and CI environments."""

    def __init__(
        self,
        responses: Optional[List[Union[str, Exception]]] = None,
        delay: float = 0.0,
    ) -> None:
        self.responses: List[Union[str, Exception]] = responses or []
        self.delay: float = delay
        self.call_history: List[Dict[str, Any]] = []

    def queue_response(self, response: Union[str, Exception]) -> None:
        self.responses.append(response)

    async def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        timeout: float = 15.0,
    ) -> str:
        self.call_history.append({
            "prompt": prompt,
            "schema": schema,
            "timeout": timeout,
        })

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if not self.responses:
            return "{}"

        next_resp = self.responses.pop(0)
        if isinstance(next_resp, Exception):
            raise next_resp
        return next_resp
