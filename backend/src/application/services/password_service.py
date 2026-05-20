"""Сервис работы с паролями."""

import logging
import asyncio

from src.infrastructure.auth.security import security
from src.config import settings


logger = logging.getLogger(__name__)


class PasswordService:
    """Хэширование и верификация паролей.

    Чистый сервис — не зависит от БД и UoW.

    Так как алгоритмы хэширования (bcrypt/argon2) сильно нагружают CPU (CPU-bound),
    мы выносим их в отдельный пул потоков через asyncio.to_thread,
    чтобы не блокировать главный Event Loop приложения (FastAPI).
    Известно, что в Python из-за GIL потоки не могут выполнять математику параллельно. Почему тогда to_thread помогает?
    Секрет в том, что библиотеки вроде bcrypt или argon2 написаны на C/Rust.
    Когда они начинают вычислять хеш, они говорят питону: "Я пошел считать в си-шный код, GIL мне не нужен, я его отпускаю".
    Поэтому для хеширования паролей потоки в Python работают по-настоящему параллельно и не мешают друг другу!
    """
    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(security.hash_password(password))

    async def verify(self, password: str, hashed: str) -> bool:
        return await asyncio.to_thread(
            security.verify_password(
                password=password,
                hashed_password=hashed,
            )
        )

    async def verify_with_timing_protection(self, password: str) -> bool:
        """Верификация с защитой от User Enumeration (постоянное время ответа)."""
        return await asyncio.to_thread(
            security.verify_password(
                password=password,
                hashed_password=settings.fake_password_hash,
            )
        )
