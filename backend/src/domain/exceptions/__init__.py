"""Бизнес-ошибки домена.

Пакет разбит по доменам (auth/repository/quiz), но всё
ре-экспортируется отсюда — импортёры продолжают писать
`from src.domain.exceptions import X`.
"""

from src.domain.exceptions.base import DomainError, RepositoryError
from src.domain.exceptions.auth import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
    RefreshTokenNotFoundError,
    RefreshTokenExpiredError,
    GoogleIdTokenNotFoundError,
    GoogleAuthorizationCodeError,
    GoogleTokenExchangeTimeoutError,
    GoogleDataReadError,
    GoogleEmailNotVerifiedError,
    InvalidOAuthStateError,
)
from src.domain.exceptions.repository import EntityNotFoundError, MissingEntityIdError
from src.domain.exceptions.quiz import (
    TopicNotFoundError,
    TestNotFoundError,
    TestNotReadyError,
    TestGenerationFailedError,
    AttemptNotFoundError,
    AnswersMismatchError,
)

__all__ = [
    # Базовые
    "DomainError",
    "RepositoryError",
    # Auth
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "RefreshTokenNotFoundError",
    "RefreshTokenExpiredError",
    "GoogleIdTokenNotFoundError",
    "GoogleAuthorizationCodeError",
    "GoogleTokenExchangeTimeoutError",
    "GoogleDataReadError",
    "GoogleEmailNotVerifiedError",
    "InvalidOAuthStateError",
    # Repository
    "EntityNotFoundError",
    "MissingEntityIdError",
    # Quiz
    "TopicNotFoundError",
    "TestNotFoundError",
    "TestNotReadyError",
    "TestGenerationFailedError",
    "AttemptNotFoundError",
    "AnswersMismatchError",
]
