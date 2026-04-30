# src/infrastructure/database/quiz_mappers.py
"""
Маппинг между доменными сущностями квизов и ORM-моделями.

Соглашение об именах — то же, что в auth-маппере:
    entity_to_model
    model_to_entity
    update_model_from_entity
"""
from src.domain.entities import (
    Topic, Test, Question, TestAttempt, AttemptAnswer,
)
from .models import (
    TopicModel, TestModel, QuestionModel,
    TestAttemptModel, AttemptAnswerModel,
)


# ════════════════════════════════════════
#  TOPIC
# ════════════════════════════════════════

def topic_entity_to_model(entity: Topic) -> TopicModel:
    return TopicModel(
        name=entity.name,
        normalized_name=entity.normalized_name,
        is_custom=entity.is_custom,
    )


def topic_model_to_entity(model: TopicModel) -> Topic:
    return Topic(
        id=model.id,
        name=model.name,
        normalized_name=model.normalized_name,
        is_custom=model.is_custom,
        created_at=model.created_at,
    )


# Topic в нашей системе иммутабелен после создания —
# update_topic_model_from_entity не нужен.


# ════════════════════════════════════════
#  QUESTION
# ════════════════════════════════════════

def question_entity_to_model(entity: Question) -> QuestionModel:
    return QuestionModel(
        test_id=entity.test_id,
        question_type=entity.question_type,
        text=entity.text,
        options=entity.options,
        correct_answer=entity.correct_answer,
    )


def question_model_to_entity(model: QuestionModel) -> Question:
    return Question(
        id=model.id,
        test_id=model.test_id,
        question_type=model.question_type,
        text=model.text,
        options=model.options,
        correct_answer=model.correct_answer,
        created_at=model.created_at,
    )


# Question тоже иммутабелен — после создания вопросы не редактируются.


# ════════════════════════════════════════
#  TEST
# ════════════════════════════════════════

def test_entity_to_model(entity: Test) -> TestModel:
    """ORM-модель теста БЕЗ вопросов.

    Вопросы сохраняются отдельно через question_entity_to_model,
    либо через relationship-cascade — на усмотрение репозитория.

    На счет рассинхрона тут и в attempt_entity_to_model:
    Почему attempt + answers сохраняются вместе, а test + questions — нет
    Это реальная разница в жизненном цикле :

    Сценарий	        Test + Questions	         Attempt + Answers
    Когда создаются?	В разные моменты времени	 Атомарно, одновременно
    Кто создаёт?	    Test — сразу при запросе     Сервис в одной транзакции после submit
                        юзера (status=GENERATING).
                        Questions — позже, в Celery,
                        когда Gemini вернул ответ
    Возможно ли
    частичное состояние? Да: Test существует с        Нет: попытка без ответов бессмысленна
                         status=GENERATING и
                         questions=[] несколько секунд

    То есть:
    T0:  POST /tests/request    → INSERT test (status=GENERATING, questions=[])
    T1:  Celery → Gemini API    → ...3-15 секунд...
    T2:  Celery получил ответ   → INSERT 10 questions + UPDATE test SET status=READY
    Если бы я делал cascade-сохранение в test_entity_to_model, это не сломалось бы,
    но ввело бы в заблуждение: создаётся впечатление, что Test без вопросов невалиден,
    хотя он валиден (это нормальное промежуточное состояние).
    """
    return TestModel(
        topic_id=entity.topic_id,
        status=entity.status,
        generation_task_id=entity.generation_task_id,
    )


def test_model_to_entity(model: TestModel, *, with_questions: bool = False) -> Test:
    """ORM → entity.

    with_questions=True — подгружаем вопросы (model.questions должен быть
    предзагружен через selectinload в репозитории, иначе lazy-load в async = ошибка).
    """
    questions = (
        [question_model_to_entity(q) for q in model.questions]
        if with_questions
        else []
    )
    return Test(
        id=model.id,
        topic_id=model.topic_id,
        status=model.status,
        generation_task_id=model.generation_task_id,
        questions=questions,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_test_model_from_entity(model: TestModel, entity: Test) -> None:
    """У теста меняется только status и task_id (после генерации Celery)."""
    model.status = entity.status
    model.generation_task_id = entity.generation_task_id


# ════════════════════════════════════════
#  ATTEMPT ANSWER
# ════════════════════════════════════════

def attempt_answer_entity_to_model(entity: AttemptAnswer) -> AttemptAnswerModel:
    return AttemptAnswerModel(
        attempt_id=entity.attempt_id,  # может быть None, если сохраняем через cascade
        question_id=entity.question_id,
        user_answer=entity.user_answer,
        is_correct=entity.is_correct,
    )


def attempt_answer_model_to_entity(model: AttemptAnswerModel) -> AttemptAnswer:
    return AttemptAnswer(
        id=model.id,
        attempt_id=model.attempt_id,
        question_id=model.question_id,
        user_answer=model.user_answer,
        is_correct=model.is_correct,
        created_at=model.created_at,
    )


# AttemptAnswer иммутабелен — после сохранения ответы не меняются.


# ════════════════════════════════════════
#  TEST ATTEMPT
# ════════════════════════════════════════

def attempt_entity_to_model(entity: TestAttempt) -> TestAttemptModel:
    """ORM-модель попытки ВМЕСТЕ с ответами через cascade.

    SQLAlchemy сам сохранит answers и проставит attempt_id —
    это работает за счёт relationship + cascade='all, delete-orphan'.
    """
    return TestAttemptModel(
        user_id=entity.user_id,
        test_id=entity.test_id,
        score=entity.score,
        total_questions=entity.total_questions,
        recommendation_status=entity.recommendation_status,
        ai_recommendation=entity.ai_recommendation,
        answers=[
            attempt_answer_entity_to_model(a)
            for a in entity.answers
        ],
    )


def attempt_model_to_entity(
    model: TestAttemptModel,
    *,
    with_answers: bool = False,
) -> TestAttempt:
    answers = (
        [attempt_answer_model_to_entity(a) for a in model.answers]
        if with_answers
        else []
    )
    return TestAttempt(
        id=model.id,
        user_id=model.user_id,
        test_id=model.test_id,
        score=model.score,
        total_questions=model.total_questions,
        recommendation_status=model.recommendation_status,
        ai_recommendation=model.ai_recommendation,
        answers=answers,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_attempt_model_from_entity(model: TestAttemptModel, entity: TestAttempt) -> None:
    """У попытки после создания меняется только рекомендация (Celery дописывает её позже)."""
    model.recommendation_status = entity.recommendation_status
    model.ai_recommendation = entity.ai_recommendation
