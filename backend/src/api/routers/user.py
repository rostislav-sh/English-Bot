from fastapi import APIRouter, Depends

from src.api.dependencies import verify_csrf_token
from src.api.dependencies import get_current_user_id_from_access_token


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