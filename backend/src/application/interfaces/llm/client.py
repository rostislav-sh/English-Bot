"""Контракт LLM-клиента."""

from typing import Protocol, runtime_checkable

@runtime_checkable # проверяет только методы, не проверяет что в них передано
class ILLMClient(Protocol):
    """
    Минимальный контракт для текстовой генерации.

    Реализация должна:
        • поднимать LLMTimeoutError / LLMRateLimitError /
          LLMServiceUnavailableError на соответствующие сбои —
          именно эти исключения ловит Celery autoretry_for;
        • поднимать LLMResponseError, если провайдер вернул
          пустой контент или нарушил формат на уровне SDK;
        • НЕ парсить и НЕ валидировать содержимое ответа —
          это задача Parser в сервисном слое.
    """

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        """
       Отправляет prompt в LLM и возвращает сгенерированный текст.

       :param prompt: входной промпт.
       :param json_mode: если True — провайдер обязан вернуть валидный JSON
           (например, через response_mime_type у Gemini).
       :return: текст ответа.
       :raises LLMError: и его подклассы — см. описание класса.
       """
        ...
