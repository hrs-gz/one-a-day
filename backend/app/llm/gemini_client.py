"""Google Gemini LLM client using the REST API directly."""

from __future__ import annotations

import time

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_RETRY_BACKOFF = [1, 3, 8]  # seconds between attempts


class GeminiClient:
    """HTTP client for the Google Gemini REST API.

    Uses ``response_mime_type: "application/json"`` in generationConfig so
    the model returns parseable JSON. Retries on 429 and transient errors.
    """

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self._api_key = settings.gemini_api_key
        self._client = httpx.Client(base_url=_BASE_URL, timeout=60.0)

    def complete(
        self,
        model: str,
        system: str,
        user: str,
    ) -> str:
        """Call Gemini generateContent with JSON output mode.

        Args:
            model: Gemini model identifier (e.g. ``"gemini-2.5-flash-lite"``).
            system: System instruction text.
            user: User message text.

        Returns:
            The response text (JSON string when json_mode is on).

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
            },
        }
        url = f"/models/{model}:generateContent"
        params = {"key": self._api_key}

        backoffs = _RETRY_BACKOFF + [None]
        for attempt, backoff in enumerate(backoffs, start=1):
            try:
                response = self._client.post(url, json=payload, params=params)
                if response.status_code == 429:
                    if backoff is None:
                        raise RuntimeError(
                            f"Gemini rate-limited after {attempt} attempts"
                        )
                    logger.warning(
                        "gemini_rate_limited", attempt=attempt, backoff=backoff
                    )
                    time.sleep(backoff)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPStatusError as exc:
                if backoff is None:
                    raise RuntimeError(
                        f"Gemini HTTP error after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "gemini_http_error",
                    status=exc.response.status_code,
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(backoff)
            except httpx.RequestError as exc:
                if backoff is None:
                    raise RuntimeError(
                        f"Gemini request error after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "gemini_request_error",
                    error=str(exc),
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(backoff)

        raise RuntimeError("Gemini request failed after all retries")

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
