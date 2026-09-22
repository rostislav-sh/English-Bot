"""Интерфейс провайдера токенов — для инверсии зависимости."""

from typing import Protocol


class TokenExpiredError(ValueError):
    """JWT истёк."""


class TokenInvalidError(ValueError):
    """JWT невалиден или неверного типа."""


class ITokenProvider(Protocol):
    """Абстракция над JWT-провайдером.

    Скрывает конкретную библиотеку (PyJWT / python-jose / ...).
    Сервисы зависят только от этого Protocol.
    """
    def hash_session_token(self, token: str) -> str:
        """Возвращает SHA-256 хэш токена для безопасного хранения в БД."""
        ...

    def create_access_token(self, user_id: int) -> str:
        """Создаёт короткоживущий JWT access-токен."""
        ...

    def create_refresh_token(self, user_id: int) -> str:
        """Создаёт долгоживущий JWT refresh-токен."""
        ...

    def decode_refresh_token(self, raw_token: str) -> dict:
        """Декодирует и верифицирует refresh JWT.

        Проверяет подпись, exp, тип токена.
        Вызывать ДО hash-lookup в БД — дешёвая проверка без IO.

        Raises:
            TokenExpiredError: токен истёк.
            TokenInvalidError: подпись невалидна или тип неверный.
        """
        ...
