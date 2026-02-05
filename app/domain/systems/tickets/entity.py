"""Entidade de domínio Ticket — com state machine, milestones e eventos."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.domain.events.base import AggregateRoot
from app.domain.events.ticket_events import (
    MilestoneAdded,
    MilestoneCompleted,
    TicketAssigned,
    TicketCreated,
    TicketDeleted,
    TicketStatusChanged,
)
from app.domain.shared.value_objects import Milestone


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# Transições válidas da state machine
_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.DONE, TicketStatus.OPEN],
    TicketStatus.DONE: [TicketStatus.OPEN],
}


@dataclass
class Ticket(AggregateRoot):
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    status: TicketStatus = TicketStatus.OPEN
    milestones: list[Milestone] = field(default_factory=list)
    assigned_to: Optional[int] = None   # FK → User
    created_by: Optional[int] = None    # FK → User
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        AggregateRoot.__init__(self)
        # Converte dicts legados para Milestone VO
        self.milestones = [
            Milestone.from_dict(m) if isinstance(m, dict) else m
            for m in self.milestones
        ]

    # ── State machine ──

    def can_transition_to(self, new_status: TicketStatus) -> bool:
        return new_status in _TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: TicketStatus, changed_by: Optional[int] = None) -> None:
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Transição inválida: {self.status.value} → {new_status.value}"
            )
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        self._record_event(TicketStatusChanged(
            ticket_id=self.id,
            old_status=old_status.value,
            new_status=new_status.value,
            changed_by=changed_by,
        ))

    # ── Assignment ──

    def assign_to(self, user_id: int, assigned_by: Optional[int] = None) -> None:
        old = self.assigned_to
        self.assigned_to = user_id
        self.updated_at = datetime.utcnow()
        self._record_event(TicketAssigned(
            ticket_id=self.id,
            old_assignee=old,
            new_assignee=user_id,
            assigned_by=assigned_by,
        ))

    # ── Milestones ──

    def add_milestone(self, milestone: Milestone) -> None:
        milestone_with_order = Milestone(
            title=milestone.title,
            due_date=milestone.due_date,
            completed=milestone.completed,
            completed_at=milestone.completed_at,
            order=len(self.milestones),
        )
        self.milestones.append(milestone_with_order)
        self.updated_at = datetime.utcnow()
        self._record_event(MilestoneAdded(
            ticket_id=self.id,
            milestone_title=milestone.title,
            due_date=milestone.due_date.isoformat() if milestone.due_date else None,
        ))

    def complete_milestone(self, index: int) -> None:
        if index < 0 or index >= len(self.milestones):
            raise IndexError(f"Milestone index {index} fora do range")
        old = self.milestones[index]
        if old.completed:
            return
        self.milestones[index] = old.mark_completed()
        self.updated_at = datetime.utcnow()
        self._record_event(MilestoneCompleted(
            ticket_id=self.id,
            milestone_title=old.title,
        ))

    def all_milestones_completed(self) -> bool:
        return len(self.milestones) > 0 and all(m.completed for m in self.milestones)

    def overdue_milestones(self) -> list[Milestone]:
        return [m for m in self.milestones if m.is_overdue()]

    # ── Serialização de milestones para JSONB ──

    def milestones_as_dicts(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.milestones]

    # ── Eventos auxiliares ──

    def record_creation(self) -> None:
        self._record_event(TicketCreated(
            ticket_id=self.id,
            title=self.title,
            created_by=self.created_by,
        ))

    def record_deletion(self, deleted_by: Optional[int] = None) -> None:
        self._record_event(TicketDeleted(
            ticket_id=self.id,
            deleted_by=deleted_by,
        ))
