from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.enums import QuestionType, TestStatus, RecommendationStatus


@dataclass
class Topic:
    """Тема теста (системная или пользовательская)."""

    # ── Обязательные при создании ──
    name: str
    normalized_name: str

    # ── С дефолтами ──
    is_custom: bool = False

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None


@dataclass
class Question:
    """Вопрос в тесте."""

    # ── Обязательные при создании ──
    test_id: int
    text: str
    options: list[Any]
    correct_answer: str

    # ── С дефолтами ──
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None

    def check_answer(self, user_answer: str) -> bool:
        """Проверка ответа юзера. Доменная логика — место ей здесь."""
        return user_answer.strip() == self.correct_answer.strip()


@dataclass
class Test:
    """Сгенерированный тест."""

    # ── Обязательные при создании ──
    topic_id: int

    # ── С дефолтами ──
    status: TestStatus = TestStatus.GENERATING
    generation_task_id: "str | None" = None
    questions: list[Question] = field(default_factory=list)

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None
    updated_at: "datetime | None" = None

    @property
    def is_ready(self) -> bool:
        return self.status == TestStatus.READY


@dataclass
class AttemptAnswer:
    """Ответ юзера на конкретный вопрос."""

    # ── Обязательные при создании ──
    question_id: int
    user_answer: str
    is_correct: bool

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    attempt_id: "int | None" = None  # проставится при сохранении вместе с attempt
    created_at: "datetime | None" = None


@dataclass
class TestAttempt:
    """Попытка прохождения теста."""

    # ── Обязательные при создании ──
    user_id: int
    test_id: int
    score: int
    total_questions: int
    answers: list[AttemptAnswer] = field(default_factory=list)

    # ── С дефолтами ──
    recommendation_status: RecommendationStatus = RecommendationStatus.PENDING
    ai_recommendation: "str | None" = None

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None
    updated_at: "datetime | None" = None

    @property
    def percentage(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return round(self.score / self.total_questions * 100, 1)

    @property
    def is_perfect(self) -> bool:
        return self.score == self.total_questions


@dataclass(slots=True)
class MonthlyStats:
    """Агрегированная статистика юзера за один месяц."""
    month: datetime           # начало месяца (через DATE_TRUNC)
    attempts_count: int       # сколько тестов прошёл
    total_score: int          # суммарно правильных ответов
    total_questions: int      # суммарно вопросов (для расчёта accuracy)

    @property
    def accuracy(self) -> float:
        """Точность за месяц в процентах."""
        if self.total_questions == 0:
            return 0.0
        return round(self.total_score / self.total_questions * 100, 1)
