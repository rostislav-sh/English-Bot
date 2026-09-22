"""Мок-реализации сервисов квизов (Фаза 1).

Честно соблюдают TestServiceProtocol/AttemptServiceProtocol, поэтому
роутеры и схемы не меняются при переходе на реальные сервисы (Фаза 2) —
меняется только DI-провайдер в api/dependencies/quiz.py.

Состояние живёт в памяти процесса (на request/reload сбрасывается) —
этого достаточно, чтобы фронтендер мог сверстать UI по реальному контракту.
"""

import itertools
import logging
from datetime import datetime, timezone

from src.domain.entities import Test, Question, TestAttempt, AttemptAnswer, MonthlyStats
from src.domain.enums import TestStatus, RecommendationStatus, QuestionType
from src.domain.exceptions import TestNotFoundError, AttemptNotFoundError, AnswersMismatchError

logger = logging.getLogger(__name__)

_FAKE_QUESTION_BANK: list[tuple[str, list[str], str]] = [
    ("I ___ to the store yesterday.", ["go", "went", "gone", "going"], "went"),
    ("She ___ English for five years.", ["study", "studies", "has studied", "studying"], "has studied"),
    ("They ___ dinner right now.", ["have", "having", "are having", "has"], "are having"),
    ("If it rains, we ___ stay home.", ["will", "would", "are", "were"], "will"),
    ("This is the ___ book I've ever read.", ["good", "better", "best", "well"], "best"),
]


class MockTestService:
    """Фейковый TestServiceProtocol: тест "генерируется" мгновенно (status=READY)."""

    def __init__(self) -> None:
        # Аналог БД
        self._tests: dict[int, Test] = {}
        # Имитация связей для быстрого поиска
        self._topic_ids: dict[str, int] = {}
        self._test_id_by_topic: dict[int, int] = {}
        # Генератор бесконечной последовательности.
        # Каждый вызов next() возвращает сл число.
        self._test_id_counter = itertools.count(1)
        self._topic_id_counter = itertools.count(1)
        self._question_id_counter = itertools.count(1)

    async def request_test(self, user_id: int, topic_name: str) -> Test:
        # topic_name.strip() — убрать пробелы по краям.
        # .lower() — привести к нижнему регистру.
        # .split() — разбить по любым пробельным символам (включая множественные пробелы/табы) на список слов.
        # " ".join(...) — склеить обратно через один пробел.
        # Исключаем дубли
        normalized = " ".join(topic_name.strip().lower().split())
        # next() - вычисляется всегда, но если в бд (словаре) уже есть, то не записываем
        # т.е будет не 1, 2, 3; а 1, 2, 7
        topic_id = self._topic_ids.setdefault(normalized, next(self._topic_id_counter))

        # Переиспользуем уже "сгенерированный" тест по теме — как и настоящий
        # find_reusable_for_user, просто без проверки "юзер уже проходил".
        # Специально отказываемся от параметра user_id, чтобы не писать полноценную бизнес логику.
        existing_test_id = self._test_id_by_topic.get(topic_id)
        if existing_test_id is not None:
            return self._tests[existing_test_id]

        test_id = next(self._test_id_counter)
        now = datetime.now(timezone.utc)
        questions = [
            Question(
                id=next(self._question_id_counter),
                test_id=test_id,
                text=text,
                options=list(options), # специально оборачиваем в список, чтобы ссылка не шла на _FAKE_QUESTION_BANK, а бы новый
                correct_answer=correct,
                question_type=QuestionType.MULTIPLE_CHOICE,
                created_at=now,
            )
            for text, options, correct in _FAKE_QUESTION_BANK
        ]
        test = Test(
            id=test_id,
            topic_id=topic_id,
            status=TestStatus.READY,
            questions=questions,
            created_at=now,
            updated_at=now,
        )
        self._tests[test_id] = test
        self._test_id_by_topic[topic_id] = test_id
        logger.debug("MockTestService: создан фейковый тест id=%s тема=%r", test_id, topic_name)
        return test

    async def get_test(self, user_id: int, test_id: int) -> Test:
        # Нет проверки прав пользователя, специальное упрощение
        test = self._tests.get(test_id)
        if test is None:
            raise TestNotFoundError()
        return test


