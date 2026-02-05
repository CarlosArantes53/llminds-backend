"""DTOs da camada de aplicação para LLM Datasets — commands e queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ════════════════════════════════════════════════════════════════
# COMMANDS
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CreateDatasetCommand:
    user_id: int
    prompt_text: str
    response_text: str
    target_model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateDatasetCommand:
    dataset_id: int
    performed_by: int
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    target_model: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class DeleteDatasetCommand:
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
    user_id: Optional[int] = None  # None = admin lista todos
    skip: int = 0
    limit: int = 100


# ════════════════════════════════════════════════════════════════
# RESULT DTOs
# ════════════════════════════════════════════════════════════════

@dataclass
class DatasetResult:
    id: int
    user_id: int
    prompt_text: str
    response_text: str
    target_model: str
    status: str
    metadata: dict[str, Any]
    inserted_at: Optional[str] = None
    updated_at: Optional[str] = None
