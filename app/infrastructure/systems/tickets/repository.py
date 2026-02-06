"""Implementação concreta do repositório de Tickets — SQLAlchemy com filtros."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.systems.tickets.entity import Ticket, TicketStatus
from app.domain.systems.tickets.repository import ITicketRepository
from app.infrastructure.database.models import TicketModel


class TicketRepository(ITicketRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: TicketModel) -> Ticket:
        return Ticket(
            id=model.id,
            title=model.title,
            description=model.description or "",
            status=TicketStatus(model.status),
            milestones=model.milestones or [],
            assigned_to=model.assigned_to,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _build_filter(self, stmt, *, status=None, assigned_to=None, created_by=None, search=None):
        if status is not None:
            stmt = stmt.where(TicketModel.status == status.value)
        if assigned_to is not None:
            stmt = stmt.where(TicketModel.assigned_to == assigned_to)
        if created_by is not None:
            stmt = stmt.where(TicketModel.created_by == created_by)
        if search:
            stmt = stmt.where(TicketModel.title.ilike(f"%{search}%"))
        return stmt

    async def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        model = await self._session.get(TicketModel, ticket_id)
        return self._to_entity(model) if model else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[Ticket]:
        stmt = select(TicketModel).offset(skip).limit(limit).order_by(TicketModel.id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_filtered(
        self,
        *,
        status: Optional[TicketStatus] = None,
        assigned_to: Optional[int] = None,
        created_by: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Ticket]:
        stmt = select(TicketModel)
        stmt = self._build_filter(stmt, status=status, assigned_to=assigned_to, created_by=created_by, search=search)
        stmt = stmt.offset(skip).limit(limit).order_by(TicketModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_filtered(
        self,
        *,
        status: Optional[TicketStatus] = None,
        assigned_to: Optional[int] = None,
        created_by: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(TicketModel.id))
        stmt = self._build_filter(stmt, status=status, assigned_to=assigned_to, created_by=created_by, search=search)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, ticket: Ticket) -> Ticket:
        model = TicketModel(
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value,
            milestones=ticket.milestones_as_dicts(),
            assigned_to=ticket.assigned_to,
            created_by=ticket.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, ticket: Ticket) -> Ticket:
        model = await self._session.get(TicketModel, ticket.id)
        if not model:
            raise ValueError(f"Ticket {ticket.id} não encontrado")
        model.title = ticket.title
        model.description = ticket.description
        model.status = ticket.status.value
        model.milestones = ticket.milestones_as_dicts()
        model.assigned_to = ticket.assigned_to
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, ticket_id: int) -> None:
        model = await self._session.get(TicketModel, ticket_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
