from enum import Enum


class AuthProvider(str, Enum):
    """Способ аутентификации пользователя."""
    LOCAL = "local"  # Регистрация через email + пароль
    GOOGLE = "google"  # Вход только через Google
    HYBRID = "hybrid"  # И пароль, и Google привязаны


class QuestionType(str, Enum):
    """Тип вопроса в тесте. Пока только MCQ, но заложено под расширение."""
    MULTIPLE_CHOICE = "multiple_choice"
    # TEXT_INPUT = "text_input"        # ввод ответа текстом
    # MATCHING = "matching"            # сопоставление пар


class TestStatus(str, Enum):
    """Статус генерации теста."""
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class RecommendationStatus(str, Enum):
    """Статус генерации рекомендаций ИИ по попытке."""
    NOT_NEEDED = "not_needed"   # все ответы верные — рекомендация не нужна
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
