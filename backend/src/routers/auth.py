"""Маршруты аутентификации."""

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.params import Depends

from src.auth.cookies import set_token_cookies
from src.routers.dependencies import get_user_service
from src.exceptions import UserAlreadyExistsError, InvalidCredentialsError, AppError
from src.routers.schemas.auth import Authentication, UserOut
from src.schemas.auth import TokenPair
from src.service.auth import AuthService

router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация пользователя",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
        data: Authentication,
        service: AuthService = Depends(get_user_service),
):
    """Регистрация нового пользователя."""
    try:
        user = await service.register(email=data.email, password=data.password)
        return UserOut.model_validate(user, from_attributes=True)
    except UserAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AppError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post(
    "/login",
    summary="Вход через JWT (access + refresh)",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,)
async def login(
        data: Authentication,
        response: Response,
        service: AuthService = Depends(get_user_service),
) -> TokenPair:
    """Проверяет учётные данные и возвращает пару токенов (access + refresh).

    Raises:
        HTTPException 401: Неверный email или пароль.
    """
    try:
        access_token, refresh_token = await service.login(email=data.email, password=data.password)
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error), )
    except AppError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    set_token_cookies(response, access_token, refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
