"""Фоновая задача: генерация ИИ-рекомендации по ошибкам в попытке.

Запускается из AttemptService.submit_answers после того, как попытка
(recommendation_status=PENDING) уже закоммичена в БД.
"""

import asyncio

from celery.utils.log import get_task_logger

from src.infrastructure.tasks.celery_config import celery_app
from src.infrastructure.tasks.db import create_task_uow
from src.infrastructure.tasks.llm_deps import (
    LLM_TASK_SOFT_TIME_LIMIT,
    LLM_TASK_TIME_LIMIT,
    create_task_llm_client,
    get_prompt_builder,
)
from src.application.interfaces.unitofwork import IUnitOfWork
from src.infrastructure.llm.gemini_client import GeminiClient
from src.infrastructure.llm.prompt_builder import PromptBuilder
from src.infrastructure.llm.schemas import MistakeItem
from src.application.interfaces.llm import LLMError, LLMRateLimitError, LLMServiceUnavailableError
from src.domain.enums import RecommendationStatus

logger = get_task_logger(__name__)


async def _generate_and_save(
        uow: IUnitOfWork,
        llm_client: GeminiClient,
        prompt_builder: PromptBuilder,
        attempt_id: int,
) -> str:
    attempt = await uow.attempts.get_with_answer(attempt_id)
    if attempt is None:
        logger.warning("Попытка id=%s не найдена, генерация рекомендации пропущена", attempt_id)
        return "attempt not found"

    test = await uow.tests.get_with_questions(attempt.test_id)
    if test is None:
        logger.warning("Тест id=%s для попытки id=%s не найден", attempt.test_id, attempt_id)
        attempt.recommendation_status = RecommendationStatus.FAILED
        await uow.attempts.update(attempt)
        await uow.commit()
        return "test not found"

    topic = await uow.topics.get_by_id(test.topic_id)
    questions_by_id = {q.id: q for q in test.questions}

    mistakes = [
        MistakeItem(
            question=questions_by_id[a.question_id].text,
            user_answer=a.user_answer,
            correct_answer=questions_by_id[a.question_id].correct_answer,
        )
        for a in attempt.answers
        if not a.is_correct and a.question_id in questions_by_id
    ]
    if not mistakes:
        # Страховка: submit_answers диспатчит таску только при has_mistakes=True,
        # поэтому штатно список ошибок не пуст. Пустым он бывает, если:
        #  • неверно отвеченные вопросы удалены из теста (отфильтрованы выше
        #    по questions_by_id);
        #  • таску запустили вручную для попытки без ошибок (например, при тестировании).
        # Без этой ветки пустой список дошёл бы до for_recommendation, который
        # бросает PromptGenerationError, а попытка осталась бы в PENDING.
        attempt.recommendation_status = RecommendationStatus.NOT_NEEDED
        await uow.attempts.update(attempt)
        await uow.commit()
        return "no mistakes, recommendation not needed"

    topic_name = topic.name if topic is not None else f"topic #{test.topic_id}"
    prompt = prompt_builder.for_recommendation(topic_name, mistakes)

    try:
        raw = await llm_client.complete(prompt)
    except (LLMRateLimitError, LLMServiceUnavailableError):
        # Транзиентные ошибки (429 и 5**) — пробрасываем наверх, их перехватывает
        # autoretry_for на самой Celery-таске и откладывает попытку.
        raise
    except LLMError as exc:
        logger.error("Генерация рекомендации attempt_id=%s провалилась: %s", attempt_id, exc)
        attempt.recommendation_status = RecommendationStatus.FAILED
        await uow.attempts.update(attempt)
        await uow.commit()
        return f"failed: {exc}"

    attempt.ai_recommendation = raw
    attempt.recommendation_status = RecommendationStatus.READY
    await uow.attempts.update(attempt)
    await uow.commit()

    logger.info("Рекомендация для попытки id=%s сгенерирована", attempt_id)
    return "ready"


async def _mark_failed(attempt_id: int) -> None:
    """Аварийный fallback: если у autoretry_for закончились попытки (или упало
    что-то ещё необработанное), рекомендация не должна остаться в PENDING навсегда —
    та же логика, что и _mark_failed в test_generation.py."""
    async with create_task_uow() as uow:
        attempt = await uow.attempts.get_with_answer(attempt_id)
        if attempt is None or attempt.recommendation_status != RecommendationStatus.PENDING:
            return
        attempt.recommendation_status = RecommendationStatus.FAILED
        await uow.attempts.update(attempt)
        await uow.commit()


class _GenerateRecommendationTask(celery_app.Task):
    """on_failure — финальный fallback после исчерпания autoretry_for, см.
    аналогичный класс в test_generation.py."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # generate_recommendation_task.delay(created.id) передаёт id позиционно,
        # значит в on_failure придёт args=(created.id,) и пустой kwargs.
        # Строка kwargs.get("attempt_id", args[0] if args else None) работает так:
        # сначала ищет id в именованных аргументах, если вызвали delay(attempt_id=5), иначе берёт первый позиционный.
        attempt_id = kwargs.get("attempt_id", args[0] if args else None)
        if attempt_id is None:
            logger.error("on_failure: не удалось определить attempt_id для таски %s", task_id)
            return

        logger.error("Попытка id=%s: генерация рекомендации окончательно провалилась: %s", attempt_id, exc)
        try:
            asyncio.run(_mark_failed(attempt_id))
        except Exception:
            logger.exception("on_failure: не удалось пометить рекомендацию attempt_id=%s как FAILED", attempt_id)


async def _create_and_run(attempt_id: int) -> str:
    # Жизненный цикл ресурсов — см. комментарий к _create_and_run в test_generation.py.
    async with create_task_llm_client() as llm_client, create_task_uow() as uow:
        return await _generate_and_save(uow, llm_client, get_prompt_builder(), attempt_id)


@celery_app.task(
    name="generate_recommendation",
    base=_GenerateRecommendationTask,
    autoretry_for=(LLMRateLimitError, LLMServiceUnavailableError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    # См. комментарий к лимитам в test_generation.py.
    soft_time_limit=LLM_TASK_SOFT_TIME_LIMIT,
    time_limit=LLM_TASK_TIME_LIMIT,
)
def generate_recommendation_task(attempt_id: int) -> str:
    """Синхронная точка входа Celery — запускает async-логику генерации рекомендации."""
    logger.info("Запуск генерации рекомендации attempt_id=%s", attempt_id)

    result = asyncio.run(_create_and_run(attempt_id))

    logger.info("Генерация рекомендации attempt_id=%s завершена: %s", attempt_id, result)
    return result
