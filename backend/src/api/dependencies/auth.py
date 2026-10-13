"""FastAPI-зависимости (Depends).

Фабрики для Unit of Work и сервиса аутентификации,
используемые через Dependency Injection в роутерах.
"""

import logging
from typing import Annotated

from fastapi import Cookie, Header, HTTPException, status, Depends
import jwt

from src.application.interfaces.unitofwork import IUnitOfWork
from src.api.dependencies.database import get_uow
from src.application.interfaces.auth import AuthServiceProtocol
from src.infrastructure.redis.auth_state import RedisAuthState
from src.infrastructure.redis.config_redis import redis_client
from src.infrastructure.http.http_client import get_http_client
from src.infrastructure.auth.tokens import tokens
from src.application.services import (
    AuthService,
    UserService,
    TokenService,
    GoogleAuthService,
    PasswordService,
)
from src.config import settings

logger = logging.getLogger(__name__)


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
    token_service = TokenService(uow=uow, tokens_provider=tokens)
    google_auth_service = GoogleAuthService(
        redis=redis,
        http_session=get_http_client(),
    )
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
    return decode_access_token(token)


async def get_current_payload_without_csrf(
    token: Annotated[str, Depends(get_token_from_cookie)],
) -> dict:
    """То же, что get_current_payload, но без проверки CSRF.

    Только для read-only эндпоинтов, которые физически не могут прислать
    заголовок X-CSRF-Token, — SSE-потоков (браузерный EventSource не умеет
    задавать заголовки). Это безопасно: CSRF-атака — это заставить браузер
    жертвы выполнить ИЗМЕНЯЮЩИЙ запрос с её cookie; такие эндпоинты ничего
    не меняют, а прочитать ответ чужой сайт не даст CORS (allow_origins).
    Изменяющие эндпоинты должны использовать get_current_payload.
    """
    return decode_access_token(token)


def decode_access_token(token: str) -> dict:
    """Проверяет подпись и срок жизни access-токена, возвращает payload.

    Общая логика для обеих payload-зависимостей выше: правила проверки
    токена живут в одном месте, отличается только наличие CSRF-проверки.
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
