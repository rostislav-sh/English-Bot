"""Маршруты аутентификации.

Все эндпоинты: регистрация, вход, обновление токенов, Google OAuth.
"""

from fastapi import APIRouter, Response, status
from fastapi.params import Depends

from fastapi import APIRouter, Request, Response, status
from fastapi.params import Depends, Cookie
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.auth.cookies import set_token_cookies, set_cookies_google_oauth_state
from src.config import settings
from src.exceptions import AppError
from src.interfaces import AuthServiceProtocol
from src.routers.dependencies import get_user_service
from src.routers.schemas.auth import (
    Authentication, RegisterOut, RefreshRequest,
)
from src.schemas.auth import TokenPair
from src.service.auth import AuthService
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация пользователя",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def register(
        request: Request,
        data: Authentication,
        response: Response,
        service: AuthServiceProtocol = Depends(get_user_service),
):
    """Регистрация нового пользователя и выдача пары токенов."""
    user, pair = await service.register(email=data.email, password=data.password)
    set_token_cookies(response, pair.access_token, pair.refresh_token)
    return RegisterOut(
        id=user.id,
        email=user.email,
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


@router.post(
    "/login",
    summary="Вход через JWT (access + refresh)",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def login(
        request: Request,
        data: Authentication,
        response: Response,
        service: AuthServiceProtocol = Depends(get_user_service),
) -> TokenPair:
    """Проверяет учётные данные и возвращает пару токенов (access + refresh)."""

    _, pair = await service.login(email=data.email, password=data.password)
    set_token_cookies(response, pair.access_token, pair.refresh_token)
    return pair


@router.post(
    "/token/refresh",
    summary="Обновление токенов JWT (access + refresh)",
    response_model=TokenPair,
)
async def refresh(
        data: RefreshRequest,
        response: Response,
        service: AuthServiceProtocol = Depends(get_user_service),
) -> TokenPair:
    """Обновление пары токенов по refresh токену."""
    _, pair = await service.refresh(data.refresh_token)
    set_token_cookies(response, pair.access_token, pair.refresh_token)
    return pair


@router.get(
    "/auth/google",
    summary="Редирект на Google OAuth consent screen",
)
async def get_google_login_url(
        service: AuthServiceProtocol = Depends(get_user_service),
) -> RedirectResponse:
    """Генерирует URL для редиректа пользователя на Google OAuth."""

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
        service: AuthServiceProtocol = Depends(get_user_service),
) -> RedirectResponse:
    """Обрабатывает GET-редирект от Google: проверяет state, обменивает code на токены,
    ставит JWT-куки и редиректит пользователя на фронтенд."""

    base = settings.frontend_redirect_url

    # Google вернул ошибку (пользователь отменил вход и т.д.)
    if error or not code or not state:
        return RedirectResponse(
            url=f"{base}?auth_error=google_cancelled", status_code=status.HTTP_302_FOUND,
        )

    # Проверка CSRF: state из cookie должен совпадать с state из query
    if not google_oauth_state or google_oauth_state != state:
        return RedirectResponse(
            url=f"{base}?auth_error=csrf_mismatch", status_code=status.HTTP_302_FOUND,
        )

    # Бизнес-логика: обмен code → токены, поиск/создание пользователя
    try:
        _, pair = await service.authenticate_via_google(code=code, state=state)
    except AppError as exc:
        return RedirectResponse(
            url=f"{base}?auth_error=google_auth_failed", status_code=status.HTTP_302_FOUND,
        )

    # Успех — редирект на фронтенд с JWT-куками
    response = RedirectResponse(url=base, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="google_oauth_state", path="/", domain=settings.domain)
    set_token_cookies(response, pair.access_token, pair.refresh_token)

    return response