"""Репозитории для квизов."""

import logging
import random
from datetime import datetime

from sqlalchemy import select, func, and_, not_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from src.application.interfaces.repositories import (
    ITopicRepository, ITestRepository, IAttemptRepository,
)
from src.domain.entities import Topic, Test, TestAttempt, TestStatus, MonthlyStats
from src.infrastructure.database.repositories.base import SQLAlchemyBaseRepository
from src.infrastructure.database.models import (
    TopicModel, TestModel,
    TestAttemptModel,
)
from src.infrastructure.database.mappers.quiz import (
    topic_entity_to_model, topic_model_to_entity,
    test_entity_to_model, test_model_to_entity, update_test_model_from_entity,
    attempt_entity_to_model, attempt_model_to_entity, update_attempt_model_from_entity,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════
#  TOPIC
# ════════════════════════════════════════

class SQLAlchemyTopicRepository(SQLAlchemyBaseRepository[Topic], ITopicRepository):
    def _get_model_class(self) -> type:
        return TopicModel

    def _to_entity(self, model: TopicModel) -> Topic:
        return topic_model_to_entity(model)

    def _to_model(self, entity: Topic) -> TopicModel:
        return topic_entity_to_model(entity)

    def _update_model(self, model: TopicModel, entity: Topic) -> None:
        # Topic иммутабелен — нечего обновлять
        pass

    # ── Специфичные методы ───────────────────────────────────────────

    async def get_by_normalized_name(self, normalized_name: str) -> Topic | None:
        model = await self._session.scalar(select(TopicModel).where(TopicModel.normalized_name == normalized_name))
        return self._track(model) if model else None

    async def get_or_create(self, topic: Topic) -> Topic:
        """
        Атомарный upsert: если тема с таким normalized_name уже есть —
        возвращаем её. Иначе создаём новую.

        Используем PostgreSQL ON CONFLICT, чтобы исключить race condition
        между двумя одновременными запросами.

        Реализация в 2 шага:
            1) INSERT ... ON CONFLICT DO NOTHING RETURNING id
            2) SELECT по normalized_name — чтобы entity была корректно
               зарегистрирована в identity map SQLAlchemy-сессии.
        """
        stmt = (
            pg_insert(TopicModel)
            # Здесь мы используем insert из sqlalchemy.dialects.postgresql, а не стандартный.
            # Стандартный SQL не умеет обрабатывать конфликты.
            .values(
                name=topic.name,
                normalized_name=topic.normalized_name,
                is_custom=topic.is_custom,
            )
            .on_conflict_do_nothing(index_elements=["normalized_name"])
            # Мы говорим базе: "Если во время вставки ты обнаружишь,
            # что нарушается уникальный индекс на колонке normalized_name (то есть такая тема уже есть),
            # ПОЖАЛУЙСТА, НЕ ПАДАЙ С ОШИБКОЙ. Просто тихо отмени эту вставку и сделай вид,
            # что ничего не произошло (DO NOTHING)".
            # Есть еще on_conflict_do_update, если произошла гонка т.е нарушается уникальный индекс,
            # то база обновит данные пользователя.
            .returning(TopicModel.id)
            # Если вставка прошла успешно, верни нам всю созданную строку (чтобы мы узнали сгенерированный базой id и created_at)
        )
        inserted_id = await self._session.execute(stmt)
        existing = await self.get_by_normalized_name(topic.normalized_name)
        if existing is None:
            raise RuntimeError(
                f"get_or_create: race condition unresolved for "
                f"'{topic.normalized_name}'"
            )

        if inserted_id is not None:
            logger.debug("get_or_create: created topic '%s'", topic.normalized_name)
        else:
            logger.debug("get_or_create: reused topic '%s'", topic.normalized_name)

        return existing

    async def list_system_topics(self) -> list[Topic]:
        models = await self._session.scalars(
            select(TopicModel)
            .where(TopicModel.is_custom.is_(False))
            .order_by(TopicModel.name)
        )
        return [self._track(m) for m in models]


# ════════════════════════════════════════
#  TEST
# ════════════════════════════════════════

class SQLAlchemyTestRepository(SQLAlchemyBaseRepository[Test], ITestRepository):
    def _get_model_class(self) -> type:
        return TestModel

    def _to_entity(self, model: TestModel) -> Test:
        # По умолчанию без вопросов — для специфичных методов
        # явно используем test_model_to_entity(model, with_questions=True)
        return test_model_to_entity(model, with_questions=False)

    def _to_model(self, entity: Test) -> TestModel:
        return test_entity_to_model(entity)

    def _update_model(self, model: TestModel, entity: Test) -> None:
        update_test_model_from_entity(model, entity)

    # ── Специфичные методы ───────────────────────────────────────────

    async def get_with_questions(self, test_id: int) -> Test | None:
        """Загружает тест вместе с вопросами (eager-load)."""
        model = await self._session.scalar(
            select(TestModel)
            .where(TestModel.id == test_id)
            .options(selectinload(TestModel.questions))
        )
        if model is None:
            return None

        # Кастомный маппинг с questions, минуя _to_entity
        entity = test_model_to_entity(model, with_questions=True)
        # Регистрируем в identity map вручную, т.к. _track() использует _to_entity()
        self._identity_map[id(entity)] = (entity, model)
        return entity

    async def find_reusable_for_user(self, topic_id: int, user_id: int) -> Test | None:
        """
        Ищет готовый тест по теме, который юзер ещё НЕ проходил.

        Алгоритм:
          1) Берём ДО _REUSABLE_POOL_SIZE свежих готовых тестов
             (ORDER BY id DESC использует первичный индекс — быстро).
          2) Случайно выбираем один на уровне Python.

        Почему не ORDER BY RANDOM():
          Полная сортировка случайных значений по всему набору =
          O(N log N) на каждый запрос. На 10k+ тестов — заметные задержки.

        Почему не просто LIMIT N без ORDER BY:
          Без ORDER BY порядок не гарантирован, на практике вернутся
          физически первые строки (самые старые) — нет разнообразия.
        """
        # Подзапрос: тесты, которые юзер уже прошёл
        passed_test_subq = (
            select(TestAttemptModel.test_id)
            .where(TestAttemptModel.user_id == user_id)
        )

        candidates = (
            await self._session.scalars(
                select(TestModel)
                .where(
                    and_(
                        TestModel.topic_id == topic_id,
                        TestModel.status == TestStatus.READY,
                        not_(TestModel.id.in_(passed_test_subq)),
                    )
                )
                .options(selectinload(TestModel.questions))
                .order_by(TestModel.id.desc())
                # TODO убрать захардкорженные данные, например, вынести в config
                .limit(100) # плохо хардкорить
            )
        ).all() # собирает ответ от асинхронного генератора Алхимии в обычный питоновский список

        if not candidates:
            return None

        model = random.choice(candidates)
        entity = test_model_to_entity(model, with_questions=True)
        self._identity_map[id(entity)] = (entity, model)
        return entity


# ════════════════════════════════════════
#  TEST ATTEMPT
# ════════════════════════════════════════

class SQLAlchemyAttemptRepository(SQLAlchemyBaseRepository[TestAttempt], IAttemptRepository):
    def _get_model_class(self) -> type:
        return TestAttemptModel

    def _to_entity(self, model: TestAttemptModel) -> TestAttempt:
        return attempt_model_to_entity(model, with_answers=False)

    def _to_model(self, entity: TestAttempt) -> TestAttemptModel:
        return attempt_entity_to_model(entity)

    def _update_model(self, model: TestAttemptModel, entity: TestAttempt) -> None:
        update_attempt_model_from_entity(model, entity)

    # ── Специфичные методы ───────────────────────────────────────────

    async def get_with_answer(self, attempt_id: int) -> TestAttempt | None:
        """Загружает попытку вместе с ответами на каждый вопрос."""
        model = await self._session.scalar(
            select(TestAttemptModel)
            .where(TestAttemptModel.id == attempt_id)
            .options(selectinload(TestAttemptModel.answers))
        )
        if model is None:
            return None

        entity = attempt_model_to_entity(model, with_answers=True)
        self._identity_map[id(entity)] = (entity, model)
        return entity

    async def list_by_user(self, user_id: int, *, limit: int = 20, offset: int = 0) -> list[TestAttempt | None]:
        """История попыток. Без ответов — для списка достаточно."""
        models = await self._session.scalars(
            select(TestAttemptModel)
            .where(TestAttemptModel.user_id == user_id)
            .order_by(TestAttemptModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._track(m) for m in models]

    async def get_monthly_stats(self, user_id: int, since: datetime) -> list[MonthlyStats]:
        """
        Агрегированная статистика юзера по месяцам.

        DATE_TRUNC('month', created_at) — нормализует timestamp до начала месяца,
        группируем по нему и считаем агрегаты.
        """
        # Обрезает все до месяца. Даем имя "month"
        month_col = func.date_trunc('month', TestAttemptModel.created_at).label("month")

        stmt = (
            # Передаем не модели целиком, а конкретные вычисляемые колонки.
            # Алхимия вернет нам не объекты-модели, а простые строки с цифрами (кортежи)
            select(
                # месяц
                month_col,
                # количество попыток за месяц
                func.count(TestAttemptModel.id).label("attempt_count"),
                # суммируем правильные ответы, coalesce нужен, чтобы вместо NULL получить 0
                func.coalesce(func.sum(TestAttemptModel.score), 0).label("total_score"),
                # суммируем общее количество вопросов
                func.coalesce(func.sum(TestAttemptModel.total_questions), 0).label("total_questions"),
            )
            .where(
                and_(
                    TestAttemptModel.user_id == user_id,
                    TestAttemptModel.created_at >= since,
                )
            )
            # группируем по месяцу, теперь sum и count работают только для него (месяца)
            .group_by(month_col)
            .order_by(month_col.desc())
        )

        result = await self._session.execute(stmt)
        return [
            MonthlyStats(
                month=row.month,
                attempts_count=row.attempt_count,
                total_score=row.total_score,
                total_questions=row.total_questions,
            )
            for row in result
        ]

    async def has_user_passed_test(self, user_id: int, test_id: int) -> bool:
        """
        Проверяет, проходил ли юзер этот тест.
        Не загружает запись в память — только EXISTS.
        Использует индекс ix_attempts_user_test.
        """
        stmt = (
            select( # подготавливает запрос для бд
                select(TestAttemptModel.id) # ищем сущность
                .where(
                    and_(
                        TestAttemptModel.user_id == user_id,
                        TestAttemptModel.test_id == test_id,
                    )
                )
                .exists() # если найдена, хотя бы одна строка возвращаем true
            )
        )
        return bool(await self._session.scalar(stmt))
