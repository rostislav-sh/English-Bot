"""
Реализация базового репозитория через SQLAlchemy.
"""
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import IBaseRepository
from src.domain.exceptions import EntityNotFoundError, MissingEntityIdError

logger = logging.getLogger(__name__)

T_Entity = TypeVar("T_Entity")


class SQLAlchemyBaseRepository(IBaseRepository[T_Entity], ABC):
    """
    Базовый репозиторий.

    Реализует identity map:
      - Все загруженные entity отслеживаются (entity → orm_model).
      - При commit() UoW вызывает sync_tracked():
        изменения из entity переносятся в orm_model,
        SQLAlchemy генерирует UPDATE автоматически.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # { id(entity) → (entity, orm_model) }
        self._identity_map: dict[int, tuple[T_Entity, object]] = {}

    # ── Абстрактные методы ───────────────────────────────────────────

    @abstractmethod
    def _get_model_class(self) -> type:
        """Возвращает класс ORM-модели. Пример: return UserModel."""
        ...

    @abstractmethod
    def _to_entity(self, model: object) -> T_Entity:
        """ORM-модель → доменная сущность."""
        ...

    @abstractmethod
    def _to_model(self, entity: T_Entity) -> object:
        """Доменная сущность → ORM-модель (для INSERT)."""
        ...

    @abstractmethod
    def _update_model(self, model: object, entity: T_Entity) -> None:
        """Синхронизирует изменения entity → ORM-модель (для UPDATE).

        Не трогаем: id, created_at — иммутабельны.
        updated_at — управляет SQLAlchemy через onupdate.
        """
        ...

    # ── Identity map ─────────────────────────────────────────────────

    def _track(self, model: object) -> T_Entity:
        """
        Конвертирует ORM-модель в entity и регистрирует пару в identity map.
        Все методы get_* обязаны проходить через _track().
        """
        entity = self._to_entity(model)
        self._identity_map[id(entity)] = (entity, model)
        return entity

    def sync_tracked(self) -> None:
        """
        Синхронизирует изменения всех отслеживаемых entity → ORM-модели.

        Вызывается UoW автоматически перед commit().
        Это необходимо потому что домен работает с entity напрямую:

            user = await uow.users.get_by_email("alice@example.com")
            user.username = "Alice"   # ← меняем entity
            await uow.commit()        # ← UoW вызывает sync_tracked()
                                      #   чтобы изменения попали в ORM-модель
        """
        for entity, model in self._identity_map.values():
            self._update_model(model, entity)

    def _evict_tracked(self, predicate: Callable[[T_Entity], bool]) -> None:
        """
        Удаляет сущности из _identity_map по условию.

        Вызывается после bulk UPDATE/DELETE, чтобы sync_tracked()
        не откатил изменения через устаревшие entity.

        Пример:
            self._evict_tracked(lambda e: e.user_id == user_id)
        """
        keys_to_remove = [
            key
            for key, (entity, _) in self._identity_map.items()
            if predicate(entity)
        ]
        for key in keys_to_remove:
            del self._identity_map[key]

        if keys_to_remove:
            logger.debug(
                "_evict_tracked: удалено из identity_map=%d",
                len(keys_to_remove),
            )

    # ── CRUD ─────────────────────────────────────────────────────────

    async def add(self, entity: T_Entity) -> T_Entity:
        """
        Добавляет entity в БД.
        После flush entity получает id назначенный БД.
        """
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        result = self._track(model)
        logger.debug(
            "add: %s id=%s",
            type(result).__name__,
            getattr(result, "id", "?"),
        )
        return result

    async def get_by_id(self, entity_id: int) -> T_Entity | None:
        """Возвращает entity по id или None."""
        model = await self._session.get(self._get_model_class(), entity_id)
        if model is None:
            return None
        return self._track(model)

    async def update(self, entity: T_Entity) -> T_Entity:
        """
        Обновляет запись в БД.

        Быстрый путь: entity есть в identity map → синхронизируем поля.
        Медленный путь: entity нет в map → SELECT по id → синхронизируем.
        """
        # Быстрый путь
        entry = self._identity_map.get(id(entity))
        if entry is not None:
            _, model = entry
            self._update_model(model, entity)
            return entity

        # Медленный путь
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            raise MissingEntityIdError(entity, operation="update")

        model = await self._session.get(self._get_model_class(), entity_id)
        if model is None:
            raise EntityNotFoundError(type(entity).__name__, entity_id)

        self._update_model(model, entity)
        self._identity_map[id(entity)] = (entity, model)
        return entity

    async def delete(self, entity: T_Entity) -> None:
        """Удаляет entity из БД."""
        # Быстрый путь: модель в identity map
        entry = self._identity_map.pop(id(entity), None)
        if entry is not None:
            _, model = entry
            await self._session.delete(model)
            logger.debug(
                "delete (identity map): %s id=%s",
                type(entity).__name__,
                getattr(entity, "id", "?"),
            )
            return

        # Медленный путь: SELECT по id
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            raise MissingEntityIdError(entity, operation="delete")

        model = await self._session.get(self._get_model_class(), entity_id)
        if model is not None:
            await self._session.delete(model)
            logger.debug(
                "delete (db fetch): %s id=%s",
                type(entity).__name__,
                entity_id,
            )
