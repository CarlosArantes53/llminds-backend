from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .entity import Ticket, TicketStatus, TicketReply, TicketAttachment


class ITicketRepository(ABC):

    @abstractmethod
    async def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[Ticket]:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def count_filtered(
        self,
        *,
        status: Optional[TicketStatus] = None,
        assigned_to: Optional[int] = None,
        created_by: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        ...

    @abstractmethod
    async def create(self, ticket: Ticket) -> Ticket:
        ...

    @abstractmethod
    async def update(self, ticket: Ticket) -> Ticket:
        ...

    @abstractmethod
    async def delete(self, ticket_id: int) -> None:
        ...

    @abstractmethod
    async def get_by_id_with_replies(self, ticket_id: int) -> Optional[Ticket]:
        ...

    @abstractmethod
    async def add_reply(self, reply: TicketReply) -> TicketReply:
        ...

    @abstractmethod
    async def get_replies(self, ticket_id: int) -> Sequence[TicketReply]:
        ...

    # ── Attachments ──

    @abstractmethod
    async def add_attachment(self, attachment: TicketAttachment) -> TicketAttachment:
        ...

    @abstractmethod
    async def get_attachments(self, ticket_id: int) -> Sequence[TicketAttachment]:
        ...

    @abstractmethod
    async def delete_attachment(self, attachment_id: int) -> None:
        ...

    # ── Agents lookup ──

    @abstractmethod
    async def list_agents(self) -> Sequence:
        """Lista usuários com role=agent para o dropdown de atribuição."""
        ...