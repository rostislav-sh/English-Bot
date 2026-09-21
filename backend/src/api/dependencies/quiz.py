"""Зависимости (Dependencies) для HTTP-эндпоинтов квизов и LLM."""

from typing import Annotated

from fastapi import Depends, Request

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.interfaces.quiz import TestServiceProtocol, AttemptServiceProtocol
from src.application.services.quiz import TopicService, MockTestService, MockAttemptService
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


# ── Фаза 1: мок-сервисы тестов/попыток ──────────────────────────────
#
# TODO(фаза 2): заменить на реальные TestService(uow, ...)/AttemptService(uow, ...).
# Роутеры типизированы через Protocol (TestServiceProtocol/AttemptServiceProtocol),
# поэтому замена не потребует правок в роутерах — только здесь.
#
# Синглтоны на процесс: моки хранят состояние в памяти, чтобы фронтендер
# мог пройти тест и увидеть попытку в истории в рамках одной сессии сервера.
_mock_test_service = MockTestService()
_mock_attempt_service = MockAttemptService(_mock_test_service)


async def get_test_service() -> TestServiceProtocol:
    """Провайдер сервиса тестов (сейчас — мок)."""
    return _mock_test_service


async def get_attempt_service() -> AttemptServiceProtocol:
    """Провайдер сервиса прохождения тестов (сейчас — мок)."""
    return _mock_attempt_service