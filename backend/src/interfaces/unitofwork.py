from abc import ABC, abstractmethod

from src.interfaces.repository import IUserRepository


class IUserUnitOfWork(ABC):

    user_repo: IUserRepository

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    @abstractmethod
    async def commit(self):
        ...

    @abstractmethod
    async def rollback(self):
        ...
