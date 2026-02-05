"""Eventos de domínio relacionados a Tickets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class TicketCreated(DomainEvent):
    ticket_id: int = 0
    title: str = ""
    created_by: Optional[int] = None


@dataclass(frozen=True)
class TicketStatusChanged(DomainEvent):
    ticket_id: int = 0
    old_status: str = ""
    new_status: str = ""
    changed_by: Optional[int] = None


@dataclass(frozen=True)
class TicketAssigned(DomainEvent):
    ticket_id: int = 0
    old_assignee: Optional[int] = None
    new_assignee: Optional[int] = None
    assigned_by: Optional[int] = None


@dataclass(frozen=True)
class MilestoneAdded(DomainEvent):
    ticket_id: int = 0
    milestone_title: str = ""
    due_date: Optional[str] = None


@dataclass(frozen=True)
class MilestoneCompleted(DomainEvent):
    ticket_id: int = 0
    milestone_title: str = ""


@dataclass(frozen=True)
class TicketDeleted(DomainEvent):
    ticket_id: int = 0
    deleted_by: Optional[int] = None
