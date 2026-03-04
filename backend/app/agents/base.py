"""Base agent class with LLM calling and JSON parsing."""

from __future__ import annotations

import json
from typing import Generic, TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from app.exceptions import AgentError
from app.llm.base_client import BaseLLMClient, LLMMessage
from app.llm.config_loader import get_agent_config, get_client_for_model

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(Generic[T]):
    """Abstract base for LLM-backed agents.

    Subclasses set `agent_name` and `output_type`, then call
    `self._run(user_prompt)` to get a validated Pydantic model.
    """

    agent_name: str = ""
    output_type: type[T]

    def __init__(self) -> None:
        if not self.agent_name:
            raise AgentError("agent_name must be set on subclass")
        self._config = get_agent_config(self.agent_name)
        model_ref = self._config.get("model_ref")
        if not model_ref:
            raise AgentError(f"Agent '{self.agent_name}' has no model_ref")
        self._client: BaseLLMClient
        self._model_id: str
        self._client, self._model_id = get_client_for_model(model_ref)

    def _run(self, user_prompt: str) -> T:
        """Call the LLM and parse the response into output_type.

        Args:
            user_prompt: The user-role message describing what to produce.

        Returns:
            Validated Pydantic model of type T.

        Raises:
            AgentError: If the LLM response cannot be parsed.
        """
        system_prompt = self._config.get("system_prompt", "")
        temperature = self._config.get("temperature", 0.3)
        max_tokens = self._config.get("max_tokens", 1024)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        logger.info(
            "agent_call_start",
            agent=self.agent_name,
            model=self._model_id,
        )

        response = self._client.chat(
            messages,
            model=self._model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(
            "agent_call_complete",
            agent=self.agent_name,
            model=response.model,
            usage=response.usage,
        )

        return self._parse_response(response.content)

    def _parse_response(self, raw: str) -> T:
        """Extract JSON from the LLM response and validate it.

        Handles responses wrapped in markdown code fences.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [
                line
                for idx, line in enumerate(lines)
                if not (idx == 0 and line.startswith("```"))
                and not (idx == len(lines) - 1 and line.strip() == "```")
            ]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AgentError(
                f"Agent '{self.agent_name}' returned invalid JSON: {exc}\n"
                f"Raw response: {raw[:500]}"
            ) from exc

        try:
            return self.output_type.model_validate(data)
        except ValidationError as exc:
            raise AgentError(
                f"Agent '{self.agent_name}' JSON failed schema validation: {exc}"
            ) from exc
