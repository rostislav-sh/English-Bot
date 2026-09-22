"""Схемы для валидации ответов от LLM и передачи данных в промпты.

Двойное назначение:
    1. Валидация JSON-ответа от LLM.
    2. Промежуточный DTO между сырым ответом и domain entities.

Эти схемы — деталь инфраструктуры. В domain (entities/services) они НЕ
утекают: Parser возвращает их, но сервис сразу маппит в Test/Question.
"""

from pydantic import BaseModel, Field, ConfigDict, model_validator


# ── Входящие данные (для PromptBuilder) ──────────────────────────

class MistakeItem(BaseModel):
    """Контекст ошибки пользователя в конкретном вопросе."""
    model_config = ConfigDict(frozen=True)  # Делаем объект неизменяемым

    question: str
    user_answer: str
    correct_answer: str


# ── Исходящие данные (от LLM, для парсера) ───────────────────────

class GeneratedQuestion(BaseModel):
    """Один вопрос из ответа LLM."""

    text: str = Field(min_length=3, max_length=500)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_correct_index_in_range(self) -> "GeneratedQuestion":
        if self.correct_index >= len(self.options):
            raise ValueError(
                f"correct_index={self.correct_index} is out of range "
                f"for options length={len(self.options)}"
            )
        # Опции должны быть уникальны — иначе непонятно, что выбрал юзер
        if len(set(self.options)) != len(self.options):
            raise ValueError("options must be unique")
        return self


class GeneratedTest(BaseModel):
    """Тест целиком — корневая схема для валидации ответа LLM."""

    topic_name: str = Field(min_length=1, max_length=100)
    questions: list[GeneratedQuestion] = Field(min_length=3, max_length=15)
