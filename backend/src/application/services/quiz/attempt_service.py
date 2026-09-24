"""Сервис прохождения тестов: проверка ответов и сохранение попытки."""

import logging
from datetime import datetime, timezone

from src.application.interfaces.unitofwork import IUnitOfWork
from src.domain.entities import TestAttempt, AttemptAnswer, MonthlyStats
from src.domain.enums import TestStatus, RecommendationStatus
from src.domain.exceptions import (
    TestNotFoundError,
    TestNotReadyError,
    TestGenerationFailedError,
    AttemptNotFoundError,
    AnswersMismatchError,
)

logger = logging.getLogger(__name__)


class AttemptService:
    """
    submit_answers — проверяет ответы доменной логикой (Question.check_answer),
    сохраняет попытку целиком (Attempt+Answers одной транзакцией) и, если
    есть ошибки, запускает Celery-таску генерации рекомендации.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def submit_answers(
            self, user_id: int, test_id: int, answers: list[tuple[int, str]],
    ) -> TestAttempt:
        test = await self._uow.tests.get_with_questions(test_id)
        if test is None:
            raise TestNotFoundError()
        if test.status == TestStatus.FAILED:
            raise TestGenerationFailedError()
        if test.status != TestStatus.READY:
            raise TestNotReadyError()

        # {1: Question(id=1, text='2 + 2 = ?', correct_answer='4'),
        #  2: Question(id=2, text='Столица Франции?', correct_answer='Париж'),
        #  3: Question(id=3, text='Цвет неба?', correct_answer='Синий')}
        questions_by_id = {q.id: q for q in test.questions}
        # {1, 2, 3} != {1: Question(...), 2: Question(...), 3: Question(...)}
        if {question_id for question_id, _ in answers} != set(questions_by_id):
            raise AnswersMismatchError()

        attempt_answers = []
        score = 0
        for question_id, user_answer in answers:
            # получаем модель Question
            question = questions_by_id[question_id]
            is_correct = question.check_answer(user_answer)
            score += int(is_correct)
            attempt_answers.append(
                AttemptAnswer(
                    question_id=question_id,
                    user_answer=user_answer,
                    is_correct=is_correct,
                )
            )

        # проверяем количество правильных ответов между списком всех ответов
        has_mistakes = score < len(attempt_answers)
        attempt = TestAttempt(
            user_id=user_id,
            test_id=test_id,
            score=score,
            total_questions=len(attempt_answers),
            answers=attempt_answers,
            recommendation_status=(
                # если has_mistakes = True -> создаем рекомендацию
                RecommendationStatus.PENDING if has_mistakes else RecommendationStatus.NOT_NEEDED
            ),
        )
        created = await self._uow.attempts.add(attempt)
        # Коммитим сразу: попытка должна быть видна воркеру Celery до того,
        # как мы задиспатчим таску рекомендации (см. TestService.request_test).
        await self._uow.commit()

        if has_mistakes:
            # Локальный импорт — та же причина, что и в TestService.request_test:
            # application-слой не должен тянуть Celery на этапе импорта модуля.
            from src.infrastructure.tasks.jobs.recommendation import generate_recommendation_task
            generate_recommendation_task.delay(created.id)
            logger.info(
                "AttemptService: запущена генерация рекомендации attempt_id=%s", created.id,
            )

        logger.info(
            "AttemptService: попытка id=%s user_id=%s score=%s/%s",
            created.id, user_id, score, len(attempt_answers),
        )
        return created

    async def get_attempt(self, user_id: int, attempt_id: int) -> TestAttempt:
        attempt = await self._uow.attempts.get_with_answer(attempt_id)
        # есть ли тест, а также тот ли юзер
        if attempt is None or attempt.user_id != user_id:
            raise AttemptNotFoundError()
        return attempt

    async def list_history(self, user_id: int, *, limit: int, offset: int) -> list[TestAttempt]:
        # * нужна, чтобы передавать параметры limit, offset как keywork-only
        return await self._uow.attempts.list_by_user(user_id, limit=limit, offset=offset)

    async def get_monthly_stats(self, user_id: int, *, months: int) -> list[MonthlyStats]:
        since = self._months_ago(months)
        return await self._uow.attempts.get_monthly_stats(user_id, since)

    @staticmethod
    def _months_ago(months: int) -> datetime:
        """Начало месяца, отстоящего на `months` назад от текущего (UTC)."""
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month - months
        while month <= 0:
            month += 12
            year -= 1
        return now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
