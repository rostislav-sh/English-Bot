class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""


class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""
