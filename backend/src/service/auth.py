from src.exceptions import UserAlreadyExistsError
from src.interfaces.unitofwork import IUserUnitOfWork
from src.auth.security import security


class AuthService:
    def __init__(self, uow: IUserUnitOfWork):
        self.uow = uow

    async def register(self, email: str, password: str):
        """Функция для создания пользователя"""
        async with self.uow:
            hash_password = security.hash_password(password)
            user = await self.uow.url_repo.register(email=email, password=hash_password)

            await self.uow.commit()
            return user
