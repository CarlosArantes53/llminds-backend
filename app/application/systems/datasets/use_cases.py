"""
Use Cases de LLM Datasets — camada de Aplicação.

Orquestram validação, persistência e eventos de domínio para datasets.
"""

from __future__ import annotations

from typing import Optional

from app.domain.systems.datasets.entity import LLMDataset, FineTuningStatus
from app.domain.systems.datasets.repository import IDatasetRepository
from app.domain.systems.users.entity import User, UserRole
from app.domain.systems.users.authorization_service import AuthorizationService
from app.application.dtos.dataset_dtos import (
    CreateDatasetCommand,
    DatasetResult,
    DeleteDatasetCommand,
    GetDatasetByIdQuery,
    ListDatasetsQuery,
    UpdateDatasetCommand,
)
from app.application.shared.unit_of_work import UnitOfWork


def _to_result(d: LLMDataset) -> DatasetResult:
    return DatasetResult(
        id=d.id,
        user_id=d.user_id,
        prompt_text=d.prompt_text,
        response_text=d.response_text,
        target_model=d.target_model,
        status=d.status.value,
        metadata=d.metadata,
        inserted_at=d.inserted_at.isoformat() if d.inserted_at else None,
        updated_at=d.updated_at.isoformat() if d.updated_at else None,
    )


class CreateDatasetUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: CreateDatasetCommand) -> DatasetResult:
        dataset = LLMDataset(
            user_id=cmd.user_id,
            prompt_text=cmd.prompt_text,
            response_text=cmd.response_text,
            target_model=cmd.target_model,
            metadata=cmd.metadata,
        )
        # Validação de domínio
        dataset.validate_content()

        created = await self._repo.create(dataset)
        created.record_creation()
        self._uow.collect_events_from(created)
        await self._uow.commit()
        return _to_result(created)


class GetDatasetUseCase:
    def __init__(self, repo: IDatasetRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetDatasetByIdQuery, actor: User) -> Optional[DatasetResult]:
        dataset = await self._repo.get_by_id(query.dataset_id)
        if not dataset:
            return None
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)
        return _to_result(dataset)


class ListDatasetsUseCase:
    def __init__(self, repo: IDatasetRepository) -> None:
        self._repo = repo

    async def execute(self, query: ListDatasetsQuery, actor: User) -> list[DatasetResult]:
        if actor.is_admin():
            datasets = await self._repo.list_all(skip=query.skip, limit=query.limit)
        else:
            datasets = await self._repo.list_by_user(actor.id)
        return [_to_result(d) for d in datasets]


class UpdateDatasetUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: UpdateDatasetCommand, actor: User) -> DatasetResult:
        dataset = await self._repo.get_by_id(cmd.dataset_id)
        if not dataset:
            raise ValueError("Dataset não encontrado")

        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)

        changed: dict = {}

        if cmd.prompt_text is not None and cmd.prompt_text != dataset.prompt_text:
            changed["prompt_text"] = {"old": dataset.prompt_text[:50], "new": cmd.prompt_text[:50]}
            dataset.prompt_text = cmd.prompt_text

        if cmd.response_text is not None and cmd.response_text != dataset.response_text:
            changed["response_text"] = {"old": dataset.response_text[:50], "new": cmd.response_text[:50]}
            dataset.response_text = cmd.response_text

        if cmd.target_model is not None:
            changed["target_model"] = {"old": dataset.target_model, "new": cmd.target_model}
            dataset.target_model = cmd.target_model

        if cmd.status is not None:
            new_status = FineTuningStatus(cmd.status)
            dataset.transition_status(new_status)  # usa state machine do domínio

        if cmd.metadata is not None:
            dataset.metadata = cmd.metadata

        # Valida conteúdo atualizado
        dataset.validate_content()

        if changed:
            dataset.record_update(changed, performed_by=cmd.performed_by)

        updated = await self._repo.update(dataset)
        self._uow.collect_events_from(updated)
        await self._uow.commit()
        return _to_result(updated)


class DeleteDatasetUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: DeleteDatasetCommand, actor: User) -> None:
        dataset = await self._repo.get_by_id(cmd.dataset_id)
        if not dataset:
            raise ValueError("Dataset não encontrado")

        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)

        dataset.record_deletion(performed_by=cmd.performed_by)
        self._uow.collect_events_from(dataset)
        await self._repo.delete(cmd.dataset_id)
        await self._uow.commit()
