"""Точка входа FastAPI-приложения.

Конфигурирует lifespan, глобальный обработчик ошибок,
rate-limiting (slowapi) и подключает роутеры.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.exception_handlers import register_exception_handlers
from src.logging_config import setup_logging
from src.infrastructure.http.http_client import init_http_client, close_http_client
from src.api.routers import auth_router, user_router, quiz_router
from src.infrastructure.llm.prompt_builder import load_templates
from src.api.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger.info("Приложение запускается…")

    # Инициализация HTTP-клиента
    await init_http_client()

    # ── LLM Шаблоны (Fail-fast) ──
    # Загружаем .md файлы синхронно. Если их нет — приложение упадет до открытия порта.
    test_gen_tpl, rec_tpl = load_templates()
    app.state.tpl_test_gen = test_gen_tpl
    app.state.tpl_recommendation = rec_tpl
    logger.info("Шаблоны LLM успешно загружены в состояние приложения.")

    yield

    await close_http_client()

    # Очистка памяти
    del app.state.tpl_test_gen
    del app.state.tpl_recommendation
    logger.info("Приложение останавливается…")


app = FastAPI(lifespan=lifespan)

# добавляем статусы ошибок к domain/error
register_exception_handlers(app)

# Подключаем rate-limiter к приложению
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
async def health():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}


app.include_router(
    auth_router,
    tags=["Авторизация"],
)
app.include_router(
    user_router,
    tags=["Пользователь"]
)
app.include_router(
    quiz_router,
    tags=["Квизы"],
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