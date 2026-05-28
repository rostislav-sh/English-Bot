"""Сервис управления темами квизов."""

import logging

from src.application.interfaces.unitofwork import IUnitOfWork
from src.domain.entities import Topic

logger = logging.getLogger(__name__)


class TopicService:
    """
    Управление темами: создание, поиск, список системных тем.

    Простейший сервис — почти прямая обёртка над репозиторием,
    но изолирует роутеры от прямого доступа к UoW.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def get_or_create_topic(self, name: str, *, is_custom: bool = False) -> Topic:
        """
        Получить тему по имени или создать новую.

        Нормализация имени (lowercase, strip) — доменная логика,
        делается здесь, а не в репозитории.

        :param name: название темы (как ввёл юзер).
        :param is_custom: True — пользовательская тема, False — системная.
        :return: существующая или новая тема.
        """
        normalized_name = self._normalize_topic_name(name)

        # Проверяем, есть ли уже такая тема
        existing = await self._uow.topics.get_by_normalized_name(normalized_name)
        if existing:
            logger.debug("Topic '%s' уже существует (id=%s)", name, existing.id)
            return existing

        # Создаём новую
        topic = Topic(
            name=name.strip(),
            normalized_name=normalized_name,
            is_custom=is_custom,
        )

        created = await self.topics.get_or_create(topic)
        return created

    async def list_system_topics(self) -> list[Topic]:
        """
        Список системных тем для UI (дропдаун выбора темы).

        Системные темы (is_custom=False) — это предустановленный набор,
        который мы заранее засеяли в БД через миграцию или seed-скрипт.
        """
        return await self._uow.topics.list_system_topics()

    async def get_by_id(self, topic_id: int) -> Topic | None:
        """
        Получить тему по ID.

        Используется в сервисах генерации/статистики, когда нужно
        проверить существование темы или получить её название.
        """
        return await self._uow.topics.get_by_id(topic_id)

    async def get_by_normalized_name(self, normalized_name: str) -> Topic | None:
        """
        Получить тему по нормализованному имени.

        Полезно для проверки существования темы без создания новой.
        """
        return await self._uow.topics.get_by_normalized_name(normalized_name)


    @staticmethod
    def _normalize_topic_name(name: str) -> str:
        """
        Нормализация имени темы для дедупликации.

        Правила:
            • lowercase
            • strip пробелов с краёв
            • множественные пробелы → один пробел

        Примеры:
            "Present Simple"  → "present simple"
            "  IT   Slang  "  → "it slang"
            "Python"          → "python"
        """
        return " ".join(name.strip().lower().split())
