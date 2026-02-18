"""
Endpoints de Tickets — /api/v1/tickets

CRUD + state machine transitions + milestones + paginação + filtros.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from app.application.systems.users.use_cases import AddReplyUseCase, AssignTicketUseCase, GetTicketWithRepliesUseCase
from app.infrastructure.services.file_storage import FileStorageService, FileStorageError
from app.domain.systems.tickets.entity import TicketStatus
from app.domain.systems.users.entity import User
from app.infrastructure.systems.tickets.repository import TicketRepository
from app.application.shared.unit_of_work import UnitOfWork
from app.application.dtos.ticket_dtos import (
    AddMilestoneCommand,
    AddReplyCommand,
    AssignTicketCommand,
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
from app.infrastructure.systems.users.repository import UserRepository
from app.domain.systems.users.authorization_service import AuthorizationService, AuthorizationError
from app.presentation.api.v1.schemas import (
    AgentOut,
    AssignTicketRequest,
    MilestoneAddRequest,
    MilestoneCompleteRequest,
    PaginatedResponse,
    TicketAttachmentOut,
    TicketCreate,
    TicketOut,
    TicketReplyCreate,
    TicketReplyOut,
    TicketStatusEnum,
    TicketUpdate,
    TransitionRequest,
)
from app.presentation.api.v1.deps import get_current_active_user, get_uow, get_ticket_repo, get_user_repo, require_roles

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
    "/agents",
    response_model=list[AgentOut],
    summary="Listar agentes disponíveis para atribuição",
)
async def list_agents(
    repo: TicketRepository = Depends(get_ticket_repo),
    _admin: User = Depends(require_roles("admin")),
):
    agents = await repo.list_agents()
    return [AgentOut(id=a["id"], username=a["username"]) for a in agents]


@router.get(
    "/{ticket_id}",
    response_model=TicketOut,
    summary="Detalhe de um ticket (com replies e anexos)",
)
async def get_ticket(
    ticket_id: int,
    repo: TicketRepository = Depends(get_ticket_repo),
    _user: User = Depends(get_current_active_user),
):
    uc = GetTicketWithRepliesUseCase(repo)
    result = await uc.execute(GetTicketByIdQuery(ticket_id=ticket_id))
    if not result:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    # Preencher download_url nos attachments
    def _with_url(att):
        return TicketAttachmentOut(
            **att.__dict__,
            download_url=f"/api/v1/tickets/{ticket_id}/attachments/{att.id}/download",
        )

    return TicketOut(
        id=result.id, title=result.title, description=result.description,
        status=result.status, milestones=result.milestones,
        assigned_to=result.assigned_to, created_by=result.created_by,
        replies=[
            TicketReplyOut(
                id=r.id, ticket_id=r.ticket_id, author_id=r.author_id,
                body=r.body,
                attachments=[_with_url(a) for a in r.attachments],
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in result.replies
        ],
        attachments=[_with_url(a) for a in result.attachments],
        created_at=result.created_at, updated_at=result.updated_at,
    )


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

# ════════════════════════════════════════════════════════════════
# ASSIGNMENT (admin → agent)
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/assign",
    response_model=TicketOut,
    summary="Atribuir ticket a um agente (admin only)",
)
async def assign_ticket(
    ticket_id: int,
    payload: AssignTicketRequest,
    repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = AssignTicketUseCase(repo, user_repo, uow)
    result = await uc.execute(
        AssignTicketCommand(
            ticket_id=ticket_id,
            agent_id=payload.agent_id,
            performed_by=current_user.id,
        ),
        actor=current_user,
    )
    return _to_out(result)

# ════════════════════════════════════════════════════════════════
# REPLIES
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/replies",
    response_model=TicketReplyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar resposta ao ticket",
    description="Criador do ticket, agente atribuído ou admin podem responder.",
)
async def add_reply(
    ticket_id: int,
    payload: TicketReplyCreate,
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = AddReplyUseCase(repo, uow)
    result = await uc.execute(
        AddReplyCommand(
            ticket_id=ticket_id,
            author_id=current_user.id,
            body=payload.body,
        ),
        actor=current_user,
    )
    return TicketReplyOut(
        id=result.id,
        ticket_id=result.ticket_id,
        author_id=result.author_id,
        author_username=current_user.username,
        body=result.body,
        created_at=result.created_at,
    )


@router.get(
    "/{ticket_id}/replies",
    response_model=list[TicketReplyOut],
    summary="Listar respostas de um ticket",
)
async def list_replies(
    ticket_id: int,
    repo: TicketRepository = Depends(get_ticket_repo),
    _user: User = Depends(get_current_active_user),
):
    replies = await repo.get_replies(ticket_id)
    return [
        TicketReplyOut(
            id=r.id, ticket_id=r.ticket_id, author_id=r.author_id,
            body=r.body,
            attachments=[
                TicketAttachmentOut(
                    id=a.id, ticket_id=a.ticket_id, reply_id=a.reply_id,
                    uploaded_by=a.uploaded_by,
                    original_filename=a.original_filename,
                    stored_filename=a.stored_filename,
                    content_type=a.content_type,
                    file_size=a.file_size,
                    download_url=f"/api/v1/tickets/{a.ticket_id}/attachments/{a.id}/download",
                    created_at=a.created_at,
                )
                for a in r.attachments
            ],
            created_at=r.created_at,
        )
        for r in replies
    ]


# ════════════════════════════════════════════════════════════════
# ATTACHMENTS (upload + download)
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{ticket_id}/attachments",
    response_model=TicketAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de anexo ao ticket (imagem ou PDF)",
    description="Aceita: image/jpeg, image/png, image/gif, image/webp, application/pdf. Max 10MB.",
)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    reply_id: Optional[int] = Query(default=None, description="ID da reply (ou null para anexo do ticket)"),
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    # Verificar se ticket existe
    ticket = await repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    # Verificar permissão (mesma regra de reply)
    try:
        AuthorizationService.ensure_can_reply_ticket(
            current_user, ticket.created_by, ticket.assigned_to
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Salvar arquivo
    storage = FileStorageService()
    try:
        file_info = await storage.save(ticket_id, file)
    except FileStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Persistir metadados
    from app.domain.systems.tickets.entity import TicketAttachment
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        reply_id=reply_id,
        uploaded_by=current_user.id,
        **file_info,
    )
    created = await repo.add_attachment(attachment)
    await uow.commit()

    return TicketAttachmentOut(
        id=created.id,
        ticket_id=created.ticket_id,
        reply_id=created.reply_id,
        uploaded_by=created.uploaded_by,
        original_filename=created.original_filename,
        stored_filename=created.stored_filename,
        content_type=created.content_type,
        file_size=created.file_size,
        download_url=f"/api/v1/tickets/{ticket_id}/attachments/{created.id}/download",
        created_at=created.created_at,
    )


@router.post(
    "/{ticket_id}/replies/{reply_id}/attachments",
    response_model=TicketAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de anexo em uma resposta específica",
)
async def upload_reply_attachment(
    ticket_id: int,
    reply_id: int,
    file: UploadFile = File(...),
    repo: TicketRepository = Depends(get_ticket_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    # Reutiliza a mesma lógica do upload_attachment com reply_id preenchido
    ticket = await repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    try:
        AuthorizationService.ensure_can_reply_ticket(
            current_user, ticket.created_by, ticket.assigned_to
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))

    storage = FileStorageService()
    try:
        file_info = await storage.save(ticket_id, file)
    except FileStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.domain.systems.tickets.entity import TicketAttachment
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        reply_id=reply_id,
        uploaded_by=current_user.id,
        **file_info,
    )
    created = await repo.add_attachment(attachment)
    await uow.commit()

    return TicketAttachmentOut(
        id=created.id,
        ticket_id=created.ticket_id,
        reply_id=created.reply_id,
        uploaded_by=created.uploaded_by,
        original_filename=created.original_filename,
        stored_filename=created.stored_filename,
        content_type=created.content_type,
        file_size=created.file_size,
        download_url=f"/api/v1/tickets/{ticket_id}/attachments/{created.id}/download",
        created_at=created.created_at,
    )


@router.get(
    "/{ticket_id}/attachments/{attachment_id}/download",
    summary="Download de anexo",
)
async def download_attachment(
    ticket_id: int,
    attachment_id: int,
    repo: TicketRepository = Depends(get_ticket_repo),
    current_user: User = Depends(get_current_active_user),
):
    from fastapi.responses import FileResponse

    # 1. Verificar ticket
    ticket = await repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    # 2. Verificar permissão
    try:
        AuthorizationService.ensure_can_reply_ticket(
            current_user, ticket.created_by, ticket.assigned_to
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))

    attachments = await repo.get_attachments(ticket_id)
    attachment = next((a for a in attachments if a.id == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")

    storage = FileStorageService()
    file_path = storage.get_path(ticket_id, attachment.stored_filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco")

    return FileResponse(
        path=str(file_path),
        filename=attachment.original_filename,
        media_type=attachment.content_type,
    )