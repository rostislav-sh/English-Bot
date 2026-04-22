"""Точка входа FastAPI-приложения.

Конфигурирует lifespan, глобальный обработчик ошибок,
rate-limiting (slowapi) и подключает роутеры.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.api.exceptions import AppError
from src.logging_config import setup_logging
from src.api.routers import auth_router, user_router
from src.api.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger.info("Приложение запускается…")
    yield
    logger.info("Приложение останавливается…")


app = FastAPI(lifespan=lifespan)

# Подключаем rate-limiter к приложению
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
async def health():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Глобальный обработчик бизнес-ошибок → JSON-ответ."""
    logger.warning("AppError: %s (status=%s, path=%s)", exc, exc.status_code, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


app.include_router(
    auth_router,
    tags=["Авторизация"],
)
app.include_router(
    user_router,
    tags=["Пользователь"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)
