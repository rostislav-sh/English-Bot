from sqlalchemy import ForeignKey, Index, Text, Integer, Enum as SQLEnum, CheckConstraint, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tests import TestModel, QuestionModel
    from .users import UserModel

from src.domain import RecommendationStatus
from .base import Base, int_pk, created_at, updated_at


class TestAttemptModel(Base):
    """Попытка прохождения теста конкретным юзером."""
    __tablename__ = "test_attempts"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey("tests.id", ondelete="CASCADE"),
    )
    score: Mapped[int] = mapped_column(Integer)           # кол-во правильных
    total_questions: Mapped[int] = mapped_column(Integer) # всего вопросов на момент попытки

    recommendation_status: Mapped[RecommendationStatus] = mapped_column(
        SQLEnum(RecommendationStatus, name="recommendation_status_enum"),
        default=RecommendationStatus.PENDING,
        nullable=False,
    )
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user: Mapped["UserModel"] = relationship(back_populates="test_attempts")
    test: Mapped["TestModel"] = relationship(back_populates="attempts")
    answers: Mapped[list["AttemptAnswerModel"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Основной индекс для истории юзера и статистики по месяцам
        # Используется в: GET /users/me/stats, GET /users/me/history
        # Фильтр: WHERE user_id = ? ORDER BY created_at DESC
        Index("ix_attempts_user_created", "user_id", "created_at"),

        # Для проверки "этот юзер уже проходил этот тест?"
        # (нужно при выборе теста для переиспользования)
        Index("ix_attempts_user_test", "user_id", "test_id"),

        # Санити-чек: score не может быть больше, чем total
        CheckConstraint(
            "score >= 0 AND score <= total_questions",
            name="ck_attempts_score_valid",
        ),
    )


class AttemptAnswerModel(Base):
    """Ответ юзера на конкретный вопрос в рамках попытки."""
    __tablename__ = "attempt_answers"

    id: Mapped[int_pk]
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("test_attempts.id", ondelete="CASCADE"),
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
    )
    user_answer: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[created_at]

    attempt: Mapped["TestAttemptModel"] = relationship(back_populates="answers")
    question: Mapped["QuestionModel"] = relationship(back_populates="answers")

    __table_args__ = (
        # Один юзер в рамках одной попытки отвечает на каждый вопрос ровно один раз
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )