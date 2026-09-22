"""Исключения LLM-клиента."""

class LLMError(Exception):
    """Базовая ошибка LLM-клиента."""
    message = "Базовая ошибка LLM"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class LLMTimeoutError(LLMError):
    """Таймаут на стороне LLM-провайдера."""
    message = "Время ожидания запроса LLM истекло"


class LLMRateLimitError(LLMError):
    """Превышен rate limit (HTTP 429)."""
    message = "Превышен лимит LLM"


class LLMServiceUnavailableError(LLMError):
    """Сервис недоступен (HTTP 5xx)."""
    message = "LLM сервис недоступен"


class LLMResponseError(LLMError):
    """Провайдер вернул пустой/невалидный ответ (но HTTP 200)."""
    message = "LLM вернул невалидный ответ"


class PromptGenerationError(LLMError):
    """Ошибка при формировании промпта (например, некорректные входные данные)."""
    message = "Не удалось создать промпт-подсказку из-за неверного ввода."


class ParseError(Exception):
    """Базовая ошибка парсинга ответа LLM."""
    message = "Не удалось проанализировать ответ LLM."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class InvalidJSONError(ParseError):
    """LLM вернул синтаксически невалидный JSON."""
    message = "Ответ LLM вернул недействительный JSON."


class SchemaValidationError(ParseError):
    """JSON валиден, но не соответствует ожидаемой схеме."""
    message = "Ответ LLM не соответствует ожидаемой схеме."
