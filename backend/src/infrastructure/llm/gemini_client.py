"""Адаптер для Google Gemini через google-genai SDK."""

import logging
from typing import Final

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.application.interfaces.llm import (
    ILLMClient,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)

# Транзиентные ошибки, на которые имеет смысл сделать короткий ретрай
# на уровне HTTP-клиента (network blip, единичный 5xx).
# 429 и 503 в эту группу НЕ входят — их обрабатывает Celery.
_TRANSIENT_FOR_TENACITY: Final = (LLMTimeoutError,)


class GeminiClient(ILLMClient):
    """
    Реализация ILLMClient поверх google-genai SDK.

    Поведение:
        • Делает короткий ретрай (max_retries попыток) только на
          сетевые таймауты — это микро-ошибки, дешевле повторить
          сразу, чем гонять задачу через Celery-брокер.
        • 429 и 5xx превращаются в типизированные исключения,
          которые ловит Celery autoretry_for и откладывает задачу
          с countdown — воркер при этом не блокируется.
    """
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float, max_retries: int) -> None:
        # Звездочка * в аргументах заставляет передавать параметры только по имени (GeminiClient(api_key="...", ...)).
        # Это защита от путаницы в порядке аргументов.
        self._model = model
        self._timeout_ms = int(timeout_seconds * 1000)
        self._max_retries = max_retries

        # google-genai создаёт собственный httpx-клиент под капотом.
        # Таймаут пробрасываем через http_options.
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )

    # ── Public API ───────────────────────────────────────────────

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        """
        Отправляет prompt в LLM и возвращает сгенерированный текст.

        :param prompt: входной промпт.
        :param json_mode: если True — провайдер обязан вернуть валидный JSON
           (например, через response_mime_type у Gemini).
        :return: текст ответа.
        :raises LLMError: и его подклассы — см. описание класса.
        """
        # Обычно ретраи вешают так: @retry(stop=...).
        # Но декоратор @retry отрабатывает в момент загрузки файла (импорта).
        # На том этапе мы еще не знаем, сколько попыток (max_retries) указано в файле .env.
        # Поэтому мы создаем объект ретрая динамически (вызывая _build_retrying_call()) и прогоняем запрос через него.
        runner = self._build_retrying_call()
        return await runner(prompt, json_mode)

    def _build_retrying_call(self):
        """
        Строит обёртку с tenacity-ретраями на основе self._max_retries.

        Ретраим ТОЛЬКО на LLMTimeoutError — это микро-ошибка сети.
        Все остальные классы (Rate Limit, ServiceUnavailable) уходят
        наверх без задержки и ловятся в Celery.
        """
        return retry(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
            retry=retry_if_exception_type(_TRANSIENT_FOR_TENACITY),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=False,
        )(self._do_complete)

    async def _do_complete(self, prompt: str, json_mode: bool) -> str:
        """Один вызов к Gemini без ретраев."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
        except genai_errors.APIError as e:
            raise self._map_api_error(e) from e
        except TimeoutError as e:
            # Сетевой таймаут (httpx-уровень)
            raise LLMTimeoutError("Время ожидания запроса Gemini истекло") from e
        except Exception as e:
            # Всё неожиданное — наверх как LLMError
            logger.exception("Неожиданная ошибка во время вызова Gemini")
            raise LLMError(f"Неожиданная ошибка во время вызова Gemini: {e}") from e

        text = response.text
        if not text:
            raise LLMResponseError("Gemini вернул пустой ответ")

        return text

    @staticmethod
    def _map_api_error(e: genai_errors.APIError) -> LLMError:
        """
        Маппит ошибки google-genai в наши типизированные исключения.

        У google-genai APIError есть атрибут .code (HTTP-статус).
        """
        code = getattr(e, "code", None)

        if code == 429:
            return LLMRateLimitError(f"Превышен лимит скорости Gemini: {e}")
        if code is not None and 500 <= code < 600:
            return LLMServiceUnavailableError(f"Gemini server error {code}: {e}")
        if code in (408, 504):
            return LLMTimeoutError(f"Gemini gateway timeout {code}: {e}")

            # 4xx (кроме 429) — обычно невалидный запрос, ретраить бессмысленно
        return LLMError(f"Gemini API error {code}: {e}")
