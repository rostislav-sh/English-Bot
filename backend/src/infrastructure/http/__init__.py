"""Модуль HTTP клиента."""
from .http_client import init_http_client, close_http_client, get_http_client

__all__ = ["init_http_client", "close_http_client", "get_http_client"]