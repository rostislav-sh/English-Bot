"""Сервисы для квизов."""

from .topic_service import TopicService
from .mocks import MockTestService, MockAttemptService

__all__ = ["TopicService", "MockTestService", "MockAttemptService"]
