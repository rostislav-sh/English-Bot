"""Сервис работы с паролями."""

import logging
from src.infrastructure.auth.security import security
from src.config import settings


logger = logging.getLogger(__name__)


class PasswordService:
    """Хэширование и верификация паролей.

    Чистый сервис — не зависит от БД и UoW.
    """
    def hash(self, password: str) -> str:
        return security.hash_password(password)

    def verify(self, password: str, hashed: str) -> bool:
        return security.verify_password(
            password=password,
            hashed_password=hashed)

    def verify_with_timing_protection(self, password: str) -> bool:
        """Верификация с защитой от User Enumeration (постоянное время ответа)."""
        return security.verify_password(
            password=password,
            hashed_password=settings.password_hash,
        )
