from abc import ABC, abstractmethod

from src.application.interfaces.base_repository import IBaseRepository
from src.domain.entities import User, RefreshToken



class IUserRepository(IBaseRepository[User], ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None."""
        ...

    @abstractmethod
    async def get_by_google_id(self, google_id: str) -> User | None:
        """Возвращает пользователя по google_id или None."""
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Проверяет существование пользователя без загрузки записи."""
        ...


class IRefreshTokenRepository(IBaseRepository[RefreshToken], ABC):
    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Возвращает токен по SHA-256 хэшу или None."""
        ...

    @abstractmethod
    async def get_active_by_user_id(self, user_id: int) -> list[RefreshToken]:
        """Возвращает активные токены пользователя, отсортированные по дате создания."""
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: int) -> int:
        """Bulk UPDATE — один SQL-запрос, отзывает все активные токены пользователя."""
        ...

    @abstractmethod
    async def delete_stale_for_user(self, user_id: int) -> int:
        """Удаляет протухшие и отозванные токены конкретного пользователя."""
        ...

    @abstractmethod
    async def delete_oldest_beyond_limit(self, user_id: int, keep: int) -> int:
        """Удаляет активные токены сверх лимита, оставляя keep самых свежих."""
        ...

    @abstractmethod
    async def delete_expired_global(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
        ...
