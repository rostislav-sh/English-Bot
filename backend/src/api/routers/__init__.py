"""Пакет роутеров (HTTP-эндпоинты FastAPI)."""

from .auth import router as auth_router
from .user import router as user_router
from .quiz import router as quiz_router