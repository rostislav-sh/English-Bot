"""Маппинг доменных ошибок в HTTP-ответы."""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    DomainError,
    RepositoryError,
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

logger = logging.getLogger(__name__)

# Domain error → HTTP status
_STATUS_MAP: dict[type[DomainError], int] = {
UserAlreadyExistsError: 409,
    InvalidCredentialsError: 401,
    UserNotFoundError: 404,
    RefreshTokenNotFoundError: 401,
    RefreshTokenExpiredError: 401,
    GoogleIdTokenNotFoundError: 401,
    GoogleAuthorizationCodeError: 401,
    GoogleTokenExchangeTimeoutError: 504,
    GoogleDataReadError: 401,
    GoogleEmailNotVerifiedError: 401,
    InvalidOAuthStateError: 400,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        status = _STATUS_MAP.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"message": exc.message})

    @app.exception_handler(InvalidCredentialsError)
    async def _repo_handler(_: Request, exc: RepositoryError) -> JSONResponse:
        logger.exception("Repository error: %s", exc)
        return JSONResponse(status_code=500, content={"message": "Internal error"})
