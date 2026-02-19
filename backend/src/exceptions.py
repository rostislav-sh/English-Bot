class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""


class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""


class InvalidCredentialsError(AppError):
    """Неверный логин или пароль"""
