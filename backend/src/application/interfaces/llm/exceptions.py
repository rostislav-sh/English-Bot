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
    