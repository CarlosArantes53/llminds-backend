"""DTOs da camada de aplicação para Tickets — commands e queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ════════════════════════════════════════════════════════════════
# COMMANDS
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CreateTicketCommand:
    title: str
    created_by: int
    description: str = ""
    milestones: list[dict[str, Any]] = field(default_factory=list)
    assigned_to: Optional[int] = None


@dataclass(frozen=True)
class UpdateTicketCommand:
    ticket_id: int
    performed_by: int
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    milestones: Optional[list[dict[str, Any]]] = None
    assigned_to: Optional[int] = None


@dataclass(frozen=True)
class DeleteTicketCommand:
    ticket_id: int
    performed_by: int


@dataclass(frozen=True)
class AddMilestoneCommand:
    ticket_id: int
    performed_by: int
    title: str
    due_date: Optional[str] = None  # ISO format


@dataclass(frozen=True)
class CompleteMilestoneCommand:
    ticket_id: int
    milestone_index: int
    performed_by: int


@dataclass(frozen=True)
class TransitionTicketCommand:
    ticket_id: int
    new_status: str
    performed_by: int


# ════════════════════════════════════════════════════════════════
# QUERIES
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GetTicketByIdQuery:
    ticket_id: int


@dataclass(frozen=True)
class ListTicketsQuery:
    skip: int = 0
    limit: int = 100


# ════════════════════════════════════════════════════════════════
# RESULT DTOs
# ════════════════════════════════════════════════════════════════

@dataclass
class TicketResult:
    id: int
    title: str
    description: str
    status: str
    milestones: list[dict[str, Any]]
    assigned_to: Optional[int]
    created_by: Optional[int]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
