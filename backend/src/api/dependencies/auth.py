"""FastAPI-зависимости (Depends).

Фабрики для Unit of Work и сервиса аутентификации,
используемые через Dependency Injection в роутерах.
"""

import logging
from typing import Annotated

from fastapi import Cookie, Header, HTTPException, status, Depends
import jwt

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.interfaces.auth import AuthServiceProtocol
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory
from src.infrastructure.database.config_db import session_factory
from src.infrastructure.redis.auth_state import RedisAuthState
from src.infrastructure.redis.config_redis import redis_client
from src.application.services.auth_service import AuthService
from src.application.services.user_service import UserService
from src.application.services.token_service import TokenService
from src.application.services.google_auth_service import GoogleAuthService
from src.application.services.password_service import PasswordService
from src.config import settings

logger = logging.getLogger(__name__)

# Фабрика создаётся один раз при старте — session_factory переиспользуется
_uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)


# ── Unit of Work ─────────────────────────────────────────────────────

async def get_uow() -> IUnitOfWork:
    """Фабрика Unit of Work для Dependency Injection.

    Каждый запрос получает изолированный UoW с собственной сессией.
    """
    return _uow_factory()


# ── Сервисы ──────────────────────────────────────────────────────────

async def get_auth_service(
    uow: Annotated[IUnitOfWork, Depends(get_uow)],
) -> AuthServiceProtocol:
    """Фабрика сервиса аутентификации с внедрением всех зависимостей.

    Все сервисы получают один и тот же uow — одна транзакция на запрос.
    """
    redis = RedisAuthState(redis=redis_client)
    password_service = PasswordService()
    user_service = UserService(uow=uow, password_service=password_service)
    token_service = TokenService(uow=uow)
    google_auth_service = GoogleAuthService(redis=redis)
    return AuthService(
        uow=uow,
        user_service=user_service,
        token_service=token_service,
        google_auth_service=google_auth_service,
    )


# ── CSRF ─────────────────────────────────────────────────────────────

async def verify_csrf_token(
    csrf_cookie: Annotated[str | None, Cookie(alias=settings.csrf_cookie_name)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Проверяет CSRF double-submit cookie.

    Cookie устанавливается сервером (httponly=False),
    заголовок отправляет клиент — совпадение подтверждает подлинность запроса.
    """
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or incorrect",
        )


# ── Access Token ─────────────────────────────────────────────────────

async def get_token_from_cookie(
    access_token: Annotated[str | None, Cookie(alias=settings.access_cookie_name)] = None,
) -> str:
    """Извлекает access-токен из cookie."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден",
        )
    return access_token


async def get_current_payload(
    token: Annotated[str, Depends(get_token_from_cookie)],
    _csrf: Annotated[None, Depends(verify_csrf_token)],
) -> dict:
    """Декодирует и валидирует JWT access-токен.

    Зависит от verify_csrf_token — защищённые эндпоинты
    автоматически проверяют и CSRF, и токен.
    """
    try:
        payload = jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истек.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные.",
        )
