"""Схемы для валидации ответов от LLM и передачи данных в промпты."""

from pydantic import BaseModel, Field, ConfigDict


# ── Входящие данные (для PromptBuilder) ──────────────────────────

class MistakeItem(BaseModel):
    """Контекст ошибки пользователя в конкретном вопросе."""
    model_config = ConfigDict(frozen=True)  # Делаем объект неизменяемым

    question: str
    user_answer: str
    correct_answer: str


# ── Исходящие данные (от LLM, для парсера) ───────────────────────

class LLMQuestionSchema(BaseModel):
    text: str = Field(..., description="Текст вопроса")
    options: list[str] = Field(..., min_length=4, max_length=4, description="4 варианта")
    correct_index: int = Field(..., ge=0, le=3, description="Индекс правильного ответа (0-3)")

class LLMTestGenerationSchema(BaseModel):
    topic_name: str
    questions: list[LLMQuestionSchema] = Field(..., min_length=1)
