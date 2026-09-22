"""Бизнес-ошибки аутентификации: пользователь, refresh-токены, Google OAuth."""

from src.domain.exceptions.base import DomainError


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
#  Google OAuth
# ════════════════════════════════════════════════════════════════════

class GoogleIdTokenNotFoundError(DomainError):
    message = "Google не вернул id_token в ответе."


class GoogleAuthorizationCodeError(DomainError):
    message = "Неверный или просроченный код авторизации Google."


class GoogleTokenExchangeTimeoutError(DomainError):
    message = "Тайм-аут при обращении к Google."


class GoogleDataReadError(DomainError):
    message = "Ошибка чтения данных Google."


class GoogleEmailNotVerifiedError(DomainError):
    message = "Email в аккаунте Google не подтверждён."


class InvalidOAuthStateError(DomainError):
    message = "Недействительный или истёкший OAuth state."
