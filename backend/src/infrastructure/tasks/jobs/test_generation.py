"""Фоновая задача: генерация теста через Gemini.

Запускается из TestService.request_test после того, как строка Test
(status=GENERATING) уже закоммичена в БД.
"""

import asyncio

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from celery.utils.log import get_task_logger

from src.infrastructure.tasks.celery_config import celery_app
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory
from src.application.interfaces.unitofwork import IUnitOfWork
from src.infrastructure.llm.gemini_client import GeminiClient
from src.infrastructure.llm.prompt_builder import PromptBuilder, load_templates
from src.infrastructure.llm.parser import TestParser
from src.application.interfaces.llm import (
    LLMError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    ParseError,
)
from src.domain.entities import Question, TestStatus
from src.config import settings

logger = get_task_logger(__name__)


async def _generate_and_save(
        uow: IUnitOfWork,
        llm_client: GeminiClient,
        prompt_builder: PromptBuilder,
        test_id: int,
        topic_name: str,
) -> str:
    async with uow:
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
            # Транзиентные ошибки — пробрасываем наверх, их перехватывает
            # autoretry_for на самой Celery-таске и откладывает попытку.
            # Просто пробрасываем ошибки выше, чтобы сделать позже ретрай
            raise
        except (LLMError, ParseError) as exc:
            # Ловим все остальные исключения.
            # Ретраить бесполезно, помечаем таску как завершенную, а генерацию теста как failed
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
                correct_answer=gq.options[gq.correct_index], # возвращаем индекс правильного ответа, а не текст
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


async def _mark_failed(database_url: str, test_id: int) -> None:
    """Аварийный fallback: тест остаётся GENERATING только если это ещё
    не обработано. Отдельный engine/сессия — та же причина, что и в
    _create_and_run (своя, не переживающая один asyncio.run() загрузка)."""
    # создаем свое подключение к бд
    engine = create_async_engine(url=database_url, poolclass=NullPool)
    try:
        # expire_on_commit=False - экономит ресурсы, после коммита не перепроверяет данные
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        uow = SQLAlchemyUnitOfWorkFactory(session_factory)()
        async with uow:
            test = await uow.tests.get_by_id(test_id)
            # test.status != TestStatus.GENERATING защита от гонки состояний
            if test is None or test.status != TestStatus.GENERATING:
                # Уже обработан (READY/FAILED) или удалён — трогать нечего.
                return
            test.status = TestStatus.FAILED
            await uow.tests.update(test)
            await uow.commit()
    finally:
        # закрываем соединения
        await engine.dispose()


class _GenerateTestTask(celery_app.Task):
    """
    on_failure срабатывает, когда таска ОКОНЧАТЕЛЬНО упала — в том числе
    после того, как autoretry_for исчерпал все попытки на
    LLMRateLimitError/LLMServiceUnavailableError. Без этого тест бы
    навсегда остался в status=GENERATING.
    Кастомный класс для таскки.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Синхронный метод с фиксированной сигнатурой, которую требует сам Celery
        exc — исключение,
        task_id — ID таски в Celery,
        args/kwargs — аргументы, с которыми таска была вызвана,
        einfo — объект с traceback-информацией"""
        # Строка получения test_id — защита от того, что таска могла быть вызвана как позиционно,
        # так и именованно:
        # generate_test_task.delay(created.id, topic.name) (позиционно, как в TestService)
        # или потенциально .delay(test_id=..., topic_name=...)
        # kwargs.get("test_id", args[0] if args else None) — сначала пробуем достать из именованных аргументов,
        # если там нет — берём первый позиционный (если он есть), иначе None
        # Такая защита нужна именно потому, что test_id необходим, чтобы вообще понять, какую строку в БД помечать как FAILED.
        test_id = kwargs.get("test_id", args[0] if args else None)
        if test_id is None:
            logger.error("on_failure: не удалось определить test_id для таски %s", task_id)
            return

        logger.error("Тест id=%s: генерация окончательно провалилась: %s", test_id, exc)
        try:
            # создаем новый event loop, выполняет корутину до завершения, закрывает loop.
            asyncio.run(_mark_failed(settings.database_url, test_id))
        except Exception:
            logger.exception("on_failure: не удалось пометить тест id=%s как FAILED", test_id)


async def _create_and_run(database_url: str, test_id: int, topic_name: str) -> str:
    """
    Свой engine/сессия/LLM-клиент внутри таски — как и в token_cleanup.py:
    httpx- и asyncpg-соединения привязаны к event loop-у, который создаёт
    asyncio.run(), поэтому переиспользовать глобальные синглтоны между
    запусками таски небезопасно (каждый запуск — новый loop).
    """
    # создаем подключение к бд на один event loop, потом закроем.
    engine = create_async_engine(url=database_url, poolclass=NullPool)
    try:
        # фабрика сессий
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)
        uow = uow_factory()

        # создание подключение на один event loop
        llm_client = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
            max_retries=settings.gemini_max_retries,
        )

        # загружаем шаблоны промптов
        test_gen_tpl, rec_tpl = load_templates()
        prompt_builder = PromptBuilder(test_gen_tpl=test_gen_tpl, rec_tpl=rec_tpl)

        return await _generate_and_save(uow, llm_client, prompt_builder, test_id, topic_name)
    finally:
        await engine.dispose()


@celery_app.task(
    name="generate_test",
    # подключаем кастомный класс с переопределённым on_failure
    base=_GenerateTestTask,
    # если внутри таски вылетит одно из этих исключений (не поймано нигде внутри и долетает досюда), Celery автоматически перезапустит таску
    autoretry_for=(LLMRateLimitError, LLMServiceUnavailableError),
    # включает экспоненциальную задержку между повторными попытками
    retry_backoff=True,
    # количество ретраев (всего 4 попытки: 1 + 3 ретрая)
    retry_kwargs={"max_retries": 3},
)
def generate_test_task(test_id: int, topic_name: str) -> str:
    """Синхронная точка входа Celery — запускает async-логику генерации."""
    logger.info("Запуск генерации теста id=%s тема=%r", test_id, topic_name)
    # оборачиваем асинхронную логику
    result = asyncio.run(_create_and_run(settings.database_url, test_id, topic_name))

    logger.info("Генерация теста id=%s завершена: %s", test_id, result)
    return result
