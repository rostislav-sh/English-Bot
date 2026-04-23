"""Маршруты аутентификации.

Все эндпоинты: регистрация, вход, обновление токенов, Google OAuth.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Request, Response, status, HTTPException
from fastapi.params import Depends, Cookie
from fastapi.responses import RedirectResponse

from src.infrastructure.auth.cookies import (
    set_token_cookies_auth,
    set_cookies_google_oauth_state,
    set_token_cookies_csrf,
    generate_csrf_token,
)
from src.config import settings
from src.api.exceptions import AppError
from src.application.interfaces import AuthServiceProtocol
from src.api.dependencies import get_auth_service, verify_csrf_token
from src.api.schemas.auth import (
    Authentication, UserOut, AuthenticationUsername,
)
from src.api.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация пользователя",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def register(
        request: Request,
        data: AuthenticationUsername,
        response: Response,
        service: AuthServiceProtocol = Depends(get_auth_service),
):
    """Регистрация нового пользователя и выдача пары токенов."""
    logger.info("POST /register email=%s", data.email)
    user, pair = await service.register(email=data.email, password=data.password, username=data.username)
    set_token_cookies_auth(response, pair.access_token, pair.refresh_token)
    csrf_token = generate_csrf_token()
    set_token_cookies_csrf(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token
    return UserOut(
        username=user.username,
        email=user.email,
    )


@router.post(
    "/login",
    summary="Вход через JWT (access + refresh)",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def login(
        request: Request,
        data: Authentication,
        response: Response,
        service: AuthServiceProtocol = Depends(get_auth_service),
) -> UserOut:
    """Проверяет учётные данные и возвращает пару токенов (access + refresh)."""
    logger.info("POST /login email=%s", data.email)
    user, pair = await service.login(email=data.email, password=data.password)
    set_token_cookies_auth(response, pair.access_token, pair.refresh_token)
    csrf_token = generate_csrf_token()
    set_token_cookies_csrf(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token
    return UserOut(username=user.username, email=user.email)


@router.post(
    "/token/refresh",
    summary="Обновление токенов JWT (access + refresh)",
    dependencies=[Depends(verify_csrf_token)],
)
async def refresh(
        response: Response,
        refresh_token: Annotated[str | None, Cookie(alias=settings.refresh_cookie_name)] = None,
        service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, str]:
    """Обновление пары токенов по refresh токену."""
    logger.debug("POST /token/refresh")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token cookie missing")
    _, pair = await service.refresh(refresh_token)
    set_token_cookies_auth(response, pair.access_token, pair.refresh_token)
    csrf_token = generate_csrf_token()
    set_token_cookies_csrf(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token
    return {"message": "success"}


@router.post(
    "/logout",
    summary="Выход (инвалидация refresh токена)",
)
async def logout(
        response: Response,
        refresh_token: Annotated[str | None, Cookie(alias=settings.refresh_cookie_name)] = None,
        service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, str]:
    """Инвалидирует рефреш-токен и удаляет куки."""
    logger.info("POST /logout")
    if refresh_token:
        try:
            await service.logout(refresh_token)
        except AppError as exc:
            logger.warning("Ошибка при отзыве токена: %s", exc)

    response.delete_cookie(
        key=settings.access_cookie_name,
        path=settings.access_cookie_path,
        domain=settings.domain,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.domain,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path=settings.csrf_cookie_path,
        domain=settings.domain,
    )
    
    return {"message": "Успешный выход из системы"}


@router.get(
    "/auth/google",
    summary="Редирект на Google OAuth consent screen",
)
async def get_google_login_url(
        service: AuthServiceProtocol = Depends(get_auth_service),
) -> RedirectResponse:
    """Генерирует URL для редиректа пользователя на Google OAuth."""
    logger.info("GET /auth/google")

    url, state = await service.get_google_url()

    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    set_cookies_google_oauth_state(response=response, state=state)

    return response


@router.get(
    "/auth/google/callback",
    summary="Обрабатывает callback от Google",
)
@limiter.limit("5/minute")
async def google_auth_callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        google_oauth_state: str | None = Cookie(default=None),
        service: AuthServiceProtocol = Depends(get_auth_service),
) -> RedirectResponse:
    """Обрабатывает GET-редирект от Google: проверяет state, обменивает code на токены,
    ставит JWT-куки и редиректит пользователя на фронтенд."""
    logger.info("GET /auth/google/callback")

    base = settings.frontend_redirect_url

    # Google вернул ошибку (пользователь отменил вход и т.д.)
    if error or not code or not state:
        logger.warning("Ошибка Google OAuth или отсутствуют параметры: error=%s", error)
        return RedirectResponse(
            url=f"{base}?auth_error=google_cancelled", status_code=status.HTTP_302_FOUND,
        )

    # Проверка CSRF: state из cookie должен совпадать с state из query
    if not google_oauth_state or google_oauth_state != state:
        logger.warning("Несоответствие состояний: cookie=%s query=%s", google_oauth_state, state)
        return RedirectResponse(
            url=f"{base}?auth_error=csrf_mismatch", status_code=status.HTTP_302_FOUND,
        )

    # Бизнес-логика: обмен code → токены, поиск/создание пользователя
    try:
        _, pair = await service.authenticate_via_google(code=code, state=state)
    except AppError as exc:
        logger.error("Бизнес ошибка Google OAuth: %s", exc)
        return RedirectResponse(
            url=f"{base}?auth_error=google_auth_failed", status_code=status.HTTP_302_FOUND,
        )

    # Успех — редирект на фронтенд с JWT-куками
    response = RedirectResponse(url=base, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="google_oauth_state", path="/", domain=settings.domain)
    set_token_cookies_auth(response, pair.access_token, pair.refresh_token)
    csrf_token = generate_csrf_token()
    set_token_cookies_csrf(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token

    logger.info("Проверка подлинности Google OAuth завершена. Редирект на фронтенд.")
    return response