"""Implementação concreta do repositório de LLM Datasets — SQLAlchemy com filtros e bulk."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.systems.datasets.entity import LLMDataset, FineTuningStatus
from app.domain.systems.datasets.repository import IDatasetRepository
from app.infrastructure.database.models import LLMDatasetModel


class DatasetRepository(IDatasetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: LLMDatasetModel) -> LLMDataset:
        return LLMDataset(
            id=model.id,
            user_id=model.user_id,
            prompt_text=model.prompt_text,
            response_text=model.response_text,
            target_model=model.target_model or "",
            status=FineTuningStatus(model.status),
            metadata=model.metadata_ or {},
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

    async def get_by_id(self, dataset_id: int) -> Optional[LLMDataset]:
        model = await self._session.get(LLMDatasetModel, dataset_id)
        return self._to_entity(model) if model else None

    async def list_by_user(self, user_id: int) -> Sequence[LLMDataset]:
        stmt = select(LLMDatasetModel).where(LLMDatasetModel.user_id == user_id).order_by(LLMDatasetModel.id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[LLMDataset]:
        stmt = select(LLMDatasetModel).offset(skip).limit(limit).order_by(LLMDatasetModel.id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

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
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_filtered(
        self,
        *,
        user_id: Optional[int] = None,
        status: Optional[FineTuningStatus] = None,
        target_model: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(LLMDatasetModel.id))
        stmt = self._build_filter(stmt, user_id=user_id, status=status, target_model=target_model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, dataset: LLMDataset) -> LLMDataset:
        model = LLMDatasetModel(
            user_id=dataset.user_id,
            prompt_text=dataset.prompt_text,
            response_text=dataset.response_text,
            target_model=dataset.target_model,
            status=dataset.status.value,
            metadata_=dataset.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def bulk_create(self, datasets: list[LLMDataset]) -> list[LLMDataset]:
        models = [
            LLMDatasetModel(
                user_id=d.user_id,
                prompt_text=d.prompt_text,
                response_text=d.response_text,
                target_model=d.target_model,
                status=d.status.value,
                metadata_=d.metadata,
            )
            for d in datasets
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_entity(m) for m in models]

    async def update(self, dataset: LLMDataset) -> LLMDataset:
        model = await self._session.get(LLMDatasetModel, dataset.id)
        if not model:
            raise ValueError(f"Dataset {dataset.id} não encontrado")
        model.prompt_text = dataset.prompt_text
        model.response_text = dataset.response_text
        model.target_model = dataset.target_model
        model.status = dataset.status.value
        model.metadata_ = dataset.metadata
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, dataset_id: int) -> None:
        model = await self._session.get(LLMDatasetModel, dataset_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
