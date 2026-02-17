"""Implementação concreta do repositório de Tickets — SQLAlchemy com filtros."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.systems.tickets.repository import ITicketRepository
from app.infrastructure.database.models import (
    TicketModel, TicketReplyModel, TicketAttachmentModel, UserModel,
)
from app.domain.systems.tickets.entity import (
    Ticket, TicketStatus, TicketReply, TicketAttachment,
)
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

    @staticmethod
    def _attachment_to_entity(model: TicketAttachmentModel) -> TicketAttachment:
        return TicketAttachment(
            id=model.id,
            ticket_id=model.ticket_id,
            reply_id=model.reply_id,
            uploaded_by=model.uploaded_by,
            original_filename=model.original_filename,
            stored_filename=model.stored_filename,
            content_type=model.content_type,
            file_size=model.file_size,
            created_at=model.created_at,
        )

    @staticmethod
    def _reply_to_entity(model: TicketReplyModel) -> TicketReply:
        return TicketReply(
            id=model.id,
            ticket_id=model.ticket_id,
            author_id=model.author_id,
            body=model.body,
            attachments=[
                TicketRepository._attachment_to_entity(a)
                for a in (model.attachments or [])
            ],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ── Get com replies ──

    async def get_by_id_with_replies(self, ticket_id: int) -> Optional[Ticket]:
        stmt = (
            select(TicketModel)
            .where(TicketModel.id == ticket_id)
            .options(
                selectinload(TicketModel.replies)
                    .selectinload(TicketReplyModel.attachments),
                selectinload(TicketModel.attachments),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        ticket = self._to_entity(model)
        ticket.replies = [self._reply_to_entity(r) for r in model.replies]
        ticket.attachments = [self._attachment_to_entity(a) for a in model.attachments if a.reply_id is None]
        return ticket

    # ── Replies ──

    async def add_reply(self, reply: TicketReply) -> TicketReply:
        model = TicketReplyModel(
            ticket_id=reply.ticket_id,
            author_id=reply.author_id,
            body=reply.body,
        )
        self._session.add(model)
        await self._session.flush()
        return TicketReply(
            id=model.id,
            ticket_id=model.ticket_id,
            author_id=model.author_id,
            body=model.body,
            created_at=model.created_at,
        )

    async def get_replies(self, ticket_id: int) -> list[TicketReply]:
        stmt = (
            select(TicketReplyModel)
            .where(TicketReplyModel.ticket_id == ticket_id)
            .options(selectinload(TicketReplyModel.attachments))
            .order_by(TicketReplyModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._reply_to_entity(m) for m in result.scalars().all()]

    # ── Attachments ──

    async def add_attachment(self, attachment: TicketAttachment) -> TicketAttachment:
        model = TicketAttachmentModel(
            ticket_id=attachment.ticket_id,
            reply_id=attachment.reply_id,
            uploaded_by=attachment.uploaded_by,
            original_filename=attachment.original_filename,
            stored_filename=attachment.stored_filename,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
        )
        self._session.add(model)
        await self._session.flush()
        return self._attachment_to_entity(model)

    async def get_attachments(self, ticket_id: int) -> list[TicketAttachment]:
        stmt = (
            select(TicketAttachmentModel)
            .where(TicketAttachmentModel.ticket_id == ticket_id)
            .order_by(TicketAttachmentModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._attachment_to_entity(m) for m in result.scalars().all()]

    async def delete_attachment(self, attachment_id: int) -> None:
        model = await self._session.get(TicketAttachmentModel, attachment_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()

    # ── Agents ──

    async def list_agents(self) -> list[dict]:
        """Retorna lista de agentes {id, username} para dropdown."""
        stmt = (
            select(UserModel.id, UserModel.username)
            .where(UserModel.role == "agent")
            .where(UserModel.is_active == True)
            .order_by(UserModel.username)
        )
        result = await self._session.execute(stmt)
        return [{"id": row.id, "username": row.username} for row in result.all()]