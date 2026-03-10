"""Утилиты для работы с auth-cookie."""

from fastapi import Response

from src.config import settings


def set_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Устанавливает access и refresh токены в httponly cookie."""
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.samesite,
        max_age=settings.auth_access_token_expire_minutes * 60,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )

    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.samesite,
        max_age=settings.auth_refresh_token_expire_days * 86400,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
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
