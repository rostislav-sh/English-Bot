from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.services import UserService, PasswordService
from src.api.dependencies.database import get_uow
from .auth import get_current_payload, get_current_payload_without_csrf


async def get_current_user_id_from_access_token(
    payload: Annotated[dict, Depends(get_current_payload)],
) -> int:
    return _user_id_from_payload(payload)


async def get_current_user_id_without_csrf(
    payload: Annotated[dict, Depends(get_current_payload_without_csrf)],
) -> int:
    """user_id без CSRF-проверки — только для read-only SSE-потоков,
    см. get_current_payload_without_csrf."""
    return _user_id_from_payload(payload)


def _user_id_from_payload(payload: dict) -> int:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def get_user_service(uow: Annotated[IUnitOfWork, Depends(get_uow)]) -> UserService:
    """Провайдер UserService (уже полностью реализован — используется как есть)."""
    return UserService(uow=uow, password_service=PasswordService())
