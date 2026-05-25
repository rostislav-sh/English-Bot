import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

# Глобальный экземпляр ClientSession
http_client: Optional[aiohttp.ClientSession] = None

async def init_http_client() -> None:
    """Инициализация глобального aiohttp клиента."""
    global http_client
    if http_client is None:
        http_client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        logger.info("Глобальный aiohttp клиент инициализирован.")

async def close_http_client() -> None:
    """Закрытие глобального aiohttp клиента."""
    global http_client
    if http_client is not None:
        await http_client.close()
        http_client = None
        logger.info("Глобальный aiohttp клиент закрыт.")

def get_http_client() -> aiohttp.ClientSession:
    """Получение глобального aiohttp клиента."""
    if http_client is None:
        raise RuntimeError("http_client не инициализирован. Вызовите init_http_client().")
    return http_client