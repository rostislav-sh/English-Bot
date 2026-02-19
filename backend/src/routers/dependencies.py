"""FastAPI-зависимости (Depends)."""

from fastapi.params import Depends

from src.database.unitofwork import UserUnitOfWork
from src.interfaces.unitofwork import IUserUnitOfWork
from src.service.auth import AuthService


async def get_uow() -> IUserUnitOfWork:
    """Фабрика Unit of Work для Dependency Injection."""
    return UserUnitOfWork()


async def get_user_service(uow: IUserUnitOfWork = Depends(get_uow)) -> AuthService:
    """Фабрика сервиса аутентификации."""
    return AuthService(uow=uow)
