"""
Use Cases de Tickets — camada de Aplicação.

Orquestram state machine, milestones e eventos de domínio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.systems.tickets.entity import Ticket, TicketStatus
from app.domain.systems.tickets.repository import ITicketRepository
from app.domain.systems.users.entity import User
from app.domain.systems.users.authorization_service import AuthorizationService
from app.domain.shared.value_objects import Milestone
from app.application.dtos.ticket_dtos import (
    AddMilestoneCommand,
    CompleteMilestoneCommand,
    CreateTicketCommand,
    DeleteTicketCommand,
    GetTicketByIdQuery,
    ListTicketsQuery,
    TicketResult,
    TransitionTicketCommand,
    UpdateTicketCommand,
)
from app.application.shared.unit_of_work import UnitOfWork


def _to_result(t: Ticket) -> TicketResult:
    return TicketResult(
        id=t.id,
        title=t.title,
        description=t.description,
        status=t.status.value,
        milestones=t.milestones_as_dicts(),
        assigned_to=t.assigned_to,
        created_by=t.created_by,
        created_at=t.created_at.isoformat() if t.created_at else None,
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
    )


class CreateTicketUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: CreateTicketCommand) -> TicketResult:
        # Converte milestones dict → VO
        milestones = [Milestone.from_dict(m) for m in cmd.milestones] if cmd.milestones else []

        ticket = Ticket(
            title=cmd.title,
            description=cmd.description,
            milestones=milestones,
            assigned_to=cmd.assigned_to,
            created_by=cmd.created_by,
        )

        created = await self._repo.create(ticket)
        created.record_creation()
        self._uow.collect_events_from(created)
        await self._uow.commit()
        return _to_result(created)


class GetTicketUseCase:
    def __init__(self, repo: ITicketRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetTicketByIdQuery, actor: User) -> Optional[TicketResult]:
        ticket = await self._repo.get_by_id(query.ticket_id)
        if not ticket:
            return None
        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)
        return _to_result(ticket)


class ListTicketsUseCase:
    def __init__(self, repo: ITicketRepository) -> None:
        self._repo = repo

    async def execute(self, query: ListTicketsQuery) -> list[TicketResult]:
        tickets = await self._repo.list_all(skip=query.skip, limit=query.limit)
        return [_to_result(t) for t in tickets]


class UpdateTicketUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: UpdateTicketCommand, actor: User) -> TicketResult:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        if cmd.title is not None:
            ticket.title = cmd.title
        if cmd.description is not None:
            ticket.description = cmd.description
        if cmd.assigned_to is not None:
            ticket.assign_to(cmd.assigned_to, assigned_by=cmd.performed_by)
        if cmd.milestones is not None:
            ticket.milestones = [Milestone.from_dict(m) for m in cmd.milestones]
        if cmd.status is not None:
            new_status = TicketStatus(cmd.status)
            ticket.transition_to(new_status, changed_by=cmd.performed_by)

        updated = await self._repo.update(ticket)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class TransitionTicketUseCase:
    """Use case dedicado para transição de status (state machine)."""

    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: TransitionTicketCommand, actor: User) -> TicketResult:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        new_status = TicketStatus(cmd.new_status)
        ticket.transition_to(new_status, changed_by=cmd.performed_by)

        updated = await self._repo.update(ticket)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class AddMilestoneUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: AddMilestoneCommand, actor: User) -> TicketResult:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        due = datetime.fromisoformat(cmd.due_date) if cmd.due_date else None
        milestone = Milestone(title=cmd.title, due_date=due)
        ticket.add_milestone(milestone)

        updated = await self._repo.update(ticket)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class CompleteMilestoneUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: CompleteMilestoneCommand, actor: User) -> TicketResult:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        ticket.complete_milestone(cmd.milestone_index)

        updated = await self._repo.update(ticket)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class DeleteTicketUseCase:
    def __init__(self, repo: ITicketRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: DeleteTicketCommand, actor: User) -> None:
        ticket = await self._repo.get_by_id(cmd.ticket_id)
        if not ticket:
            raise ValueError("Ticket não encontrado")

        AuthorizationService.ensure_can_access_ticket(actor, ticket.created_by, ticket.assigned_to)

        ticket.record_deletion(deleted_by=cmd.performed_by)
        self._uow.collect_events_from(ticket)
        await self._repo.delete(cmd.ticket_id)
        await self._uow.commit()
