"""Зависимости (Dependencies) для HTTP-эндпоинтов квизов и LLM."""

from typing import Annotated

from fastapi import Depends, Request

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.interfaces.quiz import TestServiceProtocol, AttemptServiceProtocol
from src.application.services.quiz import TopicService, TestService, AttemptService
from src.api.dependencies.database import get_uow
from src.infrastructure.llm.prompt_builder import PromptBuilder


def get_prompt_builder(request: Request) -> PromptBuilder:
    """Извлекает шаблоны из state приложения и возвращает сборщик (DI)."""
    return PromptBuilder(
        test_gen_tpl=request.app.state.tpl_test_gen,
        rec_tpl=request.app.state.tpl_recommendation,
    )

async def get_topic_service(uow: Annotated[IUnitOfWork, Depends(get_uow)]) -> TopicService:
    """Провайдер TopicService."""
    return TopicService(uow)


# ── Фаза 2: реальные сервисы тестов/попыток ─────────────────────────
#
# Роутеры типизированы через Protocol (TestServiceProtocol/AttemptServiceProtocol),
# поэтому переход с моков (Фаза 1) на эти реализации не потребовал правок
# в роутерах — только здесь. Мок-реализации остались в services/quiz/mocks.py
# (например, для юнит-тестов роутеров без реальной БД/Celery).

async def get_test_service(uow: Annotated[IUnitOfWork, Depends(get_uow)]) -> TestServiceProtocol:
    """Провайдер сервиса тестов."""
    return TestService(uow, TopicService(uow))


async def get_attempt_service(uow: Annotated[IUnitOfWork, Depends(get_uow)]) -> AttemptServiceProtocol:
    """Провайдер сервиса прохождения тестов."""
    return AttemptService(uow)