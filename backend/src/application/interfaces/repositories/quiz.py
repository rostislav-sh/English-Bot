from abc import ABC, abstractmethod
from datetime import datetime

from src.application.interfaces.repositories.base import IBaseRepository
from src.domain.entities import Topic, Test, TestAttempt, MonthlyStats


class ITopicRepository(IBaseRepository[Topic], ABC):
    @abstractmethod
    async def get_by_normalized_name(self, normalized_name: str) -> Topic | None:
        ...

    @abstractmethod
    async def get_or_create(self, topic: Topic) -> Topic:
        """Идемпотентное создание темы по normalized_name."""
        ...

    @abstractmethod
    async def list_system_topics(self) -> list[Topic]:
        """Список системных тем для UI (is_custom=False)."""
        ...


class ITestRepository(IBaseRepository[Test], ABC):
    @abstractmethod
    async def get_with_questions(self, test_id: int) -> Test | None:
        ...

    @abstractmethod
    async def find_reusable_for_user(self, topic_id: int, user_id: int) -> Test | None:
        """Готовый тест по теме, который юзер ещё НЕ проходил."""
        ...


class IAttemptRepository(IBaseRepository[TestAttempt], ABC):
    @abstractmethod
    async def get_with_answer(self, attempt_id: int) -> TestAttempt | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int, *, limit: int, offset: int) -> list[TestAttempt | None]:
        """История попыток юзера, новые сверху."""
        ...

    @abstractmethod
    async def get_monthly_stats(self, user_id: int, since: datetime) -> list[MonthlyStats]:
        """Статистика по месяцам начиная с `since`, новые сверху."""
        ...

    @abstractmethod
    async def has_user_passed_test(self, user_id: int, test_id: int) -> bool:
        """Проверяет факт прохождения без загрузки записи в память."""
        ...
