"""LLM-зависимости для Celery-тасок генерации (GeminiClient + PromptBuilder)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from src.config import settings
from src.infrastructure.llm.gemini_client import GeminiClient
from src.infrastructure.llm.prompt_builder import PromptBuilder, load_templates

# Лимиты времени для LLM-тасок, чтобы зависшая таска не держала воркер
# и соединение к Gemini. Считаются от настроек клиента, а не хардкодом:
# худший случай — (max_retries + 1) попыток по таймауту, плюс паузы
# tenacity между ними (не больше 2 с, см. GeminiClient) и запас на БД.
LLM_TASK_SOFT_TIME_LIMIT = (
    (settings.gemini_max_retries + 1) * settings.gemini_timeout_seconds
    + settings.gemini_max_retries * 2
    + 20
)
# Жёсткий лимит — страховка, если soft-лимит не сработал (например, код
# завис вне Python). Процесс воркера убивается, on_failure не вызывается.
LLM_TASK_TIME_LIMIT = LLM_TASK_SOFT_TIME_LIMIT + 30


@asynccontextmanager
async def create_task_llm_client() -> AsyncIterator[GeminiClient]:
    """
    Открывает GeminiClient на время блока и гарантированно закрывает его.

    Сессия SDK привязана к event loop-у, а каждый запуск таски — это свой
    asyncio.run(), поэтому клиент создаём на каждый вызов. Без явного
    aclose() соединения к Gemini висели бы до сборки мусора и копились
    при большом потоке тасок.

    Использование:

        async with create_task_llm_client() as llm_client:
            ...
    """
    llm_client = GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )
    try:
        yield llm_client
    finally:
        await llm_client.aclose()


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    """PromptBuilder не держит сетевых ресурсов — один инстанс на процесс воркера.
    Возвращаем готовый объект PromptBuilder"""
    test_gen_tpl, rec_tpl = load_templates()
    return PromptBuilder(test_gen_tpl=test_gen_tpl, rec_tpl=rec_tpl)
