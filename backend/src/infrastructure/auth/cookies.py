"""Утилиты для работы с auth-cookie.

Устанавливает httponly-cookie для access/refresh токенов
и Google OAuth state.
"""

import logging
import secrets

from fastapi import Response

from src.config import settings

logger = logging.getLogger(__name__)


def set_token_cookies_auth(response: Response, access_token: str, refresh_token: str) -> None:
    """Устанавливает access и refresh токены в httponly cookie."""
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=settings.auth_session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.samesite,
        max_age=settings.access_token_expire_minutes * 60,
        domain=settings.domain,
        path=settings.access_cookie_path,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=settings.auth_session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.samesite,
        max_age=settings.refresh_token_expire_days * 86400,
        domain=settings.domain,
        path=settings.refresh_cookie_path,
    )
    logger.debug("Токены для авторизации установлены в cookie")


def generate_csrf_token() -> str:
    """Генерирует криптографически стойкий CSRF токен."""
    return secrets.token_urlsafe(32)


def set_token_cookies_csrf(response: Response, csrf_token: str) -> None:
    """Устанавливает CSRF cookie для double-submit проверки."""
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=settings.csrf_session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.samesite,
        domain=settings.domain,
        path=settings.csrf_cookie_path,
    )
    logger.debug("CSRF Токены установлены в cookie")


def set_cookies_google_oauth_state(response: Response, state: str) -> None:
    """Устанавливает CSRF-state для Google OAuth в httponly cookie (TTL 5 мин)."""
    response.set_cookie(
        key="google_oauth_state",
        value=state,
        httponly=True,
        max_age=300,
        samesite=settings.samesite,
        secure=settings.session_cookie_secure,
    )
    logger.debug("Google OAuth state установлен в cookie")
