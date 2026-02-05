"""Eventos de domínio relacionados a LLM Datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class DatasetCreated(DomainEvent):
    dataset_id: int = 0
    user_id: int = 0
    target_model: str = ""


@dataclass(frozen=True)
class DatasetUpdated(DomainEvent):
    dataset_id: int = 0
    changed_fields: dict = None
    performed_by: Optional[int] = None

    def __post_init__(self):
        if self.changed_fields is None:
            object.__setattr__(self, "changed_fields", {})


@dataclass(frozen=True)
class DatasetStatusChanged(DomainEvent):
    dataset_id: int = 0
    old_status: str = ""
    new_status: str = ""


@dataclass(frozen=True)
class DatasetDeleted(DomainEvent):
    dataset_id: int = 0
    performed_by: Optional[int] = None
