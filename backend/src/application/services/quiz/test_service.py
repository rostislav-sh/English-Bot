"""Сервис получения тестов: переиспользование готового или запуск генерации."""

import logging

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.services.quiz.topic_service import TopicService
from src.domain.entities import Test
from src.domain.enums import TestStatus
from src.domain.exceptions import TestNotFoundError

logger = logging.getLogger(__name__)


class TestService:
    """
    request_test — единственная точка входа для получения теста по теме:
        1) находит/создаёт тему через TopicService;
        2) ищет готовый непройденный тест (uow.tests.find_reusable_for_user);
        3) если нет — создаёт Test(status=GENERATING) и запускает
           Celery-таску генерации (реализована в
           infrastructure/tasks/jobs/test_generation.py).
    """

    def __init__(self, uow: IUnitOfWork, topic_service: TopicService) -> None:
        self._uow = uow
        self._topic_service = topic_service

    async def request_test(self, user_id: int, topic_name: str) -> Test:
        topic = await self._topic_service.get_or_create_topic(topic_name)

        reusable = await self._uow.tests.find_reusable_for_user(topic.id, user_id)
        if reusable is not None:
            logger.debug(
                "TestService: переиспользован тест id=%s тема=%s", reusable.id, topic.name,
            )
            return reusable

        test = Test(topic_id=topic.id, status=TestStatus.GENERATING)
        created = await self._uow.tests.add(test)
        # Коммитим сразу: тест должен быть виден воркеру Celery до того,
        # как мы задиспатчим таску — иначе воркер может не найти строку.
        await self._uow.commit()

        # Локальный импорт: application-слой не должен тянуть Celery на этапе
        # импорта модуля (нужен только при реальном запросе генерации).
        from src.infrastructure.tasks.jobs.test_generation import generate_test_task
        task = generate_test_task.delay(created.id, topic.name)

        created.generation_task_id = task.id
        await self._uow.tests.update(created)
        await self._uow.commit()

        logger.info(
            "TestService: запущена генерация теста id=%s тема=%s task_id=%s",
            created.id, topic.name, task.id,
        )
        return created

    async def get_test(self, user_id: int, test_id: int) -> Test:
        test = await self._uow.tests.get_with_questions(test_id)
        if test is None:
            raise TestNotFoundError()
        return test
