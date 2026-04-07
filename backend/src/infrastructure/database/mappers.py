"""
Маппинг между доменными сущностями и ORM-моделями.
Изолирует домен от деталей хранения.

Соглашение об именах:
    entity_to_model       — создание ORM-модели из доменной сущности (для INSERT)
    model_to_entity       — создание доменной сущности из ORM-модели (для SELECT)
    update_model_from_entity — синхронизация изменений entity → model (для UPDATE)
"""
from src.domain.entities import User, RefreshToken
from .models import UserModel, RefreshTokenModel


# ════════════════════════════════════════
#  USER
# ════════════════════════════════════════

def user_entity_to_model(entity: User) -> UserModel:
    """Новая ORM-модель из доменной сущности. Используется при INSERT.

    Для создания новых записей"""
    return UserModel(
        email=entity.email,
        password_hash=entity.password_hash,
        google_id=entity.google_id,
        auth_provider=entity.auth_provider,
        username=entity.username,
        picture_url=entity.picture_url,
        # id, created_at, updated_at — назначает БД, не передаём
    )


def user_model_to_entity(model: UserModel) -> User:
    """Доменная сущность из ORM-модели. Используется при SELECT.

    Для чтения из БД"""
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        google_id=model.google_id,
        auth_provider=model.auth_provider,
        username=model.username,
        picture_url=model.picture_url,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_user_model_from_entity(model: UserModel, entity: User) -> None:
    """Синхронизирует изменения из entity в ORM-модель. Используется при UPDATE.

    updated_at НЕ трогаем — им управляет SQLAlchemy через onupdate.
    id, created_at НЕ трогаем — они иммутабельны.

    Для обновления записей
    """
    model.email = entity.email
    model.password_hash = entity.password_hash
    model.google_id = entity.google_id
    model.auth_provider = entity.auth_provider
    model.username = entity.username
    model.picture_url = entity.picture_url


# ════════════════════════════════════════
#  REFRESH TOKEN
# ════════════════════════════════════════

def token_entity_to_model(entity: RefreshToken) -> RefreshTokenModel:
    """Новая ORM-модель из доменной сущности. Используется при INSERT.

    Для создания новых записей"""
    return RefreshTokenModel(
        user_id=entity.id,
        token_hash=entity.token_hash,
        expires_at=entity.expires_at,
        revoked=entity.revoked,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def token_model_to_entity(model: RefreshTokenModel) -> RefreshToken:
    """Доменная сущность из ORM-модели. Используется при SELECT.

    Для чтения из БД"""
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        revoked=model.revoked,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_token_model_from_entity(model: RefreshTokenModel, entity: RefreshToken) -> None:
    """Синхронизирует изменения из entity в ORM-модель. Используется при UPDATE.

    Токены почти иммутабельны — единственное, что меняется, это revoked.
    updated_at НЕ трогаем — им управляет SQLAlchemy через onupdate.

    Для обновления записей"""
    model.revoked = entity.revoked
