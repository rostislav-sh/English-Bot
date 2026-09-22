"""Базовые классы доменных ошибок.

Правила:
- Никакого HTTP (status_code живёт в api/exception_handlers.py)
- Никаких импортов из infrastructure/application/api
- Только бизнес-правила и программные ошибки репозитория
"""


class DomainError(Exception):
    """Базовая бизнес-ошибка. Ожидаемая ситуация — обрабатывается в API."""
    message: str = "Бизнес-ошибка."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class RepositoryError(Exception):
    """Базовая ошибка репозитория. Программный баг — логируется, возвращает 500."""
    message: str = "Ошибка репозитория."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
