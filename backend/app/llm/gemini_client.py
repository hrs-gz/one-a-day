"""Google Gemini LLM client with retry + backoff."""

from __future__ import annotations

import time

import structlog
from google import genai
from google.genai import errors as genai_errors

from app.exceptions import LLMProviderError
from app.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)


class GeminiClient(BaseLLMClient):
    """LLM client that talks to the Gemini API via google-genai SDK."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        max_attempts: int = 3,
        backoff_seconds: list[float] | None = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
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
        # Build Gemini contents from messages.
        # Gemini uses "user" and "model" roles; system prompt goes into
        # the config rather than as a message.
        system_instruction = None
        contents: list[genai.types.Content] = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(
                    genai.types.Content(
                        role=role,
                        parts=[genai.types.Part(text=msg.content)],
                    )
                )

        config = genai.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        last_exc: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                content = response.text or ""
                return LLMResponse(content=content, model=model)
            except (
                genai_errors.ClientError,
                genai_errors.ServerError,
            ) as exc:
                last_exc = exc
                wait = (
                    self._backoff[attempt]
                    if attempt < len(self._backoff)
                    else self._backoff[-1]
                )
                logger.warning(
                    "gemini_retry",
                    attempt=attempt + 1,
                    wait=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            except Exception as exc:
                raise LLMProviderError(f"Gemini error: {exc}") from exc

        raise LLMProviderError(
            f"Gemini failed after {self._max_attempts} attempts: {last_exc}"
        )
