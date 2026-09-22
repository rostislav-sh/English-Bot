# ---------- Этап 1: сборка зависимостей ----------
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# Не создаём .pyc файлы — в контейнере они бесполезны
ENV PYTHONDONTWRITEBYTECODE=1

# Копируем только файлы зависимостей — для кэширования слоёв Docker.
# Если код изменится, а зависимости нет — Docker пропустит установку
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости отдельно от кода проекта.
# --frozen: строго по uv.lock (воспроизводимость сборки)
# --no-dev: без тестовых библиотек (pytest, black и т.д.)
# --no-install-project: пока не ставим сам проект — только зависимости
RUN uv sync --frozen --no-dev --no-install-project

# Копируем только нужные файлы (не весь контекст)
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

# Повторная синхронизация — uv убедится, что всё на месте
RUN uv sync --frozen --no-dev --no-install-project


# ---------- Этап 2: финальный лёгкий образ ----------
FROM python:3.14-slim-bookworm AS runtime

WORKDIR /app

# PYTHONDONTWRITEBYTECODE=1 — без .pyc мусора
# PYTHONUNBUFFERED=1 — логи мгновенно в docker logs, без буферизации
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Забираем только готовое окружение и код из этапа сборки
COPY --from=builder /app /app

# Добавляем venv в PATH — python и uvicorn доступны напрямую
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Запускаем только сервер; миграции выполняются отдельным сервисом
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]