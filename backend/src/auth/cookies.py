"""Утилиты для работы с auth-cookie."""

from fastapi import Response

from src.config import settings


def set_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Устанавливает access и refresh токены в httponly cookie."""
    response.set_cookie(
        key=settings.access_token_key,
        value=access_token,
        httponly=settings.httponly,
        secure=settings.secure,
        samesite=settings.samesite,
        max_age=settings.auth_access_token_expire_minus,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )

    response.set_cookie(
        key=settings.refresh_token_key,
        value=refresh_token,
        httponly=settings.httponly,
        secure=settings.secure,
        samesite=settings.samesite,
        max_age=settings.auth_refresh_token_expire_minus,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )
