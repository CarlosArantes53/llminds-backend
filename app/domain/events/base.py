"""
Sistema de eventos de domínio.

Entidades disparam eventos; a camada de aplicação os coleta e despacha
para handlers (notificações, audit logs, side-effects).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(frozen=True)
class DomainEvent:
    """Classe base para todos os eventos de domínio."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


class AggregateRoot:
    """
    Mixin para entidades que disparam eventos de domínio.
    Coleta eventos em _events; a camada de aplicação chama collect_events()
    após persistir para despachar.
    """

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def _record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
