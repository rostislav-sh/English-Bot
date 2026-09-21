"""Зависимости (Dependencies) для HTTP-эндпоинтов квизов и LLM."""

from typing import Annotated

from fastapi import Depends, Request

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.services.quiz import TopicService
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
