"""Зависимости (Dependencies) для HTTP-эндпоинтов квизов и LLM."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.interfaces.quiz import TestServiceProtocol, AttemptServiceProtocol
from src.application.services.quiz import TopicService, TestService, AttemptService
from src.api.dependencies.database import get_uow, open_short_uow
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


# ── Короткоживущие сервисы для SSE ──────────────────────────────────
#
# SSE-поток живёт минуты, поэтому сервисы для него нельзя получать через
# Depends(get_uow) — см. open_short_uow. Это не FastAPI-зависимости, а
# контекстные менеджеры: сессия БД открыта только внутри `async with`.
# Сервисы те же, что у обычных GET, — значит, и правила доступа те же.

@asynccontextmanager
async def open_test_service() -> AsyncIterator[TestServiceProtocol]:
    async with open_short_uow() as uow:
        yield TestService(uow, TopicService(uow))


@asynccontextmanager
async def open_attempt_service() -> AsyncIterator[AttemptServiceProtocol]:
    async with open_short_uow() as uow:
        yield AttemptService(uow)