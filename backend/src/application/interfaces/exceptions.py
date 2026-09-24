"""Ошибки контракта репозитория.

Эти ошибки — часть интерфейса репозитория: их обязан ловить слой
application. Они НЕ наследуются от RepositoryError, потому что
RepositoryError означает «программный баг» и не ловится.
"""


class RepositoryIntegrityError(Exception):
    """
    Базовая ошибка нарушения целостности БД при записи.

    Бросается реализацией репозитория, когда Postgres отклонил INSERT/UPDATE
    из-за нарушенного ограничения. Конкретный подкласс говорит, какое именно —
    сервис обязан перехватить и сконвертировать в бизнес-ошибку.
    """
    message: str = "Нарушено ограничение целостности БД."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class UniqueViolationError(RepositoryIntegrityError):
    """Нарушено уникальное ограничение (email, normalized_name и т.п.) — дубликат."""
    message = "Нарушено уникальное ограничение."


class ForeignKeyViolationError(RepositoryIntegrityError):
    """Ссылка на строку, которой не существует в связанной таблице."""
    message = "Нарушено ограничение внешнего ключа: связанная запись не найдена."


class CheckViolationError(RepositoryIntegrityError):
    """Нарушено CHECK-ограничение (например, score <= total_questions)."""
    message = "Нарушено ограничение целостности данных."
