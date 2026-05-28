"""LLM-интерфейсы."""

from .client import ILLMClient
from .exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMResponseError,
    PromptGenerationError,
    LLMParseError
)

__all__ = [
    "ILLMClient",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMServiceUnavailableError",
    "LLMResponseError",
    "PromptGenerationError",
    "LLMParseError"
]