from __future__ import annotations


class OADError(Exception):
    """Base exception for all domain errors."""


class LeadExistsError(OADError):
    """Raised when attempting to create a lead for a date that already has one."""


class SourceNotFoundError(OADError):
    """Raised when a ScraperSource ID doesn't exist."""


class ScraperError(OADError):
    """Raised when a scraper fails (HTTP error, parse error, timeout)."""


class AgentError(OADError):
    """Raised when an agent fails to produce valid output."""


class LLMProviderError(OADError):
    """Raised when an LLM provider is unreachable or misconfigured."""
