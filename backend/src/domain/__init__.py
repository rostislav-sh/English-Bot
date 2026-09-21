"""
Domain Layer (Слой бизнес-логики)

Содержит:
- Entities (сущности): дата-классы без привязки к инфраструктуре
- Enums (перечисления): типы и статусы
- Exceptions (исключения): бизнес-ошибки
"""

# Enums
from src.domain.enums import (
    AuthProvider,
    QuestionType,
    TestStatus,
    RecommendationStatus,
)

# Entities / Dataclasses
from src.domain.entities import (
    User,
    RefreshToken,
)

# Exceptions (Основные)
from src.domain.exceptions import (
    DomainError,
    RepositoryError,
)

__all__ = [
    # Enums
    "QuestionType",
    "TestStatus",
    "RecommendationStatus",
    
    # Entities
    "AuthProvider",
    "User",
    "RefreshToken",
    
    # Exceptions
    "DomainError",
    "RepositoryError",
]
