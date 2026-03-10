"""Иерархия бизнес-ошибок приложения.

Все ошибки наследуются от ``AppError``, содержат ``message`` и ``status_code``.
Глобальный обработчик в ``main.py`` конвертирует их в JSON-ответ.
"""


class AppError(Exception):
    """Базовая ошибка приложения. От нее наследуются все остальные."""

    message: str = "Произошла непредвиденная ошибка."
    status_code: int = 400

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


# ── Пользователь / авторизация ──────────────────────────────────────

class UserAlreadyExistsError(AppError):
    """Пользователь уже существует."""
    message = "Пользователь с таким email уже существует."
    status_code = 409


class InvalidCredentialsError(AppError):
    """Неверный логин или пароль."""
    message = "Неверный email или пароль."
    status_code = 401


class UserNotFoundError(AppError):
    """Пользователь не найден."""
    message = "Пользователь не найден."
    status_code = 401


# ── Refresh-токены ───────────────────────────────────────────────────

class RefreshTokenNotFoundError(AppError):
    """Refresh токен не найден или отозван."""
    message = "Refresh токен не найден или отозван."
    status_code = 401


class RefreshTokenLifetimeExpiredError(AppError):
    """Время жизни refresh токена истекло."""
    message = "Время жизни refresh токена истекло."
    status_code = 401


# ── Google OAuth ─────────────────────────────────────────────────────

class GoogleIdTokenNotFoundError(AppError):
    """Google не вернул id_token в ответе на обмен кода."""
    message = "Google не вернул id_token в ответе"
    status_code = 401


class GoogleExpiredAuthorizationCodeError(AppError):
    """Код авторизации Google невалиден или истёк."""
    message = "Неверный или просроченный код авторизации Google"
    status_code = 401


class GoogleTokenExchangeTimeoutError(AppError):
    """Тайм-аут при обмене кода авторизации на токен у Google."""
    message = "Тайм-аут при обращении к Google для обмена кода"
    status_code = 504


class GoogleDataReadError(AppError):
    """Не удалось прочитать / валидировать данные из Google ID-токена."""
    message = "Ошибка чтения данных Google"
    status_code = 401

    def __init__(self, error: str | None = None) -> None:
        super().__init__(f"{self.message}: {error}")


class GoogleEmailNotFoundError(AppError):
    """Email в аккаунте Google не подтверждён."""
    message = "Email в аккаунте Google не подтвержден"
    status_code = 401


class InvalidOAuthStateError(AppError):
    """OAuth state не найден или истёк."""
    message = "Недействительный или истёкший OAuth state."
    status_code = 400
