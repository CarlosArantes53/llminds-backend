from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .entity import LLMDataset, DatasetRow, FineTuningStatus


class IDatasetRepository(ABC):

    @abstractmethod
    async def get_by_id(self, dataset_id: int, load_rows: bool = True) -> Optional[LLMDataset]:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> Sequence[LLMDataset]:
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[LLMDataset]:
        ...

    @abstractmethod
    async def list_filtered(
        self,
        *,
        user_id: Optional[int] = None,
        status: Optional[FineTuningStatus] = None,
        target_model: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[LLMDataset]:
        ...

    @abstractmethod
    async def count_filtered(
        self,
        *,
        user_id: Optional[int] = None,
        status: Optional[FineTuningStatus] = None,
        target_model: Optional[str] = None,
    ) -> int:
        ...

    @abstractmethod
    async def create(self, dataset: LLMDataset) -> LLMDataset:
        ...

    @abstractmethod
    async def bulk_create(self, datasets: list[LLMDataset]) -> list[LLMDataset]:
        ...

    @abstractmethod
    async def update(self, dataset: LLMDataset) -> LLMDataset:
        ...

    @abstractmethod
    async def delete(self, dataset_id: int) -> None:
        ...

    # ── Row-level operations ──

    @abstractmethod
    async def add_row(self, dataset_id: int, row: DatasetRow) -> DatasetRow:
        ...

    @abstractmethod
    async def update_row(self, row: DatasetRow) -> DatasetRow:
        ...

    @abstractmethod
    async def delete_row(self, row_id: int) -> None:
        ...

    @abstractmethod
    async def get_rows(self, dataset_id: int) -> Sequence[DatasetRow]:
        ...