"""Фоновая задача: генерация теста через Gemini.

Запускается из TestService.request_test после того, как строка Test
(status=GENERATING) уже закоммичена в БД.
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
from src.infrastructure.llm.parser import TestParser
from src.application.interfaces.llm import (
    LLMError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    ParseError,
)
from src.domain.entities import Question, TestStatus

logger = get_task_logger(__name__)


async def _generate_and_save(
        uow: IUnitOfWork,
        llm_client: GeminiClient,
        prompt_builder: PromptBuilder,
        test_id: int,
        topic_name: str,
) -> str:
    test = await uow.tests.get_by_id(test_id)
    if test is None:
        # Тест мог быть удалён между диспатчем таски и её запуском — не наша забота.
        logger.warning("Тест id=%s не найден, генерация пропущена", test_id)
        return "test not found"

    # строим промпт
    prompt = prompt_builder.for_test_generation(topic_name)

    try:
        raw = await llm_client.complete(prompt, json_mode=True)
        generated = TestParser.parser(raw)
    except (LLMRateLimitError, LLMServiceUnavailableError):
        # Транзиентные ошибки (429, 5**) — пробрасываем наверх, их перехватывает
        # autoretry_for на самой Celery-таске и откладывает попытку.
        raise
    except (LLMError, ParseError) as exc:
        # Ловим все остальные исключения. Ретраить бесполезно, помечаем
        # генерацию теста как failed.
        logger.error("Генерация теста id=%s провалилась: %s", test_id, exc)
        test.status = TestStatus.FAILED
        await uow.tests.update(test)
        await uow.commit()
        return f"failed: {exc}"

    questions = [
        Question(
            test_id=test_id,
            text=gq.text,
            options=list(gq.options),
            correct_answer=gq.options[gq.correct_index],
        )
        for gq in generated.questions
    ]

    # массово вставляем вопросы
    await uow.tests.add_questions(questions)

    # обновляем статус теста
    test.status = TestStatus.READY
    await uow.tests.update(test)
    await uow.commit()

    logger.info("Тест id=%s сгенерирован: вопросов=%s", test_id, len(questions))
    return f"ready: questions={len(questions)}"


async def _mark_failed(test_id: int) -> None:
    """Аварийный fallback: тест остаётся GENERATING только если это ещё
    не обработано."""
    async with create_task_uow() as uow:
        test = await uow.tests.get_by_id(test_id)
        # test.status != TestStatus.GENERATING — защита от гонки состояний
        if test is None or test.status != TestStatus.GENERATING:
            # Уже обработан (READY/FAILED) или удалён — трогать нечего.
            return
        test.status = TestStatus.FAILED
        await uow.tests.update(test)
        await uow.commit()


class _GenerateTestTask(celery_app.Task):
    """
    on_failure срабатывает, когда таска ОКОНЧАТЕЛЬНО упала — в том числе
    после того, как autoretry_for исчерпал все попытки на
    LLMRateLimitError/LLMServiceUnavailableError, и после SoftTimeLimitExceeded
    (soft_time_limit). При жёстком time_limit процесс убивается и on_failure
    не вызывается — это крайний случай. Без этого тест бы
    навсегда остался в status=GENERATING.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Синхронный метод с фиксированной сигнатурой, которую требует сам Celery.
        exc — исключение, task_id — ID таски в Celery, args/kwargs — аргументы,
        с которыми таска была вызвана, einfo — объект с traceback-информацией."""
        # generate_test_task.delay(created.id, topic.name) вызывается позиционно
        # (как в TestService), но на случай именованного вызова подстраховываемся kwargs.
        test_id = kwargs.get("test_id", args[0] if args else None)
        if test_id is None:
            logger.error("on_failure: не удалось определить test_id для таски %s", task_id)
            return

        logger.error("Тест id=%s: генерация окончательно провалилась: %s", test_id, exc)
        try:
            asyncio.run(_mark_failed(test_id))
        except Exception:
            logger.exception("on_failure: не удалось пометить тест id=%s как FAILED", test_id)


async def _create_and_run(test_id: int, topic_name: str) -> str:
    # Оба ресурса открываются через async with внутри этого asyncio.run(), поэтому
    # закрываются в том же event loop-е — и при успехе, и при исключении
    # (ретрай Celery, SoftTimeLimitExceeded). Клиент Gemini создаётся на каждый
    # запуск (его сессия привязана к loop-у), engine БД — один на процесс (NullPool).
    async with create_task_llm_client() as llm_client, create_task_uow() as uow:
        return await _generate_and_save(uow, llm_client, get_prompt_builder(), test_id, topic_name)


@celery_app.task(
    name="generate_test",
    # подключаем кастомный класс с переопределённым on_failure
    base=_GenerateTestTask,
    # если внутри таски вылетит одно из этих исключений (не поймано нигде внутри
    # и долетает досюда), Celery автоматически перезапустит таску
    autoretry_for=(LLMRateLimitError, LLMServiceUnavailableError),
    # включает экспоненциальную задержку между повторными попытками
    retry_backoff=True,
    # количество ретраев (всего 4 попытки: 1 + 3 ретрая)
    retry_kwargs={"max_retries": 3},
    # soft-лимит бросает SoftTimeLimitExceeded внутри таски: asyncio.run отменяет
    # корутину, async with закрывают клиент Gemini и сессию БД, а on_failure
    # помечает тест как FAILED. Лимит действует на каждую попытку отдельно.
    soft_time_limit=LLM_TASK_SOFT_TIME_LIMIT,
    time_limit=LLM_TASK_TIME_LIMIT,
)
def generate_test_task(test_id: int, topic_name: str) -> str:
    """Синхронная точка входа Celery — запускает async-логику генерации."""
    logger.info("Запуск генерации теста id=%s тема=%r", test_id, topic_name)

    result = asyncio.run(_create_and_run(test_id, topic_name))

    logger.info("Генерация теста id=%s завершена: %s", test_id, result)
    return result
