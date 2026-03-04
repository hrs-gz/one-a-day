"""OpenRouter (OpenAI-compatible) LLM client with retry + backoff."""

from __future__ import annotations

import time

import structlog
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from app.exceptions import LLMProviderError
from app.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)


class OpenRouterClient(BaseLLMClient):
    """LLM client that talks to OpenRouter via the OpenAI SDK."""

    provider_name = "openrouter"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_attempts: int = 3,
        backoff_seconds: list[float] | None = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._max_attempts = max_attempts
        self._backoff = backoff_seconds or [1, 3, 8]

    def chat(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        oai_messages = [{"role": m.role, "content": m.content} for m in messages]

        last_exc: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=oai_messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                    }
                return LLMResponse(
                    content=content,
                    model=response.model or model,
                    usage=usage,
                )
            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                wait = (
                    self._backoff[attempt]
                    if attempt < len(self._backoff)
                    else self._backoff[-1]
                )
                logger.warning(
                    "openrouter_retry",
                    attempt=attempt + 1,
                    wait=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            except Exception as exc:
                raise LLMProviderError(f"OpenRouter error: {exc}") from exc

        raise LLMProviderError(
            f"OpenRouter failed after {self._max_attempts} attempts: {last_exc}"
        )
