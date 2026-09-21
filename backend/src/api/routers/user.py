from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import verify_csrf_token
from src.api.dependencies import get_current_user_id_from_access_token, get_user_service
from src.application.services import UserService
from src.api.schemas.user import UserProfileOut


router = APIRouter()


@router.get(
    "/me",
    summary="Получить пользователя",
    dependencies=[Depends(verify_csrf_token)],
)
async def get_me(
    user_id: str = Depends(get_current_user_id_from_access_token),
):
    return {"user_id": user_id}


@router.get(
    "/me/profile",
    summary="Профиль пользователя",
    response_model=UserProfileOut,
    dependencies=[Depends(verify_csrf_token)],
)
async def get_my_profile(
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[UserService, Depends(get_user_service)],
):
    """Базовые данные пользователя. Задел на будущее — можно расширить статистикой."""
    user = await service.get_by_id(user_id)
    return UserProfileOut(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at,
    )
