"""ORM-модели для системы тестов."""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .attempts import AttemptAnswerModel, TestAttemptModel

from sqlalchemy import ForeignKey, Enum as SQLEnum, String, Boolean, UniqueConstraint, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, int_pk, created_at, updated_at
from src.domain.enums import (
    QuestionType, TestStatus,
)


class TopicModel(Base):
    """Тема теста (системная или пользовательская)."""
    __tablename__ = "topics"

    id: Mapped[int_pk]
    # Отображаемое имя, как его увидит юзер ("Present Simple", "IT Slang")
    name: Mapped[str] = mapped_column(String(150))
    # Нормализованное имя для поиска/дедупликации: lower().strip()
    # Именно по нему проверяем "а нет ли уже такой темы?"
    normalized_name: Mapped[str] = mapped_column(String(150))
    # Системная тема (из каталога) или созданная юзером через Custom input
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[created_at]

    tests: Mapped[list["TestModel"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Уникальность по нормализованному имени — чтобы "IT Slang", "it slang " и "it  slang" не плодили дубли
        UniqueConstraint("normalized_name", name="uq_topics_normalized_name"),
    )


class TestModel(Base):
    """Сгенерированный тест (переиспользуется между юзерами)."""
    __tablename__ = "tests"

    id: Mapped[int_pk]
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
    )
    status: Mapped[TestStatus] = mapped_column(
        SQLEnum(TestStatus, name="test_status_enum"),
        default=TestStatus.GENERATING,
        nullable=False,
    )
    # Celery task id — чтобы фронт мог опрашивать статус генерации
    generation_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    topic: Mapped["TopicModel"] = relationship(back_populates="tests")
    questions: Mapped[list["QuestionModel"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="QuestionModel.id",
    )
    attempts: Mapped[list["TestAttemptModel"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Используется при поиске "есть ли готовый тест по этой теме"
        # Фильтр: WHERE topic_id = ? AND status = 'ready'
        Index("ix_tests_topic_status", "topic_id", "status"),
    )


class QuestionModel(Base):
    """Вопрос в тесте."""
    __tablename__ = "questions"

    id: Mapped[int_pk]
    test_id: Mapped[int] = mapped_column(
        ForeignKey("tests.id", ondelete="CASCADE"),
        index=True,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, name="question_type_enum"),
        default=QuestionType.MULTIPLE_CHOICE,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text)
    # Для MCQ — массив строк-вариантов. Для будущих типов — структура может отличаться,
    # поэтому JSONB даёт гибкость без миграций.
    # Пример: ["was going", "went", "had gone", "goes"]
    options: Mapped[list[Any]] = mapped_column(JSONB)
    # Для MCQ — строка, точно совпадающая с одним из options.
    # Храним как Text, чтобы под будущие типы не переделывать схему.
    correct_answer: Mapped[str] = mapped_column(Text)

    created_at: Mapped[created_at]

    test: Mapped["TestModel"] = relationship(back_populates="questions")
    answers: Mapped[list["AttemptAnswerModel"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )