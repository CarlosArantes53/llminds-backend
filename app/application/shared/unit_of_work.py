"""
Unit of Work — garante transacionalidade e despacho de eventos.

Encapsula a sessão do banco e, após commit, despacha os eventos
coletados das entidades.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events.base import AggregateRoot, DomainEvent
from app.application.shared.event_dispatcher import dispatch_events


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pending_events: list[DomainEvent] = []

    @property
    def session(self) -> AsyncSession:
        return self._session

    def collect_events_from(self, *aggregates: AggregateRoot) -> None:
        """Coleta eventos pendentes de um ou mais aggregates."""
        for agg in aggregates:
            self._pending_events.extend(agg.collect_events())

    async def commit(self) -> None:
        """Commit da sessão + despacho de eventos."""
        await self._session.commit()
        # Despacha após commit bem-sucedido
        if self._pending_events:
            await dispatch_events(self._pending_events)
            self._pending_events.clear()

    async def rollback(self) -> None:
        await self._session.rollback()
        self._pending_events.clear()

    async def flush(self) -> None:
        await self._session.flush()