class MockAttemptService:
    """Фейковый AttemptServiceProtocol: score считается реальной доменной логикой."""

    def __init__(self, test_service: MockTestService) -> None:
        self._test_service = test_service
        # главная таблица
        self._attempts: dict[int, TestAttempt] = {}
        # имитация связи
        self._attempt_ids_by_user: dict[int, list[int]] = {}
        # генератор
        self._attempt_id_counter = itertools.count(1)
        self._answer_id_counter = itertools.count(1)

    async def submit_answers(
            self, user_id: int, test_id: int, answers: list[tuple[int, str]],
    ) -> TestAttempt:

        test = await self._test_service.get_test(user_id, test_id)
        questions_by_id = {q.id: q for q in test.questions}

        # Проверяем полное совпадение id вопросов
        if {question_id for question_id, _ in answers} != set(questions_by_id):
            raise AnswersMismatchError()

        now = datetime.now(timezone.utc)
        attempt_answers = []
        score = 0
        for question_id, user_answer in answers:
            question = questions_by_id[question_id]
            # проверяем правильность ответа и увеличиваем счет
            is_correct = question.check_answer(user_answer)
            score += int(is_correct)
            # добавляем информацию об ответе
            attempt_answers.append(
                AttemptAnswer(
                    id=next(self._answer_id_counter),
                    question_id=question_id,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    created_at=now,
                )
            )

        has_mistakes = score < len(attempt_answers)
        attempt_id = next(self._attempt_id_counter)
        attempt = TestAttempt(
            id=attempt_id,
            user_id=user_id,
            test_id=test_id,
            score=score,
            total_questions=len(attempt_answers),
            answers=attempt_answers,
            # Если ошибка есть, то даем рекомендацию, пропуская статус PENDING и сразу переходим к READY.
            recommendation_status=(
                RecommendationStatus.READY if has_mistakes else RecommendationStatus.NOT_NEEDED
            ),
            ai_recommendation=self._fake_recommendation() if has_mistakes else None,
            created_at=now,
            updated_at=now,
        )
        self._attempts[attempt_id] = attempt
        # получить список по ключу, а если его нет — создать пустой и сразу добавить туда элемент
        self._attempt_ids_by_user.setdefault(user_id, []).append(attempt_id)
        logger.debug("MockAttemptService: попытка id=%s score=%s/%s", attempt_id, score, len(attempt_answers))
        return attempt

    async def get_attempt(self, user_id: int, attempt_id: int) -> TestAttempt:
        """Проверка на доступ к попыткам юзера или их отсутствие."""
        attempt = self._attempts.get(attempt_id)
        if attempt is None or attempt.user_id != user_id:
            # возвращаем одну и туже ошибку при разных сценариях
            raise AttemptNotFoundError()
        return attempt

    async def list_history(self, user_id: int, *, limit: int, offset: int) -> list[TestAttempt]:
        # * - передаем параметры позиционно
        # список ID попыток юзера (или пустой список, если попыток не было вообще).
        # Использование reversed дает сначала новые попытки.
        ids = list(reversed(self._attempt_ids_by_user.get(user_id, [])))
        # offset пагинация
        return [self._attempts[i] for i in ids[offset:offset + limit]]

    async def get_monthly_stats(self, user_id: int, *, months: int) -> list[MonthlyStats]:
        # * - передаем параметры позиционно
        attempts = [self._attempts[i] for i in self._attempt_ids_by_user.get(user_id, [])]
        if not attempts:
            return []
        # получаем начало текущего месяца из произвольного datetime
        current_month = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )
        # отдаем все попытки юзера
        # не важно когда, они были сделаны (если запросить за 6 месяцев, вернем за вес время)
        # специальное упрощение
        return [
            MonthlyStats(
                month=current_month,
                attempts_count=len(attempts),
                total_score=sum(a.score for a in attempts),
                total_questions=sum(a.total_questions for a in attempts),
            )
        ]

    @staticmethod
    def _fake_recommendation() -> str:
        return (
            "You made a few mistakes with verb tenses and word choice. "
            "Review the difference between present perfect and simple past, "
            "and practice with a few more example sentences. Keep going — you're improving!"
        )
