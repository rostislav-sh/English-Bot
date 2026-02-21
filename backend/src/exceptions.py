class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""

    message: str = "Произошла непредвиденная ошибка."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""
    message = "Пользователь с таким email уже существует."


class InvalidCredentialsError(AppError):
    """Неверный логин или пароль."""
    message = "Неверный email или пароль."


class RefreshTokenNotFoundError(AppError):
    """Refresh токен не найден или отозван."""
    message = "Refresh токен не найден или отозван."


class RefreshTokenLifetimeExpiredError(AppError):
    """Время жизни refresh токена истекло."""
    message = "Время жизни refresh токена истекло."


class UserNotFoundError(AppError):
    """Пользователь не найден."""
    message = "Пользователь не найден."