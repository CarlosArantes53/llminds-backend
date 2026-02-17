"""Use Cases de LLM Datasets."""

from __future__ import annotations
from typing import Optional

from app.domain.systems.datasets.entity import LLMDataset, DatasetRow, FineTuningStatus
from app.domain.systems.datasets.repository import IDatasetRepository
from app.domain.systems.users.entity import User
from app.domain.systems.users.authorization_service import AuthorizationService
from app.application.dtos.dataset_dtos import (
    AddRowCommand,
    CreateDatasetCommand,
    DatasetResult,
    DeleteDatasetCommand,
    DeleteRowCommand,
    GetDatasetByIdQuery,
    ListDatasetsQuery,
    RowResult,
    UpdateDatasetCommand,
    UpdateRowCommand,
)
from app.application.shared.unit_of_work import UnitOfWork


def _row_to_result(r: DatasetRow) -> RowResult:
    return RowResult(
        id=r.id,
        dataset_id=r.dataset_id,
        prompt_text=r.prompt_text,
        response_text=r.response_text,
        category=r.category,
        semantics=r.semantics,
        order=r.order,
        inserted_at=r.inserted_at.isoformat() if r.inserted_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
    )


def _to_result(d: LLMDataset, include_rows: bool = True) -> DatasetResult:
    return DatasetResult(
        id=d.id,
        user_id=d.user_id,
        name=d.name,
        target_model=d.target_model,
        status=d.status.value,
        metadata=d.metadata,
        row_count=d.row_count,
        rows=[_row_to_result(r) for r in d.rows] if include_rows else [],
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
            name=cmd.name,
            target_model=cmd.target_model,
            metadata=cmd.metadata,
        )
        for row_input in cmd.rows:
            dataset.add_row(DatasetRow(
                prompt_text=row_input.prompt_text,
                response_text=row_input.response_text,
                category=row_input.category,
                semantics=row_input.semantics,
            ))

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
        dataset = await self._repo.get_by_id(query.dataset_id, load_rows=True)
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
        return [_to_result(d, include_rows=False) for d in datasets]


class UpdateDatasetUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: UpdateDatasetCommand, actor: User) -> DatasetResult:
        dataset = await self._repo.get_by_id(cmd.dataset_id, load_rows=False)
        if not dataset:
            raise ValueError("Dataset não encontrado")
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)

        changed: dict = {}
        if cmd.name is not None and cmd.name != dataset.name:
            changed["name"] = {"old": dataset.name[:50], "new": cmd.name[:50]}
            dataset.name = cmd.name
        if cmd.target_model is not None:
            changed["target_model"] = {"old": dataset.target_model, "new": cmd.target_model}
            dataset.target_model = cmd.target_model
        if cmd.status is not None:
            new_status = FineTuningStatus(cmd.status)
            dataset.transition_status(new_status)
        if cmd.metadata is not None:
            dataset.metadata = cmd.metadata

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
        dataset = await self._repo.get_by_id(cmd.dataset_id, load_rows=False)
        if not dataset:
            raise ValueError("Dataset não encontrado")
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)
        dataset.record_deletion(performed_by=cmd.performed_by)
        self._uow.collect_events_from(dataset)
        await self._repo.delete(cmd.dataset_id)
        await self._uow.commit()


# ════════════════════════════════════════════════════════════════
# ROW USE CASES
# ════════════════════════════════════════════════════════════════

class AddRowUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: AddRowCommand, actor: User) -> RowResult:
        dataset = await self._repo.get_by_id(cmd.dataset_id, load_rows=False)
        if not dataset:
            raise ValueError("Dataset não encontrado")
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)

        row = DatasetRow(
            prompt_text=cmd.prompt_text,
            response_text=cmd.response_text,
            category=cmd.category,
            semantics=cmd.semantics,
        )
        row.validate()

        created = await self._repo.add_row(cmd.dataset_id, row)
        dataset.record_update({"rows": "added"}, performed_by=cmd.performed_by)
        self._uow.collect_events_from(dataset)
        await self._uow.commit()
        return _row_to_result(created)


class UpdateRowUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: UpdateRowCommand, actor: User) -> RowResult:
        dataset = await self._repo.get_by_id(cmd.dataset_id, load_rows=False)
        if not dataset:
            raise ValueError("Dataset não encontrado")
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)

        rows = await self._repo.get_rows(cmd.dataset_id)
        row = next((r for r in rows if r.id == cmd.row_id), None)
        if not row:
            raise ValueError("Row não encontrada")

        if cmd.prompt_text is not None:
            row.prompt_text = cmd.prompt_text
        if cmd.response_text is not None:
            row.response_text = cmd.response_text
        if cmd.category is not None:
            row.category = cmd.category
        if cmd.semantics is not None:
            row.semantics = cmd.semantics

        row.validate()
        updated = await self._repo.update_row(row)
        await self._uow.commit()
        return _row_to_result(updated)


class DeleteRowUseCase:
    def __init__(self, repo: IDatasetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(self, cmd: DeleteRowCommand, actor: User) -> None:
        dataset = await self._repo.get_by_id(cmd.dataset_id, load_rows=False)
        if not dataset:
            raise ValueError("Dataset não encontrado")
        AuthorizationService.ensure_can_access_dataset(actor, dataset.user_id)
        await self._repo.delete_row(cmd.row_id)
        await self._uow.commit()