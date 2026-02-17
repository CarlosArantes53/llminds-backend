"""DTOs para LLM Datasets — commands, queries e results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ════════════════════════════════════════════════════════════════
# ROW DTOs
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RowInput:
    prompt_text: str
    response_text: str
    category: str = ""
    semantics: str = ""


@dataclass
class RowResult:
    id: int
    dataset_id: int
    prompt_text: str
    response_text: str
    category: str
    semantics: str
    order: int
    inserted_at: Optional[str] = None
    updated_at: Optional[str] = None


# ════════════════════════════════════════════════════════════════
# COMMANDS
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CreateDatasetCommand:
    user_id: int
    name: str
    target_model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    rows: list[RowInput] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateDatasetCommand:
    dataset_id: int
    performed_by: int
    name: Optional[str] = None
    target_model: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class DeleteDatasetCommand:
    dataset_id: int
    performed_by: int


@dataclass(frozen=True)
class AddRowCommand:
    dataset_id: int
    performed_by: int
    prompt_text: str
    response_text: str
    category: str = ""
    semantics: str = ""


@dataclass(frozen=True)
class UpdateRowCommand:
    row_id: int
    dataset_id: int
    performed_by: int
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    category: Optional[str] = None
    semantics: Optional[str] = None


@dataclass(frozen=True)
class DeleteRowCommand:
    row_id: int
    dataset_id: int
    performed_by: int


# ════════════════════════════════════════════════════════════════
# QUERIES
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GetDatasetByIdQuery:
    dataset_id: int


@dataclass(frozen=True)
class ListDatasetsQuery:
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = 100


# ════════════════════════════════════════════════════════════════
# RESULT DTOs
# ════════════════════════════════════════════════════════════════

@dataclass
class DatasetResult:
    id: int
    user_id: int
    name: str
    target_model: str
    status: str
    metadata: dict[str, Any]
    row_count: int = 0
    rows: list[RowResult] = field(default_factory=list)
    inserted_at: Optional[str] = None
    updated_at: Optional[str] = None