"""Контракты сервисов квизов для слоя роутеров."""

from typing import Protocol

from src.domain.entities import Test, TestAttempt, MonthlyStats


class TestServiceProtocol(Protocol):
    """Минимальный контракт сервиса тестов, используемый через Depends.

    Роутеры зависят от этого протокола, а не от конкретной реализации.
    """

    async def request_test(self, user_id: int, topic_name: str) -> Test:
        """Получить тест по теме: переиспользовать готовый или запустить генерацию."""

    async def get_test(self, user_id: int, test_id: int) -> Test:
        """Получить тест с вопросами (для polling статуса генерации)."""


class AttemptServiceProtocol(Protocol):
    """Минимальный контракт сервиса прохождения тестов, используемый через Depends."""

    async def submit_answers(
            self, user_id: int, test_id: int, answers: list[tuple[int, str]],
    ) -> TestAttempt:
        """Проверяет ответы, сохраняет попытку и запускает генерацию рекомендации."""

    async def get_attempt(self, user_id: int, attempt_id: int) -> TestAttempt:
        """Получить попытку по id (для polling статуса рекомендации)."""

    async def list_history(self, user_id: int, *, limit: int, offset: int) -> list[TestAttempt]:
        """История попыток пользователя, новые сверху."""

    async def get_monthly_stats(self, user_id: int, *, months: int) -> list[MonthlyStats]:
        """Статистика пользователя по месяцам."""
