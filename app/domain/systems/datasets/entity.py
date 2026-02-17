"""Entidades de domínio — LLMDataset (container) + DatasetRow (linhas)."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.events.base import AggregateRoot
from app.domain.events.dataset_events import (
    DatasetCreated,
    DatasetDeleted,
    DatasetStatusChanged,
    DatasetUpdated,
)


class FineTuningStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_STATUS_TRANSITIONS: dict[FineTuningStatus, list[FineTuningStatus]] = {
    FineTuningStatus.PENDING: [FineTuningStatus.PROCESSING],
    FineTuningStatus.PROCESSING: [FineTuningStatus.COMPLETED, FineTuningStatus.FAILED],
    FineTuningStatus.FAILED: [FineTuningStatus.PENDING],
    FineTuningStatus.COMPLETED: [],
}


@dataclass
class DatasetRow:
    """Uma linha de dados dentro de um dataset."""
    id: Optional[int] = None
    dataset_id: Optional[int] = None
    prompt_text: str = ""
    response_text: str = ""
    category: str = ""
    semantics: str = ""
    order: int = 0
    inserted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def validate(self) -> None:
        if not self.prompt_text.strip():
            raise ValueError("prompt_text não pode ser vazio")
        if not self.response_text.strip():
            raise ValueError("response_text não pode ser vazio")


@dataclass
class LLMDataset(AggregateRoot):
    id: Optional[int] = None
    user_id: Optional[int] = None
    name: str = ""
    target_model: str = ""
    status: FineTuningStatus = FineTuningStatus.PENDING
    metadata: dict = field(default_factory=dict)
    rows: list[DatasetRow] = field(default_factory=list)
    inserted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        AggregateRoot.__init__(self)

    # ── Rows ──

    def add_row(self, row: DatasetRow) -> None:
        row.dataset_id = self.id
        row.order = len(self.rows)
        row.validate()
        self.rows.append(row)

    def remove_row(self, row_id: int) -> None:
        self.rows = [r for r in self.rows if r.id != row_id]
        for i, r in enumerate(self.rows):
            r.order = i

    @property
    def row_count(self) -> int:
        return len(self.rows)

    # ── Status transitions ──

    def can_transition_to(self, new_status: FineTuningStatus) -> bool:
        return new_status in _STATUS_TRANSITIONS.get(self.status, [])

    def transition_status(self, new_status: FineTuningStatus) -> None:
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Transição de status inválida: {self.status.value} → {new_status.value}"
            )
        old = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        self._record_event(DatasetStatusChanged(
            dataset_id=self.id,
            old_status=old.value,
            new_status=new_status.value,
        ))

    # ── Validation ──

    def validate_content(self) -> None:
        if not self.name.strip():
            raise ValueError("name não pode ser vazio")
        for row in self.rows:
            row.validate()

    # ── Events ──

    def record_creation(self) -> None:
        self._record_event(DatasetCreated(
            dataset_id=self.id,
            user_id=self.user_id,
            target_model=self.target_model,
        ))

    def record_update(self, changed_fields: dict, performed_by: Optional[int] = None) -> None:
        self._record_event(DatasetUpdated(
            dataset_id=self.id,
            changed_fields=changed_fields,
            performed_by=performed_by,
        ))

    def record_deletion(self, performed_by: Optional[int] = None) -> None:
        self._record_event(DatasetDeleted(
            dataset_id=self.id,
            performed_by=performed_by,
        ))