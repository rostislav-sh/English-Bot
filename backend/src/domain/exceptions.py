"""Бизнес-ошибки домена.

Правила:
- Никакого HTTP (status_code живёт в api/exception_handlers.py)
- Никаких импортов из infrastructure/application/api
- Только бизнес-правила и программные ошибки репозитория
"""


# ════════════════════════════════════════════════════════════════════
#  Базовые классы
# ════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════
#  Пользователь
# ════════════════════════════════════════════════════════════════════

class UserAlreadyExistsError(DomainError):
    """Пользователь с таким email уже существует."""
    message = "Пользователь с таким email уже существует."


class InvalidCredentialsError(DomainError):
    """Неверный email или пароль."""
    message = "Неверный email или пароль."


class UserNotFoundError(DomainError):
    """Пользователь не найден."""
    message = "Пользователь не найден."


# ════════════════════════════════════════════════════════════════════
#  Refresh-токены
# ════════════════════════════════════════════════════════════════════

class RefreshTokenNotFoundError(DomainError):
    """Refresh-токен не найден или отозван."""
    message = "Refresh-токен не найден или отозван."


class RefreshTokenExpiredError(DomainError):
    """Refresh-токен истёк."""
    message = "Refresh-токен истёк."


# ════════════════════════════════════════════════════════════════════
#  Ошибки репозитория (программные баги, не бизнес-логика)
# ════════════════════════════════════════════════════════════════════

class EntityNotFoundError(RepositoryError):
    """
    ORM-модель не найдена в БД при операции update/delete.
    Означает рассинхронизацию между identity map и БД — это баг.
    """
    def __init__(self, entity_name: str, lookup_value: object) -> None:
        super().__init__(f"{entity_name} не найден(а) в БД: {lookup_value!r}")
        self.entity_name = entity_name
        self.lookup_value = lookup_value


class MissingEntityIdError(RepositoryError):
    """
    Сущность без id передана в update/delete.
    Означает ошибку в коде сервиса — это баг.
    """
    def __init__(self, entity: object, operation: str) -> None:
        super().__init__(
            f"Операция '{operation}' невозможна: "
            f"сущность {type(entity).__name__!r} не имеет id. "
            f"Значение: {entity!r}"
        )
        self.entity = entity
        self.operation = operation
