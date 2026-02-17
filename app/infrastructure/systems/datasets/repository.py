"""Repositório de LLM Datasets — SQLAlchemy com rows."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.systems.datasets.entity import LLMDataset, DatasetRow, FineTuningStatus
from app.domain.systems.datasets.repository import IDatasetRepository
from app.infrastructure.database.models import LLMDatasetModel, DatasetRowModel


class DatasetRepository(IDatasetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Mapeamento ──

    @staticmethod
    def _row_to_entity(model: DatasetRowModel) -> DatasetRow:
        return DatasetRow(
            id=model.id,
            dataset_id=model.dataset_id,
            prompt_text=model.prompt_text,
            response_text=model.response_text,
            category=model.category or "",
            semantics=model.semantics or "",
            order=model.order,
            inserted_at=model.inserted_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_entity(model: LLMDatasetModel, include_rows: bool = True) -> LLMDataset:
        rows = []
        if include_rows and model.rows:
            rows = [DatasetRepository._row_to_entity(r) for r in model.rows]
        return LLMDataset(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            target_model=model.target_model or "",
            status=FineTuningStatus(model.status),
            metadata=model.metadata_ or {},
            rows=rows,
            inserted_at=model.inserted_at,
            updated_at=model.updated_at,
        )

    def _build_filter(self, stmt, *, user_id=None, status=None, target_model=None):
        if user_id is not None:
            stmt = stmt.where(LLMDatasetModel.user_id == user_id)
        if status is not None:
            stmt = stmt.where(LLMDatasetModel.status == status.value)
        if target_model:
            stmt = stmt.where(LLMDatasetModel.target_model == target_model)
        return stmt

    # ── Dataset CRUD ──

    async def get_by_id(self, dataset_id: int, load_rows: bool = True) -> Optional[LLMDataset]:
        stmt = select(LLMDatasetModel).where(LLMDatasetModel.id == dataset_id)
        if load_rows:
            stmt = stmt.options(selectinload(LLMDatasetModel.rows))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model, include_rows=load_rows) if model else None

    async def list_by_user(self, user_id: int) -> Sequence[LLMDataset]:
        stmt = (
            select(LLMDatasetModel)
            .where(LLMDatasetModel.user_id == user_id)
            .order_by(LLMDatasetModel.id)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m, include_rows=False) for m in result.scalars().all()]

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[LLMDataset]:
        stmt = select(LLMDatasetModel).offset(skip).limit(limit).order_by(LLMDatasetModel.id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m, include_rows=False) for m in result.scalars().all()]

    async def list_filtered(
        self,
        *,
        user_id: Optional[int] = None,
        status: Optional[FineTuningStatus] = None,
        target_model: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[LLMDataset]:
        stmt = select(LLMDatasetModel)
        stmt = self._build_filter(stmt, user_id=user_id, status=status, target_model=target_model)
        stmt = stmt.offset(skip).limit(limit).order_by(LLMDatasetModel.inserted_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m, include_rows=False) for m in result.scalars().all()]

    async def count_filtered(self, *, user_id=None, status=None, target_model=None) -> int:
        stmt = select(func.count(LLMDatasetModel.id))
        stmt = self._build_filter(stmt, user_id=user_id, status=status, target_model=target_model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, dataset: LLMDataset) -> LLMDataset:
        model = LLMDatasetModel(
            user_id=dataset.user_id,
            name=dataset.name,
            target_model=dataset.target_model,
            status=dataset.status.value,
            metadata_=dataset.metadata,
        )
        self._session.add(model)
        await self._session.flush()

        # Criar rows
        for row in dataset.rows:
            row_model = DatasetRowModel(
                dataset_id=model.id,
                prompt_text=row.prompt_text,
                response_text=row.response_text,
                category=row.category,
                semantics=row.semantics,
                order=row.order,
            )
            self._session.add(row_model)

        await self._session.flush()
        # Reload com rows
        return await self.get_by_id(model.id)

    async def bulk_create(self, datasets: list[LLMDataset]) -> list[LLMDataset]:
        results = []
        for d in datasets:
            created = await self.create(d)
            results.append(created)
        return results

    async def update(self, dataset: LLMDataset) -> LLMDataset:
        model = await self._session.get(LLMDatasetModel, dataset.id)
        if not model:
            raise ValueError(f"Dataset {dataset.id} não encontrado")
        model.name = dataset.name
        model.target_model = dataset.target_model
        model.status = dataset.status.value
        model.metadata_ = dataset.metadata
        await self._session.flush()
        await self._session.refresh(model)
        return await self.get_by_id(dataset.id)

    async def delete(self, dataset_id: int) -> None:
        model = await self._session.get(LLMDatasetModel, dataset_id)
        if model:
            await self._session.delete(model)  # cascade deleta rows
            await self._session.flush()

    # ── Row-level ──

    async def add_row(self, dataset_id: int, row: DatasetRow) -> DatasetRow:
        # Descobrir próximo order
        stmt = select(func.coalesce(func.max(DatasetRowModel.order), -1)).where(
            DatasetRowModel.dataset_id == dataset_id
        )
        result = await self._session.execute(stmt)
        next_order = result.scalar_one() + 1

        model = DatasetRowModel(
            dataset_id=dataset_id,
            prompt_text=row.prompt_text,
            response_text=row.response_text,
            category=row.category,
            semantics=row.semantics,
            order=next_order,
        )
        self._session.add(model)
        await self._session.flush()
        return self._row_to_entity(model)

    async def update_row(self, row: DatasetRow) -> DatasetRow:
        model = await self._session.get(DatasetRowModel, row.id)
        if not model:
            raise ValueError(f"Row {row.id} não encontrada")
        model.prompt_text = row.prompt_text
        model.response_text = row.response_text
        model.category = row.category
        model.semantics = row.semantics
        model.order = row.order
        await self._session.flush()
        await self._session.refresh(model)
        return self._row_to_entity(model)

    async def delete_row(self, row_id: int) -> None:
        model = await self._session.get(DatasetRowModel, row_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()

    async def get_rows(self, dataset_id: int) -> Sequence[DatasetRow]:
        stmt = (
            select(DatasetRowModel)
            .where(DatasetRowModel.dataset_id == dataset_id)
            .order_by(DatasetRowModel.order)
        )
        result = await self._session.execute(stmt)
        return [self._row_to_entity(m) for m in result.scalars().all()]