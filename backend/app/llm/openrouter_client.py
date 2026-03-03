"""OpenRouter LLM client (OpenAI-compatible API)."""

from __future__ import annotations

import time

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_BASE_URL = "https://openrouter.ai/api/v1"
_RETRY_BACKOFF = [1, 3, 8]  # seconds between attempts


class OpenRouterClient:
    """HTTP client for the OpenRouter OpenAI-compatible chat completion API.

    Supports automatic retry with exponential backoff on 429 and transient
    HTTP errors. Set ``json_mode=True`` (the default) to request a JSON
    object response from models that support it.
    """

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self._client = httpx.Client(
            base_url=_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def complete(
        self,
        model: str,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
    ) -> str:
        """Call the chat completions endpoint with retry + backoff.

        Args:
            model: OpenRouter model identifier
                (e.g. ``"meta-llama/llama-3.3-70b-instruct:free"``).
            system: System prompt text.
            user: User message text.
            json_mode: Request a JSON object response (default True).

        Returns:
            The assistant message content string.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        backoffs = _RETRY_BACKOFF + [None]
        for attempt, backoff in enumerate(backoffs, start=1):
            try:
                response = self._client.post("/chat/completions", json=payload)
                if response.status_code == 429:
                    if backoff is None:
                        raise RuntimeError(
                            f"OpenRouter rate-limited after {attempt} attempts"
                        )
                    logger.warning(
                        "openrouter_rate_limited", attempt=attempt, backoff=backoff
                    )
                    time.sleep(backoff)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                if backoff is None:
                    raise RuntimeError(
                        f"OpenRouter HTTP error after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "openrouter_http_error",
                    status=exc.response.status_code,
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(backoff)
            except httpx.RequestError as exc:
                if backoff is None:
                    raise RuntimeError(
                        f"OpenRouter request error after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "openrouter_request_error",
                    error=str(exc),
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(backoff)

        raise RuntimeError("OpenRouter request failed after all retries")

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
