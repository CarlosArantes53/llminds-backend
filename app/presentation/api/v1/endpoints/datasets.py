"""
Endpoints de LLM Datasets — /api/v1/datasets

CRUD + bulk import + paginação + filtros + audit logs.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.systems.datasets.entity import FineTuningStatus, LLMDataset
from app.domain.systems.users.entity import User, UserRole
from app.domain.systems.users.authorization_service import AuthorizationService
from app.infrastructure.database import get_db
from app.infrastructure.database.models import DatasetAuditLogModel
from app.infrastructure.systems.datasets.repository import DatasetRepository
from app.application.shared.unit_of_work import UnitOfWork
from app.application.dtos.dataset_dtos import (
    CreateDatasetCommand,
    DeleteDatasetCommand,
    GetDatasetByIdQuery,
    UpdateDatasetCommand,
)
from app.application.systems.datasets.use_cases import (
    CreateDatasetUseCase,
    DeleteDatasetUseCase,
    GetDatasetUseCase,
    UpdateDatasetUseCase,
)
from app.presentation.api.v1.schemas import (
    DatasetAuditLogOut,
    DatasetBulkCreateRequest,
    DatasetBulkCreateResponse,
    DatasetCreate,
    DatasetOut,
    DatasetUpdate,
    FineTuningStatusEnum,
    PaginatedResponse,
)
from app.presentation.api.v1.deps import get_current_active_user, get_uow, get_dataset_repo

router = APIRouter()


def _to_out(r) -> DatasetOut:
    return DatasetOut(
        id=r.id, user_id=r.user_id,
        prompt_text=r.prompt_text, response_text=r.response_text,
        target_model=r.target_model, status=r.status,
        metadata=r.metadata,
    )


def _entity_to_out(d) -> DatasetOut:
    return DatasetOut(
        id=d.id, user_id=d.user_id,
        prompt_text=d.prompt_text, response_text=d.response_text,
        target_model=d.target_model, status=d.status.value,
        metadata=d.metadata,
        inserted_at=d.inserted_at, updated_at=d.updated_at,
    )


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=DatasetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Inserir par prompt/response",
)
async def create_dataset(
    payload: DatasetCreate,
    repo: DatasetRepository = Depends(get_dataset_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = CreateDatasetUseCase(repo, uow)
    result = await uc.execute(CreateDatasetCommand(
        user_id=current_user.id,
        prompt_text=payload.prompt_text,
        response_text=payload.response_text,
        target_model=payload.target_model,
        metadata=payload.metadata,
    ))
    return _to_out(result)


@router.get(
    "/",
    response_model=PaginatedResponse[DatasetOut],
    summary="Listar datasets com paginação e filtros",
    description="Admin vê todos. Demais veem apenas seus próprios. Filtros: status, target_model.",
)
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    dataset_status: Optional[FineTuningStatusEnum] = Query(default=None, alias="status"),
    target_model: Optional[str] = Query(default=None),
    repo: DatasetRepository = Depends(get_dataset_repo),
    current_user: User = Depends(get_current_active_user),
):
    domain_status = FineTuningStatus(dataset_status.value) if dataset_status else None
    user_id = None if current_user.is_admin() else current_user.id
    skip = (page - 1) * page_size

    total = await repo.count_filtered(user_id=user_id, status=domain_status, target_model=target_model)
    datasets = await repo.list_filtered(
        user_id=user_id, status=domain_status, target_model=target_model,
        skip=skip, limit=page_size,
    )

    return PaginatedResponse(
        items=[_entity_to_out(d) for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/{dataset_id}",
    response_model=DatasetOut,
    summary="Detalhe de um dataset",
)
async def get_dataset(
    dataset_id: int,
    repo: DatasetRepository = Depends(get_dataset_repo),
    current_user: User = Depends(get_current_active_user),
):
    uc = GetDatasetUseCase(repo)
    result = await uc.execute(GetDatasetByIdQuery(dataset_id=dataset_id), actor=current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")
    return _to_out(result)


@router.patch(
    "/{dataset_id}",
    response_model=DatasetOut,
    summary="Atualizar dataset",
)
async def update_dataset(
    dataset_id: int,
    payload: DatasetUpdate,
    repo: DatasetRepository = Depends(get_dataset_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = UpdateDatasetUseCase(repo, uow)
    result = await uc.execute(
        UpdateDatasetCommand(
            dataset_id=dataset_id,
            performed_by=current_user.id,
            prompt_text=payload.prompt_text,
            response_text=payload.response_text,
            target_model=payload.target_model,
            status=payload.status.value if payload.status else None,
            metadata=payload.metadata,
        ),
        actor=current_user,
    )
    return _to_out(result)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar dataset",
)
async def delete_dataset(
    dataset_id: int,
    repo: DatasetRepository = Depends(get_dataset_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    uc = DeleteDatasetUseCase(repo, uow)
    await uc.execute(
        DeleteDatasetCommand(dataset_id=dataset_id, performed_by=current_user.id),
        actor=current_user,
    )


# ════════════════════════════════════════════════════════════════
# BULK IMPORT
# ════════════════════════════════════════════════════════════════

@router.post(
    "/bulk",
    response_model=DatasetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importação em lote de datasets (até 1000)",
)
async def bulk_create_datasets(
    payload: DatasetBulkCreateRequest,
    repo: DatasetRepository = Depends(get_dataset_repo),
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_active_user),
):
    created = 0
    failed = 0
    errors: list[str] = []

    entities = []
    for i, item in enumerate(payload.items):
        try:
            ds = LLMDataset(
                user_id=current_user.id,
                prompt_text=item.prompt_text,
                response_text=item.response_text,
                target_model=item.target_model,
                metadata=item.metadata,
            )
            ds.validate_content()
            entities.append(ds)
        except ValueError as e:
            failed += 1
            errors.append(f"Item {i}: {str(e)}")

    if entities:
        results = await repo.bulk_create(entities)
        created = len(results)
        await uow.commit()

    return DatasetBulkCreateResponse(created=created, failed=failed, errors=errors)


# ════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ════════════════════════════════════════════════════════════════

@router.get(
    "/{dataset_id}/audit-logs",
    response_model=list[DatasetAuditLogOut],
    summary="Listar audit logs de um dataset (admin)",
)
async def get_dataset_audit_logs(
    dataset_id: int,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_user),
):
    stmt = (
        select(DatasetAuditLogModel)
        .where(DatasetAuditLogModel.dataset_id == dataset_id)
        .order_by(DatasetAuditLogModel.performed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        DatasetAuditLogOut(
            id=log.id, dataset_id=log.dataset_id, action=log.action,
            changed_fields=log.changed_fields, performed_by=log.performed_by,
            performed_at=log.performed_at,
        )
        for log in logs
    ]
