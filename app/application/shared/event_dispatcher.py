"""
Dispatcher de eventos de domínio.

Coleta eventos das entidades após persistência e despacha para handlers registrados.
Handlers podem gravar audit logs, enviar notificações, etc.
"""

from __future__ import annotations

import logging
from typing import Callable, Type

from app.domain.events.base import DomainEvent

logger = logging.getLogger(__name__)

# Registry: event_type → list[handler]
_handlers: dict[Type[DomainEvent], list[Callable]] = {}


def register_handler(event_type: Type[DomainEvent], handler: Callable) -> None:
    """Registra um handler para um tipo de evento."""
    _handlers.setdefault(event_type, []).append(handler)


async def dispatch_events(events: list[DomainEvent]) -> None:
    """Despacha lista de eventos para os handlers registrados."""
    for event in events:
        handlers = _handlers.get(type(event), [])
        for handler in handlers:
            try:
                result = handler(event)
                # Suporta handlers async e sync
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                logger.error(
                    "Erro ao despachar evento %s para handler %s: %s",
                    event.event_type,
                    handler.__name__,
                    exc,
                )


def clear_handlers() -> None:
    """Limpa todos os handlers (útil em testes)."""
    _handlers.clear()
