class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""

    def __init__(self, message: str = "Произошла непредвиденная ошибка.") -> None:
        super().__init__(message)

class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""

    def __init__(self, message: str = "Пользователь с таким email уже существует"):
        super().__init__(message)


class InvalidCredentialsError(AppError):
    """Неверный логин или пароль"""

    def __init__(self, message: str = "Неверный email или пароль"):
        super().__init__(message)
