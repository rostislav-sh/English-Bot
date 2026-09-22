"""Парсинг ответов LLM с типизированной обработкой ошибок."""

import json
import logging

from pydantic import ValidationError

from src.infrastructure.llm.schemas import GeneratedTest
from src.application.interfaces.llm import InvalidJSONError, SchemaValidationError


logger = logging.getLogger(__name__)


class TestParser:
    """
    Парсер сгенерированного теста.

    Изолирует json+pydantic от сервисного слоя. Сервис ловит
    типизированные ParseError-исключения и решает, что делать:
    повторить запрос к LLM, упасть с пометкой test.status=FAILED,
    отправить в DLQ и т.п.
    """

    @staticmethod
    def parser(raw: str) -> GeneratedTest:
        """
        Парсит сырой текст от LLMClient.complete() в GeneratedTest.

        :raises InvalidJSONError: невалидный JSON-синтаксис.
        :raises SchemaValidationError: JSON валиден, но не подходит под схему.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("LLM вернул неверный JSON (первые 200 символов): %r", raw[:200])
            raise InvalidJSONError(f"Ошибка декодирования JSON на позиции {e.pos}: {e.msg}") from e

        try:
            return GeneratedTest.model_validate(data)
        except ValidationError as e:
            logger.warning("Ответ LLM не подошел под pydantic схему: %s", e)
            raise SchemaValidationError(str(e)) from e
        