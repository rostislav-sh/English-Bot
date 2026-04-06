from typing import TypeVar, Generic
from abc import ABC, abstractmethod


T = TypeVar("T")


class IBaseRepository(ABC, Generic[T]):
    """Базовый контракт"""

    @abstractmethod
    async def add(self, entity: T) -> T:
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        ...

    @abstractmethod
    async def delete(self, entity: T) -> T:
        ...

    @abstractmethod
    async def get_user_by_id(self, entity_id) -> "T | None":
        """Получение пользователя по id."""
        ...
