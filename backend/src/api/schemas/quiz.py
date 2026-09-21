"""Pydantic-схемы для роутеров квизов (transport layer)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import QuestionType, TestStatus, RecommendationStatus


# ── Темы ──────────────────────────────────────────────────────────────

class TopicOut(BaseModel):
    """Тема теста."""
    id: int
    name: str
    is_custom: bool

# ── Запрос и получение теста ────────────────────────────────────────────

class RequestTestIn(BaseModel):
    """Запрос на получение теста по теме (создание или переиспользование)."""
    topic_name: str = Field(min_length=1, max_length=150)


class QuestionOut(BaseModel):
    """Вопрос теста. Без correct_answer — ответ не должен утекать на фронт."""
    id: int
    text: str
    options: list[Any]
    question_type: QuestionType


class TestOut(BaseModel):
    """Тест. `questions` пуст, пока status=GENERATING."""
    id: int
    topic_id: int
    status: TestStatus
    questions: list[QuestionOut]


# ── Прохождение теста ────────────────────────────────────────────────

class AnswerIn(BaseModel):
    """Ответ пользователя на один вопрос."""
    question_id: int
    answer: str


class SubmitAnswersIn(BaseModel):
    """Все ответы пользователя отправляются одним запросом."""
    answers: list[AnswerIn] = Field(min_length=1)


class AnswerResultOut(BaseModel):
    """Результат проверки одного ответа."""
    question_id: int
    user_answer: str
    correct_answer: str
    is_correct: bool


class AttemptOut(BaseModel):
    """Результат попытки прохождения теста."""
    id: int
    test_id: int
    score: int
    total_questions: int
    percentage: float
    is_perfect: bool
    recommendation_status: RecommendationStatus
    ai_recommendation: str | None
    answers: list[AnswerResultOut]


class AttemptHistoryItemOut(BaseModel):
    """Элемент истории попыток (без детализации по ответам)."""
    id: int
    test_id: int
    score: int
    total_questions: int
    percentage: float
    created_at: datetime | None


class MonthlyStatOut(BaseModel):
    """Агрегированная статистика пользователя за месяц."""
    month: datetime
    attempts_count: int
    total_score: int
    total_questions: int
    accuracy: float
