"""Ошибки репозитория (программные баги, не бизнес-логика)."""

from src.domain.exceptions.base import RepositoryError


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
