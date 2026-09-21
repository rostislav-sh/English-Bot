"""Маршруты квизов.

Эндпоинты: темы, запрос/получение теста, прохождение (сабмит),
история попыток и статистика.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.interfaces.quiz import TestServiceProtocol, AttemptServiceProtocol
from src.application.services.quiz import TopicService
from src.api.dependencies import (
    verify_csrf_token,
    get_current_user_id_from_access_token,
    get_topic_service,
    get_test_service,
    get_attempt_service,
)
from src.api.schemas.quiz import (
    TopicOut,
    RequestTestIn,
    QuestionOut,
    TestOut,
    SubmitAnswersIn,
    AnswerResultOut,
    AttemptOut,
    AttemptHistoryItemOut,
    MonthlyStatOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Темы ──────────────────────────────────────────────────────────────

@router.get(
    "/topics",
    summary="Список системных тем",
    response_model=list[TopicOut],
)
async def list_topics(
        service: Annotated[TopicService, Depends(get_topic_service)],
):
    """Список тем, доступных для выбора при запросе теста."""
    topics = await service.list_system_topics()
    return [TopicOut(id=t.id, name=t.name, is_custom=t.is_custom) for t in topics]


# ── Тесты ─────────────────────────────────────────────────────────────

@router.post(
    "/tests",
    summary="Запросить тест по теме",
    response_model=TestOut,
    dependencies=[Depends(verify_csrf_token)],
)
async def request_test(
        data: RequestTestIn,
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[TestServiceProtocol, Depends(get_test_service)],
):
    """Создаёт (или переиспользует готовый) тест по теме.

    Если тест ещё генерируется — `status=generating`, `questions` пуст.
    Фронт опрашивает GET /tests/{id}, пока status не станет `ready`.
    """
    logger.info("POST /tests user_id=%s topic=%r", user_id, data.topic_name)
    test = await service.request_test(user_id, data.topic_name)
    return _test_to_out(test)


@router.get(
    "/tests/{test_id}",
    summary="Получить тест (для polling статуса генерации)",
    response_model=TestOut,
    dependencies=[Depends(verify_csrf_token)],
)
async def get_test(
        test_id: int,
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[TestServiceProtocol, Depends(get_test_service)],
):
    test = await service.get_test(user_id, test_id)
    return _test_to_out(test)


@router.post(
    "/tests/{test_id}/submit",
    summary="Отправить все ответы теста разом",
    response_model=AttemptOut,
    dependencies=[Depends(verify_csrf_token)],
)
async def submit_test(
        test_id: int,
        data: SubmitAnswersIn,
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[AttemptServiceProtocol, Depends(get_attempt_service)],
        test_service: Annotated[TestServiceProtocol, Depends(get_test_service)],
):
    """Проверяет ответы, сохраняет попытку. Рекомендация может появиться позже —
    см. GET /attempts/{id} для polling `recommendation_status`.
    """
    logger.info("POST /tests/%s/submit user_id=%s", test_id, user_id)
    answers = [(a.question_id, a.answer) for a in data.answers]
    attempt = await service.submit_answers(user_id, test_id, answers)
    correct_answers = await _get_correct_answers(user_id, attempt.test_id, test_service)
    return _attempt_to_out(attempt, correct_answers)


# ── Попытки / история / статистика ──────────────────────────────────

@router.get(
    "/attempts/{attempt_id}",
    summary="Получить попытку (для polling статуса рекомендации)",
    response_model=AttemptOut,
    dependencies=[Depends(verify_csrf_token)],
)
async def get_attempt(
        attempt_id: int,
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[AttemptServiceProtocol, Depends(get_attempt_service)],
        test_service: Annotated[TestServiceProtocol, Depends(get_test_service)],
):
    attempt = await service.get_attempt(user_id, attempt_id)
    correct_answers = await _get_correct_answers(user_id, attempt.test_id, test_service)
    return _attempt_to_out(attempt, correct_answers)


@router.get(
    "/attempts",
    summary="История попыток пользователя",
    response_model=list[AttemptHistoryItemOut],
    dependencies=[Depends(verify_csrf_token)],
)
async def list_attempts(
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[AttemptServiceProtocol, Depends(get_attempt_service)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
):
    attempts = await service.list_history(user_id, limit=limit, offset=offset)
    return [
        AttemptHistoryItemOut(
            id=a.id,
            test_id=a.test_id,
            score=a.score,
            total_questions=a.total_questions,
            percentage=a.percentage,
            created_at=a.created_at,
        )
        for a in attempts
    ]


@router.get(
    "/attempts/stats/monthly",
    summary="Статистика пользователя по месяцам",
    response_model=list[MonthlyStatOut],
    dependencies=[Depends(verify_csrf_token)],
)
async def get_monthly_stats(
        user_id: Annotated[int, Depends(get_current_user_id_from_access_token)],
        service: Annotated[AttemptServiceProtocol, Depends(get_attempt_service)],
        months: Annotated[int, Query(ge=1, le=24)] = 12,
):
    stats = await service.get_monthly_stats(user_id, months=months)
    return [
        MonthlyStatOut(
            month=s.month,
            attempts_count=s.attempts_count,
            total_score=s.total_score,
            total_questions=s.total_questions,
            accuracy=s.accuracy,
        )
        for s in stats
    ]


# ── Мапперы entity → schema ──────────────────────────────────────────

def _test_to_out(test) -> TestOut:
    return TestOut(
        id=test.id,
        topic_id=test.topic_id,
        status=test.status,
        questions=[
            QuestionOut(
                id=q.id,
                text=q.text,
                options=q.options,
                question_type=q.question_type,
            )
            for q in test.questions
        ],
    )


async def _get_correct_answers(
        user_id: int, test_id: int, test_service: TestServiceProtocol,
) -> dict[int, str]:
    """correct_answer живёт на Question, а не на AttemptAnswer — подгружаем тест,
    чтобы собрать вопрос → правильный ответ для отображения результата."""
    test = await test_service.get_test(user_id, test_id)
    return {q.id: q.correct_answer for q in test.questions}


def _attempt_to_out(attempt, correct_answers: dict[int, str]) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        test_id=attempt.test_id,
        score=attempt.score,
        total_questions=attempt.total_questions,
        percentage=attempt.percentage,
        is_perfect=attempt.is_perfect,
        recommendation_status=attempt.recommendation_status,
        ai_recommendation=attempt.ai_recommendation,
        answers=[
            AnswerResultOut(
                question_id=a.question_id,
                user_answer=a.user_answer,
                correct_answer=correct_answers.get(a.question_id, ""),
                is_correct=a.is_correct,
            )
            for a in attempt.answers
        ],
    )
