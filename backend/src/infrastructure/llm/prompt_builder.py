"""Конструктор промптов для LLM."""

from pathlib import Path
from string import Template
from typing import Literal

from src.infrastructure.llm.schemas import MistakeItem
from src.application.interfaces.llm import PromptGenerationError

Difficulty = Literal["beginner", "intermediate", "advanced"]


def load_templates() -> tuple[Template, Template]:
    """Считывает файлы с диска и возвращает готовые шаблоны."""
    prompts_dir = Path(__file__).parent / "prompts"

    test_gen_tpl = Template((prompts_dir / "test_generation.md").read_text(encoding="utf-8"))
    rec_tpl = Template((prompts_dir / "recommendation.md").read_text(encoding="utf-8"))

    return test_gen_tpl, rec_tpl


class PromptBuilder:
    """
    Pure-функции построения промптов.

    Никакого I/O, никаких внешних зависимостей — только форматирование строк.
    Это делает класс легко тестируемым: snapshot-тесты на ожидаемый текст,
    юнит-тесты на edge-cases (escaping, пустые поля, спецсимволы).
    """

    def __init__(self, test_gen_tpl: Template, rec_tpl: Template) -> None:
        self._test_gen_template = test_gen_tpl
        self._rec_template = rec_tpl

    def for_test_generation(
            self,
            topic_name: str,
            *,
            questions_count: int = 5,
            difficulty: Difficulty = "intermediate",
            language: str = "English",
    ) -> str:
        """
        Промпт для создания теста по теме.

        Используется в связке с json_mode=True:
        Gemini сам гарантирует структуру JSON, поэтому в промпте
        фокусируемся на содержательных требованиях, а не на формате.
        """
        return self._test_gen_template.substitute(
            language=language,
            topic_name=self._sanitize(topic_name),
            questions_count=questions_count,
            difficulty=difficulty,
        )

    def for_recommendation(
            self,
            topic_name: str,
            mistakes: list[MistakeItem],
            *,
            language: str = "English",
    ) -> str:
        if not mistakes:
            raise PromptGenerationError("Список ошибок не может быть пустым для промпта-рекомендаций.")

        return self._rec_template.substitute(
            language=language,
            topic_name=self._sanitize(topic_name),
            mistakes_block=self._format_mistakes(mistakes),
        )

    @staticmethod
    def _sanitize(text: str) -> str:
        return text.replace('"', "'").strip()

    @staticmethod
    def _format_mistakes(mistakes: list[MistakeItem]) -> str:
        lines = [
            f'{i}. Question: "{m.question}"\n'
            f'   Student: "{m.user_answer}" | Correct: "{m.correct_answer}"'
            for i, m in enumerate(mistakes, start=1)
        ]
        return "\n\n".join(lines)
