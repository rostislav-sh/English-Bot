"""FastAPI-зависимости (Depends)."""
"""FastAPI-зависимости (Depends).

Фабрики для Unit of Work и сервиса аутентификации,
используемые через Dependency Injection в роутерах.
"""


from fastapi.params import Depends

from src.database.unitofwork import UserUnitOfWork
from src.interfaces import AuthServiceProtocol
from src.interfaces.unitofwork import IUserUnitOfWork
from src.redis.auth_state import RedisAuthState
from src.redis.config_redis import redis_client
from src.service.auth import AuthService


async def get_uow() -> IUserUnitOfWork:
    """Фабрика Unit of Work для Dependency Injection."""
    return UserUnitOfWork()


async def get_user_service(uow: IUserUnitOfWork = Depends(get_uow)) -> AuthServiceProtocol:
    """Фабрика сервиса аутентификации с UoW и Redis."""
    redis = RedisAuthState(redis=redis_client)
    return AuthService(uow=uow, redis=redis)
