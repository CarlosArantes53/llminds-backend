"""
Endpoints de Tickets — /api/v1/tickets

CRUD + state machine transitions + milestones + paginação + filtros.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.systems.tickets.entity import TicketStatus
from app.domain.systems.users.entity import User
from app.infrastructure.systems.tickets.repository import TicketRepository
from app.application.shared.unit_of_work import UnitOfWork
from app.application.dtos.ticket_dtos import (
    AddMilestoneCommand,
    CompleteMilestoneCommand,
    CreateTicketCommand,
    DeleteTicketCommand,
    GetTicketByIdQuery,
    TransitionTicketCommand,
    UpdateTicketCommand,
)
from app.application.systems.tickets.use_cases import (
    AddMilestoneUseCase,
    CompleteMilestoneUseCase,
    CreateTicketUseCase,
    DeleteTicketUseCase,
    GetTicketUseCase,
    TransitionTicketUseCase,
    UpdateTicketUseCase,
)
from app.presentation.api.v1.schemas import (
    MilestoneAddRequest,
    MilestoneCompleteRequest,
    PaginatedResponse,
    TicketCreate,
    TicketOut,
    TicketStatusEnum,
    TicketUpdate,
    TransitionRequest,
)
from app.presentation.api.v1.deps import get_current_active_user, get_uow, get_ticket_repo

router = APIRouter()


def _to_out(r) -> TicketOut:
    return TicketOut(
        id=r.id, title=r.title, description=r.description,
        status=r.status, milestones=r.milestones,
        assigned_to=r.assigned_to, created_by=r.created_by,
    )


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar ticket",
)
async def create_ticket(
    payload: TicketCreate,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    milestones_dicts = [m.model_dump() for m in payload.milestones] if payload.milestones else []
    uc = CreateTicketUseCase(repo, uow)
    result = await uc.execute(CreateTicketCommand(
        title=payload.title,
        description=payload.description,
        milestones=milestones_dicts,
        assigned_to=payload.assigned_to,
        created_by=current_user.id,
    ))
    return _to_out(result)


@router.get(
    "/",
    response_model=PaginatedResponse[TicketOut],
    summary="Listar tickets com paginação e filtros",
    description="Filtros opcionais: status, assigned_to, created_by, search (busca no título).",
)
async def list_tickets(
    page: int = Query(default=1, ge=1, description="Página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página"),
    ticket_status: Optional[TicketStatusEnum] = Query(default=None, alias="status", description="Filtrar por status"),
    assigned_to: Optional[int] = Query(default=None),
    created_by: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=255, description="Busca no título"),
    repo: TicketRepository = Depends(get_ticket_repo),
    _user: User = Depends(get_current_active_user),
):
    domain_status = TicketStatus(ticket_status.value) if ticket_status else None
    skip = (page - 1) * page_size

    total = await repo.count_filtered(
        status=domain_status, assigned_to=assigned_to,
        created_by=created_by, search=search,
    )
    tickets = await repo.list_filtered(
        status=domain_status, assigned_to=assigned_to,
        created_by=created_by, search=search,
        skip=skip, limit=page_size,
    )

    return PaginatedResponse(
        items=[_to_out_entity(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def _to_out_entity(t) -> TicketOut:
    """From domain entity (not DTO) to schema."""
    return TicketOut(
        id=t.id, title=t.title, description=t.description,
        status=t.status.value, milestones=t.milestones_as_dicts(),
        assigned_to=t.assigned_to, created_by=t.created_by,
        created_at=t.created_at, updated_at=t.updated_at,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketOut,
    summary="Detalhe de um ticket",
)
async def get_ticket(
    ticket_id: int,
    repo: TicketRepository = Depends(get_ticket_repo),
    _user: User = Depends(get_current_active_user),
):
    uc = GetTicketUseCase(repo)
    result = await uc.execute(GetTicketByIdQuery(ticket_id=ticket_id))
    if not result:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return _to_out(result)


@router.patch(
    "/{ticket_id}",
    response_model=TicketOut,
    summary="Atualizar ticket",
)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    milestones_dicts = [m.model_dump() for m in payload.milestones] if payload.milestones else None
    uc = UpdateTicketUseCase(repo, uow)
    result = await uc.execute(UpdateTicketCommand(
        ticket_id=ticket_id,
        performed_by=current_user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status.value if payload.status else None,
        milestones=milestones_dicts,
        assigned_to=payload.assigned_to,
    ))
    return _to_out(result)


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar ticket",
)
async def delete_ticket(
    ticket_id: int,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = DeleteTicketUseCase(repo, uow)
    await uc.execute(DeleteTicketCommand(ticket_id=ticket_id, performed_by=current_user.id))


# ════════════════════════════════════════════════════════════════
# STATE MACHINE
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/transition",
    response_model=TicketOut,
    summary="Transicionar status do ticket (state machine)",
    description="Transições válidas: open→in_progress, in_progress→done|open, done→open.",
)
async def transition_ticket(
    ticket_id: int,
    payload: TransitionRequest,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = TransitionTicketUseCase(repo, uow)
    result = await uc.execute(TransitionTicketCommand(
        ticket_id=ticket_id,
        new_status=payload.status.value,
        performed_by=current_user.id,
    ))
    return _to_out(result)


# ════════════════════════════════════════════════════════════════
# MILESTONES
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/milestones",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar milestone a um ticket",
)
async def add_milestone(
    ticket_id: int,
    payload: MilestoneAddRequest,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = AddMilestoneUseCase(repo, uow)
    result = await uc.execute(AddMilestoneCommand(
        ticket_id=ticket_id,
        performed_by=current_user.id,
        title=payload.title,
        due_date=payload.due_date,
    ))
    return _to_out(result)


@router.post(
    "/{ticket_id}/milestones/complete",
    response_model=TicketOut,
    summary="Marcar milestone como concluído",
)
async def complete_milestone(
    ticket_id: int,
    payload: MilestoneCompleteRequest,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = CompleteMilestoneUseCase(repo, uow)
    result = await uc.execute(CompleteMilestoneCommand(
        ticket_id=ticket_id,
        milestone_index=payload.milestone_index,
        performed_by=current_user.id,
    ))
    return _to_out(result)
