"""LLM-интерфейсы."""

from .client import ILLMClient
from .exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMResponseError,
)

__all__ = [
    "ILLMClient",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMServiceUnavailableError",
    "LLMResponseError",
]