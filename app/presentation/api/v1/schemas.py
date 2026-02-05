"""
Schemas Pydantic — camada de Apresentação.

Inclui: DTOs de request/response, paginação, filtros, bulk import,
audit log output e error model para OpenAPI.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════
# GENERICS — Pagination wrapper
# ════════════════════════════════════════════════════════════════
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope de paginação genérico."""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════
# ERROR MODEL (para Swagger docs)
# ════════════════════════════════════════════════════════════════
class ErrorResponse(BaseModel):
    error: str = Field(..., examples=["validation_error"])
    detail: str = Field(..., examples=["Email já cadastrado"])
    request_id: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"error": "not_found", "detail": "Recurso não encontrado", "request_id": "a1b2c3d4"}}}


# ════════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════════
class UserRoleEnum(str, Enum):
    admin = "admin"
    agent = "agent"
    user = "user"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150, examples=["joao_silva"])
    email: str = Field(..., max_length=255, examples=["joao@empresa.com"])
    password: str = Field(..., min_length=6, examples=["senhaForte123"])
    role: UserRoleEnum = UserRoleEnum.user

    model_config = {"json_schema_extra": {"example": {"username": "joao_silva", "email": "joao@empresa.com", "password": "senhaForte123", "role": "user"}}}


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════
# AUTH / JWT
# ════════════════════════════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str = Field(..., examples=["joao_silva"])
    password: str = Field(..., examples=["senhaForte123"])


class TokenOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(default=3600, description="Segundos até expiração")


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


# ════════════════════════════════════════════════════════════════
# TICKETS
# ════════════════════════════════════════════════════════════════
class TicketStatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"


class MilestoneSchema(BaseModel):
    title: str = Field(..., min_length=1)
    due_date: Optional[str] = Field(None, description="ISO 8601 datetime")
    completed: bool = False
    completed_at: Optional[str] = None
    order: int = 0


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Implementar login OAuth"])
    description: str = Field(default="", examples=["Adicionar login com Google e GitHub"])
    milestones: list[MilestoneSchema] = Field(default_factory=list)
    assigned_to: Optional[int] = None

    model_config = {"json_schema_extra": {"example": {"title": "Implementar login OAuth", "description": "Adicionar login com Google e GitHub", "milestones": [{"title": "Pesquisa de libs", "due_date": "2026-03-01T00:00:00"}], "assigned_to": None}}}


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TicketStatusEnum] = None
    milestones: Optional[list[MilestoneSchema]] = None
    assigned_to: Optional[int] = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    milestones: list[dict[str, Any]]
    assigned_to: Optional[int]
    created_by: Optional[int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MilestoneAddRequest(BaseModel):
    title: str = Field(..., min_length=1, examples=["Deploy em staging"])
    due_date: Optional[str] = Field(None, description="ISO 8601", examples=["2026-03-15T00:00:00"])


class MilestoneCompleteRequest(BaseModel):
    milestone_index: int = Field(..., ge=0, examples=[0])


class TransitionRequest(BaseModel):
    status: TicketStatusEnum = Field(..., examples=["in_progress"])


# ── Filtros de Ticket ──
class TicketFilterParams(BaseModel):
    status: Optional[TicketStatusEnum] = None
    assigned_to: Optional[int] = None
    created_by: Optional[int] = None
    search: Optional[str] = Field(None, max_length=255, description="Busca no título")


# ════════════════════════════════════════════════════════════════
# LLM DATASETS
# ════════════════════════════════════════════════════════════════
class FineTuningStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DatasetCreate(BaseModel):
    prompt_text: str = Field(..., min_length=1, examples=["O que é machine learning?"])
    response_text: str = Field(..., min_length=1, examples=["Machine learning é um subcampo da IA..."])
    target_model: str = Field(default="", examples=["llama-3"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetUpdate(BaseModel):
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    target_model: Optional[str] = None
    status: Optional[FineTuningStatusEnum] = None
    metadata: Optional[dict[str, Any]] = None


class DatasetOut(BaseModel):
    id: int
    user_id: int
    prompt_text: str
    response_text: str
    target_model: str
    status: str
    metadata: dict[str, Any]
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DatasetBulkItem(BaseModel):
    prompt_text: str = Field(..., min_length=1)
    response_text: str = Field(..., min_length=1)
    target_model: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetBulkCreateRequest(BaseModel):
    items: list[DatasetBulkItem] = Field(..., min_length=1, max_length=1000)


class DatasetBulkCreateResponse(BaseModel):
    created: int
    failed: int
    errors: list[str] = Field(default_factory=list)


# ── Filtros de Dataset ──
class DatasetFilterParams(BaseModel):
    status: Optional[FineTuningStatusEnum] = None
    target_model: Optional[str] = None


# ════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ════════════════════════════════════════════════════════════════
class AuditLogOut(BaseModel):
    id: int
    action: str
    changed_fields: Optional[dict[str, Any]] = None
    performed_by: Optional[int] = None
    performed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserAuditLogOut(AuditLogOut):
    user_id: int


class DatasetAuditLogOut(AuditLogOut):
    dataset_id: int
