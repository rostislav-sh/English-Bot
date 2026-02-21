class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""

    message: str = "Произошла непредвиденная ошибка."
    status_code: int = 400

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""
    message = "Пользователь с таким email уже существует."
    status_code = 409


class InvalidCredentialsError(AppError):
    """Неверный логин или пароль."""
    message = "Неверный email или пароль."
    status_code = 401


class RefreshTokenNotFoundError(AppError):
    """Refresh токен не найден или отозван."""
    message = "Refresh токен не найден или отозван."
    status_code = 401


class RefreshTokenLifetimeExpiredError(AppError):
    """Время жизни refresh токена истекло."""
    message = "Время жизни refresh токена истекло."
    status_code = 401


class UserNotFoundError(AppError):
    """Пользователь не найден."""
    message = "Пользователь не найден."
    status_code = 401