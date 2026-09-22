"""Пакет интерфейсов (протоколы и абстрактные классы)."""

from .auth import AuthServiceProtocol
from .quiz import TestServiceProtocol, AttemptServiceProtocol

__all__ = ["AuthServiceProtocol", "TestServiceProtocol", "AttemptServiceProtocol"]