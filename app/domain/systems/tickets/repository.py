from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .entity import Ticket, TicketStatus


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
