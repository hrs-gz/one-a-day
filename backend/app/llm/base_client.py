"""Abstract base class for LLM provider clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """A single message in a chat conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class BaseLLMClient(ABC):
    """Abstract LLM client. Subclasses wrap a specific provider SDK."""

    provider_name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send a chat completion request and return the response.

        Args:
            messages: Conversation messages.
            model: Model ID (provider-specific).
            temperature: Sampling temperature.
            max_tokens: Max tokens in the response.

        Returns:
            LLMResponse with the assistant's reply.

        Raises:
            LLMProviderError: On any provider failure.
        """
        ...
