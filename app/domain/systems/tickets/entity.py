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
    replies: list[TicketReply] = field(default_factory=list)
    attachments: list[TicketAttachment] = field(default_factory=list)

    # ── Assignment (regra de negócio) ──

    def assign_to_agent(
        self,
        agent_id: int,
        agent_role: str,
        assigned_by: int,
        assigner_role: str,
    ) -> None:
        """Apenas admin pode atribuir, e apenas para agentes."""
        if assigner_role != "admin":
            raise ValueError("Apenas administradores podem atribuir tickets")
        if agent_role != "agent":
            raise ValueError("Tickets só podem ser atribuídos a usuários com role 'agent'")

        old = self.assigned_to
        self.assigned_to = agent_id
        self.updated_at = datetime.utcnow()
        self._record_event(TicketAssigned(
            ticket_id=self.id,
            old_assignee=old,
            new_assignee=agent_id,
            assigned_by=assigned_by,
        ))

    # ── Replies (regra de negócio) ──

    def can_reply(self, user_id: int, user_role: str) -> bool:
        """Criador, agente atribuído ou admin podem responder."""
        if user_role == "admin":
            return True
        if user_id == self.created_by:
            return True
        if user_id == self.assigned_to:
            return True
        return False

    def add_reply(self, reply: TicketReply, user_role: str) -> None:
        if not self.can_reply(reply.author_id, user_role):
            raise ValueError(
                "Apenas o criador do ticket, agente atribuído ou admin podem responder"
            )
        reply.ticket_id = self.id
        reply.validate()
        self.replies.append(reply)
        self.updated_at = datetime.utcnow()

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

@dataclass
class TicketAttachment:
    """Value object para anexo de ticket."""
    id: Optional[int] = None
    ticket_id: Optional[int] = None
    reply_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    original_filename: str = ""
    stored_filename: str = ""
    content_type: str = ""
    file_size: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TicketReply:
    """Uma resposta/mensagem em um ticket."""
    id: Optional[int] = None
    ticket_id: Optional[int] = None
    author_id: Optional[int] = None
    body: str = ""
    attachments: list[TicketAttachment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def validate(self) -> None:
        if not self.body.strip():
            raise ValueError("body da resposta não pode ser vazio")