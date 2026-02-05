"""
Endpoints de gestão de Users — /api/v1/users

CRUD administrativo + audit logs. Auth fica em /api/v1/auth.
"""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.systems.users.entity import User
from app.infrastructure.database import get_db
from app.infrastructure.database.models import UserAuditLogModel
from app.infrastructure.systems.users.repository import UserRepository
from app.application.shared.unit_of_work import UnitOfWork
from app.application.dtos.user_dtos import (
    DeleteUserCommand,
    ListUsersQuery,
    UpdateUserCommand,
)
from app.application.systems.users.use_cases import (
    DeleteUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from app.presentation.api.v1.schemas import (
    PaginatedResponse,
    UserAuditLogOut,
    UserOut,
    UserUpdate,
)
from app.presentation.api.v1.deps import (
    get_current_active_user,
    get_uow,
    get_user_repo,
    hash_password,
    require_roles,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[UserOut],
    summary="Listar todos os usuários (admin)",
)
async def list_users(
    repo: UserRepository = Depends(get_user_repo),
    current_user: User = Depends(require_roles("admin")),
):
    from app.application.systems.users.use_cases import ListUsersUseCase
    uc = ListUsersUseCase(repo)
    results = await uc.execute(ListUsersQuery(), actor=current_user)
    return [UserOut(id=r.id, username=r.username, email=r.email, role=r.role, is_active=r.is_active) for r in results]


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Buscar usuário por ID",
)
async def get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
    _admin: User = Depends(require_roles("admin")),
):
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserOut(id=user.id, username=user.username, email=user.email, role=user.role.value, is_active=user.is_active, created_at=user.created_at, updated_at=user.updated_at)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Atualizar usuário",
    description="Próprio usuário pode atualizar username/email/password. Admin pode alterar role e is_active.",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    repo: UserRepository = Depends(get_user_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = UpdateUserUseCase(repo, uow, hash_password)
    result = await uc.execute(
        UpdateUserCommand(
            user_id=user_id,
            performed_by=current_user.id,
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=payload.role.value if payload.role else None,
            is_active=payload.is_active,
        ),
        actor=current_user,
    )
    return UserOut(id=result.id, username=result.username, email=result.email, role=result.role, is_active=result.is_active)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar usuário (admin)",
)
async def delete_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(require_roles("admin")),
):
    uc = DeleteUserUseCase(repo, uow)
    await uc.execute(
        DeleteUserCommand(user_id=user_id, performed_by=current_user.id),
        actor=current_user,
    )


# ── Audit Logs ──

@router.get(
    "/{user_id}/audit-logs",
    response_model=list[UserAuditLogOut],
    summary="Listar audit logs de um usuário (admin)",
)
async def get_user_audit_logs(
    user_id: int,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    stmt = (
        select(UserAuditLogModel)
        .where(UserAuditLogModel.user_id == user_id)
        .order_by(UserAuditLogModel.performed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        UserAuditLogOut(
            id=log.id, user_id=log.user_id, action=log.action,
            changed_fields=log.changed_fields, performed_by=log.performed_by,
            performed_at=log.performed_at,
        )
        for log in logs
    ]
