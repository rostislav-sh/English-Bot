"""Контракт хранения OAuth state (Redis)."""

from typing import Protocol


class RedisAuthState(Protocol):
    """Протокол для сохранения и проверки OAuth CSRF-state."""

    async def save_state(self, state: str, ttl: int = 300) -> None:
        """Сохраняет state на определенное время."""

    async def consume_state(self, state: str) -> None:
        """Проверяет и удаляет state (одноразовый)."""
