"""Бизнес-ошибки квизов: темы, тесты, попытки прохождения."""

from src.domain.exceptions.base import DomainError


class TopicNotFoundError(DomainError):
    """Тема не найдена."""
    message = "Тема не найдена."


class TestNotFoundError(DomainError):
    """Тест не найден."""
    message = "Тест не найден."


class TestNotReadyError(DomainError):
    """Тест ещё генерируется (или генерация упала) — вопросы недоступны."""
    message = "Тест ещё не готов."


class TestGenerationFailedError(DomainError):
    """Генерация теста через LLM завершилась ошибкой."""
    message = "Не удалось сгенерировать тест."


class AttemptNotFoundError(DomainError):
    """Попытка прохождения теста не найдена."""
    message = "Попытка прохождения не найдена."


class AnswersMismatchError(DomainError):
    """Набор ответов в сабмите не совпадает с вопросами теста."""
    message = "Ответы не соответствуют вопросам теста."
