"""Маршруты аутентификации."""

from fastapi import APIRouter, Response, status
from fastapi.params import Depends

from src.auth.cookies import set_token_cookies
from src.routers.dependencies import get_user_service
from src.routers.schemas.auth import Authentication, RegisterOut, RefreshRequest
from src.schemas.auth import TokenPair
from src.service.auth import AuthService

router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация пользователя",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
        data: Authentication,
        response: Response,
        service: AuthService = Depends(get_user_service),
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
    status_code=status.HTTP_200_OK, )
async def login(
        data: Authentication,
        response: Response,
        service: AuthService = Depends(get_user_service),
) -> TokenPair:
    """Проверяет учётные данные и возвращает пару токенов (access + refresh)."""

    # TODO:
    #  Сейчас каждый вызов login создает новую запись в refresh_tokens.
    #  Если пользователь логинится с телефона 100 раз, в базе будет 100 активных токенов.
    #  При логине имеет смысл удалять истекшие токены,
    #  либо оставлять только N последних активных (например, не больше 5 сессий на юзера).

    _, pair = await service.login(email=data.email, password=data.password)
    set_token_cookies(response, pair.access_token, pair.refresh_token)
    return pair


@router.post(
    # Обновление токенов (и access, и refresh). Здесь refresh - это глагол, который переводиться, как обновить
    "/token/refresh",
    summary="Обновление токенов JWT (access + refresh)",
    response_model=TokenPair,
)
async def refresh(
        data: RefreshRequest,
        response: Response,
        service: AuthService = Depends(get_user_service),
) -> TokenPair:
    """Обновление пары токенов по refresh токену."""
    _, pair = await service.refresh(data.refresh_token)
    set_token_cookies(response, pair.access_token, pair.refresh_token)
    return pair
