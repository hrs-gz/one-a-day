"""Load LLM provider and agent config from YAML files.

Reads config/models.yaml and config/agents.yaml from the project root,
caches the parsed dicts, and provides factory functions for LLM clients.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import settings
from app.exceptions import LLMProviderError
from app.llm.base_client import BaseLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.openrouter_client import OpenRouterClient

# Project root is three dirs up from this file:
# backend/app/llm/config_loader.py → project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@lru_cache
def load_models_config() -> dict[str, Any]:
    """Load and cache config/models.yaml."""
    path = _PROJECT_ROOT / "config" / "models.yaml"
    if not path.exists():
        raise LLMProviderError(f"models.yaml not found at {path}")
    with open(path) as f:
        return yaml.safe_load(f)


@lru_cache
def load_agents_config() -> dict[str, Any]:
    """Load and cache config/agents.yaml."""
    path = _PROJECT_ROOT / "config" / "agents.yaml"
    if not path.exists():
        raise LLMProviderError(f"agents.yaml not found at {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def get_agent_config(agent_name: str) -> dict[str, Any]:
    """Return the config block for a named agent from agents.yaml."""
    agents = load_agents_config().get("agents", {})
    if agent_name not in agents:
        raise LLMProviderError(f"Agent '{agent_name}' not found in agents.yaml")
    return agents[agent_name]


def _resolve_api_key(env_var: str) -> str:
    """Resolve an API key from an environment variable name."""
    # Try settings first, then os.environ
    key = getattr(settings, env_var.lower(), None) or os.environ.get(env_var, "")
    if not key:
        raise LLMProviderError(
            f"API key not set: configure {env_var} in .env or environment"
        )
    return key


def _get_runtime_config() -> dict[str, Any]:
    """Return the runtime section from models.yaml."""
    return load_models_config().get("runtime", {})


def get_client_for_model(model_ref: str) -> tuple[BaseLLMClient, str]:
    """Return an LLM client + model ID for a named model reference.

    Args:
        model_ref: Key from models.yaml 'models' section (e.g. 'planner').

    Returns:
        Tuple of (client, model_id).

    Raises:
        LLMProviderError: If provider or model is misconfigured.
    """
    cfg = load_models_config()
    models = cfg.get("models", {})
    providers = cfg.get("providers", {})
    runtime = cfg.get("runtime", {})

    if model_ref not in models:
        raise LLMProviderError(f"Model ref '{model_ref}' not in models.yaml")

    model_cfg = models[model_ref]
    provider_name = model_cfg["provider"]
    model_id = model_cfg["id"]

    if provider_name not in providers:
        raise LLMProviderError(f"Provider '{provider_name}' not in models.yaml")

    provider_cfg = providers[provider_name]
    retries = runtime.get("retries", {})
    max_attempts = retries.get("max_attempts", 3)
    backoff = retries.get("backoff_seconds", [1, 3, 8])

    api_key = _resolve_api_key(provider_cfg["api_key_env"])

    if provider_cfg["type"] == "openai_compatible":
        client = OpenRouterClient(
            api_key=api_key,
            base_url=provider_cfg.get("base_url", "https://openrouter.ai/api/v1"),
            max_attempts=max_attempts,
            backoff_seconds=backoff,
        )
    elif provider_cfg["type"] == "gemini":
        client = GeminiClient(
            api_key=api_key,
            max_attempts=max_attempts,
            backoff_seconds=backoff,
        )
    else:
        raise LLMProviderError(f"Unknown provider type: {provider_cfg['type']}")

    return client, model_id
