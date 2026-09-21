"""Зависимости для LLM-клиента."""

from functools import lru_cache

from src.config import settings
from src.application.interfaces.llm import ILLMClient
from src.infrastructure.llm.gemini_client import GeminiClient


@lru_cache()
def get_llm_client() -> ILLMClient:
    """
    Провайдер LLM-клиента.

    Использует lru_cache, чтобы инстанс (и его httpx-пул соединений)
    создавался один раз при старте приложения и переиспользовался, а не плодили соединения.
    """
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )
